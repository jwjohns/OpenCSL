import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .models import (
    ApprovalRequest, ApprovalStatus, SemanticChange,
    GovernancePolicy, User, UserRole, ChangeType
)
from .audit import AuditLogger
from .notifications import NotificationService

class ApprovalEngine:
    """
    Enterprise approval workflow engine for semantic changes.

    Ensures that all changes to business-critical metrics go through
    proper governance channels while maintaining agility for development.
    """

    def __init__(self, audit_logger: AuditLogger, notifier: NotificationService):
        self.audit_logger = audit_logger
        self.notifier = notifier
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.policies: Dict[str, GovernancePolicy] = {}
        self.users: Dict[str, User] = {}

    def submit_change(self, change: SemanticChange, requesting_user: User) -> ApprovalRequest:
        """Submit a semantic change for approval."""

        # Check if auto-approval is possible
        auto_approved = self._check_auto_approval(change, requesting_user)

        approval_request = ApprovalRequest(
            id=str(uuid.uuid4()),
            change_id=change.id,
            status=ApprovalStatus.APPROVED if auto_approved else ApprovalStatus.PENDING,
            auto_approved=auto_approved
        )

        if auto_approved:
            approval_request.approver = "system"
            approval_request.approved_at = datetime.now()
            approval_request.comments = "Auto-approved based on governance policy"
        else:
            self.pending_approvals[approval_request.id] = approval_request
            self._notify_stewards(change, approval_request)

        # Log the submission
        self.audit_logger.log_action(
            user=requesting_user.username,
            action="change_submitted",
            resource_type="approval_request",
            resource_id=approval_request.id,
            details={
                "change_type": change.change_type,
                "metric_name": change.metric_name,
                "auto_approved": auto_approved,
                "breaking_change": change.breaking_change
            }
        )

        return approval_request

    def approve_change(self, approval_id: str, approver: User, comments: str = "") -> ApprovalRequest:
        """Approve a pending change."""

        if approval_id not in self.pending_approvals:
            raise ValueError(f"Approval request {approval_id} not found")

        approval = self.pending_approvals[approval_id]

        # Verify approver has permissions
        if not self._can_approve(approver, approval):
            raise PermissionError(f"User {approver.username} cannot approve this change")

        approval.status = ApprovalStatus.APPROVED
        approval.approver = approver.username
        approval.approved_at = datetime.now()
        approval.comments = comments

        # Remove from pending
        del self.pending_approvals[approval_id]

        # Log the approval
        self.audit_logger.log_action(
            user=approver.username,
            action="change_approved",
            resource_type="approval_request",
            resource_id=approval_id,
            details={"comments": comments}
        )

        # Notify stakeholders
        self._notify_approval_decision(approval, "approved")

        return approval

    def reject_change(self, approval_id: str, approver: User, reason: str) -> ApprovalRequest:
        """Reject a pending change."""

        if approval_id not in self.pending_approvals:
            raise ValueError(f"Approval request {approval_id} not found")

        approval = self.pending_approvals[approval_id]

        if not self._can_approve(approver, approval):
            raise PermissionError(f"User {approver.username} cannot reject this change")

        approval.status = ApprovalStatus.REJECTED
        approval.approver = approver.username
        approval.approved_at = datetime.now()
        approval.comments = reason

        del self.pending_approvals[approval_id]

        self.audit_logger.log_action(
            user=approver.username,
            action="change_rejected",
            resource_type="approval_request",
            resource_id=approval_id,
            details={"reason": reason}
        )

        self._notify_approval_decision(approval, "rejected")

        return approval

    def _check_auto_approval(self, change: SemanticChange, user: User) -> bool:
        """Check if a change can be auto-approved based on policies."""

        # Never auto-approve breaking changes
        if change.breaking_change:
            return False

        # Check if user is admin
        if user.role == UserRole.ADMIN:
            return True

        # Check if it's a non-breaking update by the original author
        if (change.change_type == ChangeType.UPDATE and
            not change.breaking_change and
            change.author == user.username):
            return True

        # Check policy-based auto-approval
        for policy in self.policies.values():
            for criteria in policy.auto_approval_criteria:
                if self._matches_criteria(change, criteria):
                    return True

        return False

    def _can_approve(self, user: User, approval: ApprovalRequest) -> bool:
        """Check if user can approve this change."""

        # Admins can approve anything
        if user.role == UserRole.ADMIN:
            return True

        # Stewards can approve in their domains
        if user.role == UserRole.STEWARD:
            # TODO: Check if metric belongs to steward's domain
            return True

        return False

    def _matches_criteria(self, change: SemanticChange, criteria: Dict) -> bool:
        """Check if change matches auto-approval criteria."""

        if "change_type" in criteria:
            if change.change_type != criteria["change_type"]:
                return False

        if "breaking_change" in criteria:
            if change.breaking_change != criteria["breaking_change"]:
                return False

        if "owner" in criteria:
            if change.author not in criteria["owner"]:
                return False

        return True

    def _notify_stewards(self, change: SemanticChange, approval: ApprovalRequest):
        """Notify relevant stewards about pending approval."""

        message = f"""
New semantic change requires approval:

**Metric:** {change.metric_name}
**Type:** {change.change_type.value}
**Author:** {change.author}
**Breaking Change:** {'Yes' if change.breaking_change else 'No'}

**Description:** {change.description}
**Justification:** {change.justification}

**Approval ID:** {approval.id}

Please review and approve/reject this change.
        """.strip()

        self.notifier.send_notification(
            channel="stewards",
            message=message,
            metadata={
                "approval_id": approval.id,
                "change_type": change.change_type,
                "breaking_change": change.breaking_change
            }
        )

    def _notify_approval_decision(self, approval: ApprovalRequest, decision: str):
        """Notify about approval decision."""

        message = f"""
Semantic change has been **{decision}**:

**Approval ID:** {approval.id}
**Approver:** {approval.approver}
**Comments:** {approval.comments or 'None'}
        """.strip()

        self.notifier.send_notification(
            channel="general",
            message=message,
            metadata={
                "approval_id": approval.id,
                "decision": decision
            }
        )

    def get_pending_approvals(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        return list(self.pending_approvals.values())

    def cleanup_expired_approvals(self, max_age_days: int = 7):
        """Remove approval requests older than specified days."""

        cutoff = datetime.now() - timedelta(days=max_age_days)
        expired = []

        for approval_id, approval in self.pending_approvals.items():
            # Assuming we have a created_at field (would need to add to model)
            if hasattr(approval, 'created_at') and approval.created_at < cutoff:
                expired.append(approval_id)

        for approval_id in expired:
            del self.pending_approvals[approval_id]

        return len(expired)