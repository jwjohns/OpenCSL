from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .governance.models import (
    ApprovalRequest, ApprovalStatus, SemanticChange,
    User, UserRole, AuditEntry
)
from .governance.approval_engine import ApprovalEngine
from .governance.audit import AuditLogger
from .governance.rbac import AccessControlManager
from .governance.notifications import NotificationService
from .governance.github_integration import GitHubWorkflowIntegration

# Initialize governance components
audit_logger = AuditLogger("csl_audit.jsonl")
notification_service = NotificationService()
access_control = AccessControlManager()
approval_engine = ApprovalEngine(audit_logger, notification_service)

# Create API router
governance_router = APIRouter(prefix="/governance", tags=["governance"])

# Dependency to get current user (simplified - would use JWT/API keys)
async def get_current_user(request: Request) -> User:
    """Get current authenticated user."""
    # This would validate API token or JWT
    # For now, return a sample user
    return User(
        username="demo_user",
        email="demo@example.com",
        role=UserRole.STEWARD,
        teams=["analytics", "finance"]
    )

@governance_router.post("/changes", response_model=ApprovalRequest)
async def submit_semantic_change(
    change: SemanticChange,
    current_user: User = Depends(get_current_user)
):
    """Submit a semantic change for approval."""

    # Check if user can modify this metric
    if not access_control.can_write_metric(current_user.username, change.metric_name):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to modify this metric"
        )

    approval_request = approval_engine.submit_change(change, current_user)

    return approval_request

@governance_router.get("/approvals/pending", response_model=List[ApprovalRequest])
async def get_pending_approvals(
    current_user: User = Depends(get_current_user)
):
    """Get all pending approval requests."""

    if not access_control.check_permission(
        current_user.username, "approval", "read"
    ):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view approvals"
        )

    return approval_engine.get_pending_approvals()

@governance_router.post("/approvals/{approval_id}/approve")
async def approve_change(
    approval_id: str,
    comments: str = "",
    current_user: User = Depends(get_current_user)
):
    """Approve a pending semantic change."""

    try:
        approval_request = approval_engine.approve_change(
            approval_id, current_user, comments
        )
        return {
            "message": "Change approved successfully",
            "approval_request": approval_request
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@governance_router.post("/approvals/{approval_id}/reject")
async def reject_change(
    approval_id: str,
    reason: str,
    current_user: User = Depends(get_current_user)
):
    """Reject a pending semantic change."""

    if not reason.strip():
        raise HTTPException(
            status_code=400,
            detail="Rejection reason is required"
        )

    try:
        approval_request = approval_engine.reject_change(
            approval_id, current_user, reason
        )
        return {
            "message": "Change rejected successfully",
            "approval_request": approval_request
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@governance_router.get("/audit", response_model=List[AuditEntry])
async def get_audit_trail(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user: Optional[str] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get audit trail with optional filters."""

    if not access_control.can_view_audit(current_user.username):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view audit logs"
        )

    return audit_logger.get_audit_trail(
        start_date=start_date,
        end_date=end_date,
        user=user,
        resource_type=resource_type,
        action=action,
        limit=limit
    )

@governance_router.get("/audit/metrics/{metric_name}")
async def get_metric_history(
    metric_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get complete change history for a metric."""

    if not access_control.can_read_metric(current_user.username, metric_name):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view this metric's history"
        )

    return audit_logger.get_metric_history(metric_name)

@governance_router.post("/audit/compliance-report")
async def generate_compliance_report(
    start_date: datetime,
    end_date: datetime,
    current_user: User = Depends(get_current_user)
):
    """Generate compliance report for audit purposes."""

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can generate compliance reports"
        )

    return audit_logger.generate_compliance_report(start_date, end_date)

@governance_router.get("/users/me/permissions")
async def get_my_permissions(
    current_user: User = Depends(get_current_user)
):
    """Get current user's permissions summary."""

    return access_control.get_permission_summary(current_user.username)

@governance_router.get("/users/me/accessible-metrics")
async def get_my_accessible_metrics(
    current_user: User = Depends(get_current_user)
):
    """Get metrics accessible to current user."""

    accessible_metrics = access_control.get_accessible_metrics(current_user.username)

    return {
        "username": current_user.username,
        "accessible_metrics": accessible_metrics,
        "count": len(accessible_metrics)
    }

@governance_router.post("/users")
async def create_user(
    user: User,
    current_user: User = Depends(get_current_user)
):
    """Create a new user (admin only)."""

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can create users"
        )

    access_control.add_user(user)

    audit_logger.log_action(
        user=current_user.username,
        action="user_created",
        resource_type="user",
        resource_id=user.username,
        details={"role": user.role.value, "teams": user.teams}
    )

    return {"message": f"User {user.username} created successfully"}

@governance_router.post("/domains/{domain}/stewards/{username}")
async def assign_domain_steward(
    domain: str,
    username: str,
    current_user: User = Depends(get_current_user)
):
    """Assign user as steward for a domain."""

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can assign stewards"
        )

    access_control.assign_domain_steward(domain, username)

    audit_logger.log_action(
        user=current_user.username,
        action="steward_assigned",
        resource_type="domain",
        resource_id=domain,
        details={"steward": username}
    )

    return {
        "message": f"User {username} assigned as steward for domain {domain}"
    }

@governance_router.post("/metrics/{metric_name}/domain")
async def assign_metric_domain(
    metric_name: str,
    domain: str,
    current_user: User = Depends(get_current_user)
):
    """Assign metric to a domain."""

    if not access_control.can_write_metric(current_user.username, metric_name):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to modify this metric"
        )

    access_control.set_metric_domain(metric_name, domain)

    audit_logger.log_action(
        user=current_user.username,
        action="metric_domain_assigned",
        resource_type="metric",
        resource_id=metric_name,
        details={"domain": domain}
    )

    return {
        "message": f"Metric {metric_name} assigned to domain {domain}"
    }

@governance_router.post("/webhook/github")
async def handle_github_webhook(request: Request):
    """Handle GitHub webhook for PR-based workflows."""

    # Get headers and payload
    headers = dict(request.headers)
    payload = await request.body()

    # Initialize GitHub integration (would be configured)
    github_integration = GitHubWorkflowIntegration(
        repo_path=".",
        approval_engine=approval_engine,
        audit_logger=audit_logger,
        webhook_secret=None  # Would be configured
    )

    result = github_integration.handle_webhook(headers, payload)

    if result.get("status", 200) != 200:
        raise HTTPException(
            status_code=result["status"],
            detail=result.get("error", "Webhook processing failed")
        )

    return result

@governance_router.post("/notifications/test")
async def test_notifications(
    current_user: User = Depends(get_current_user)
):
    """Test all notification channels."""

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can test notifications"
        )

    results = notification_service.test_notifications()
    return {"test_results": results}

@governance_router.get("/health")
async def governance_health():
    """Check governance system health."""

    # Check audit log integrity
    audit_integrity = audit_logger.verify_integrity()

    # Check pending approvals
    pending_count = len(approval_engine.get_pending_approvals())

    return {
        "status": "healthy",
        "audit_integrity": audit_integrity,
        "pending_approvals": pending_count,
        "timestamp": datetime.now().isoformat()
    }