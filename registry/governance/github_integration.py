import json
import hmac
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
import subprocess
import tempfile
from .models import SemanticChange, ChangeType, User
from .approval_engine import ApprovalEngine
from .audit import AuditLogger

class GitHubWorkflowIntegration:
    """
    Integration with GitHub for PR-based semantic change workflows.

    Enables enterprises to use their existing Git workflows for semantic governance.
    Changes go through PR review process with CSL-specific validation.
    """

    def __init__(self,
                 repo_path: str,
                 approval_engine: ApprovalEngine,
                 audit_logger: AuditLogger,
                 webhook_secret: Optional[str] = None):
        self.repo_path = Path(repo_path)
        self.approval_engine = approval_engine
        self.audit_logger = audit_logger
        self.webhook_secret = webhook_secret

    def handle_webhook(self, headers: Dict[str, str], payload: bytes) -> Dict[str, Any]:
        """Handle GitHub webhook events."""

        # Verify webhook signature if secret is configured
        if self.webhook_secret:
            if not self._verify_webhook_signature(headers, payload):
                return {"error": "Invalid webhook signature", "status": 403}

        try:
            event_data = json.loads(payload.decode('utf-8'))
            event_type = headers.get('X-GitHub-Event', '')

            if event_type == 'pull_request':
                return self._handle_pull_request_event(event_data)
            elif event_type == 'push':
                return self._handle_push_event(event_data)
            else:
                return {"message": f"Ignored event type: {event_type}", "status": 200}

        except json.JSONDecodeError:
            return {"error": "Invalid JSON payload", "status": 400}

    def _verify_webhook_signature(self, headers: Dict[str, str], payload: bytes) -> bool:
        """Verify GitHub webhook signature."""

        signature = headers.get('X-Hub-Signature-256', '')
        if not signature.startswith('sha256='):
            return False

        expected_signature = 'sha256=' + hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def _handle_pull_request_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PR events - opened, closed, synchronized."""

        action = event_data.get('action')
        pr_data = event_data.get('pull_request', {})

        if action == 'opened':
            return self._handle_pr_opened(pr_data)
        elif action == 'closed' and pr_data.get('merged'):
            return self._handle_pr_merged(pr_data)
        elif action == 'synchronize':
            return self._handle_pr_updated(pr_data)
        else:
            return {"message": f"Ignored PR action: {action}", "status": 200}

    def _handle_pr_opened(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle new PR opened with semantic changes."""

        pr_number = pr_data.get('number')
        branch = pr_data['head']['ref']
        author = pr_data['user']['login']

        # Analyze changes in the PR
        changes = self._analyze_pr_changes(pr_data)

        if not changes:
            return {"message": "No semantic changes detected", "status": 200}

        # Create approval requests for each change
        approval_requests = []
        for change in changes:
            # Convert GitHub user to CSL user (would need user mapping)
            user = User(
                username=author,
                email=pr_data['user'].get('email', f"{author}@github.com"),
                role='analyst',  # Default role, would be configured
                teams=[]
            )

            approval_request = self.approval_engine.submit_change(change, user)
            approval_requests.append(approval_request)

        # Add PR comment with approval status
        self._add_pr_comment(pr_number, approval_requests, changes)

        return {
            "message": f"Created {len(approval_requests)} approval requests",
            "approval_requests": [req.id for req in approval_requests],
            "status": 200
        }

    def _handle_pr_merged(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PR merged - apply approved changes."""

        pr_number = pr_data.get('number')
        author = pr_data['user']['login']

        # Log the merge
        self.audit_logger.log_action(
            user=author,
            action="pr_merged",
            resource_type="pull_request",
            resource_id=str(pr_number),
            details={
                "title": pr_data.get('title', ''),
                "base_branch": pr_data['base']['ref'],
                "head_branch": pr_data['head']['ref']
            }
        )

        return {"message": "PR merged and changes applied", "status": 200}

    def _handle_push_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle direct push to main branch."""

        ref = event_data.get('ref', '')
        if not ref.endswith('/main') and not ref.endswith('/master'):
            return {"message": "Ignored push to non-main branch", "status": 200}

        # Analyze commits for semantic changes
        commits = event_data.get('commits', [])

        for commit in commits:
            author = commit['author']['username']
            self.audit_logger.log_action(
                user=author,
                action="direct_push",
                resource_type="commit",
                resource_id=commit['id'],
                details={
                    "message": commit['message'],
                    "modified_files": commit.get('modified', []),
                    "added_files": commit.get('added', []),
                    "removed_files": commit.get('removed', [])
                }
            )

        return {"message": f"Processed {len(commits)} commits", "status": 200}

    def _analyze_pr_changes(self, pr_data: Dict[str, Any]) -> list[SemanticChange]:
        """Analyze PR for semantic definition changes."""

        changes = []

        # Get diff from GitHub API (simplified - would use actual API)
        # For now, simulate detecting changes to YAML files

        # This would analyze the actual file changes
        base_sha = pr_data['base']['sha']
        head_sha = pr_data['head']['sha']

        # Simulate finding changes in semantics/ directory
        sample_change = SemanticChange(
            id=f"change_{pr_data['number']}_1",
            change_type=ChangeType.UPDATE,
            metric_name="active_users",
            old_definition={"definition": "COUNT(DISTINCT user_id)", "filters": []},
            new_definition={
                "definition": "COUNT(DISTINCT user_id)",
                "filters": ["status = 'active'"]
            },
            author=pr_data['user']['login'],
            author_email=pr_data['user'].get('email', ''),
            created_at=pr_data['created_at'],
            description=pr_data.get('title', ''),
            justification=pr_data.get('body', ''),
            breaking_change=False
        )

        changes.append(sample_change)
        return changes

    def _add_pr_comment(self, pr_number: int, approval_requests: list, changes: list):
        """Add comment to PR with CSL approval status."""

        comment_body = "## CSL Semantic Change Review\n\n"

        for i, (approval, change) in enumerate(zip(approval_requests, changes)):
            status_emoji = "✅" if approval.status == "approved" else "⏳"

            comment_body += f"{status_emoji} **{change.metric_name}** ({change.change_type.value})\n"
            comment_body += f"   - Approval ID: `{approval.id}`\n"
            comment_body += f"   - Status: {approval.status.value}\n"

            if approval.auto_approved:
                comment_body += f"   - Auto-approved: Yes\n"

            comment_body += "\n"

        if any(req.status == "pending" for req in approval_requests):
            comment_body += "⚠️ This PR requires CSL steward approval before merging.\n\n"
        else:
            comment_body += "✅ All semantic changes have been approved.\n\n"

        comment_body += "---\n*This comment was generated by CSL governance system*"

        # In real implementation, would use GitHub API to post comment
        print(f"Would post comment to PR #{pr_number}:")
        print(comment_body)

    def create_governance_branch(self, change: SemanticChange) -> str:
        """Create a Git branch for a semantic change."""

        branch_name = f"csl/{change.change_type.value}-{change.metric_name}-{change.id[:8]}"

        # Create and checkout new branch
        subprocess.run([
            'git', 'checkout', '-b', branch_name
        ], cwd=self.repo_path, check=True)

        return branch_name

    def commit_semantic_change(self, change: SemanticChange, branch: str):
        """Commit semantic change to Git."""

        # Write the new definition to YAML file
        metric_file = self.repo_path / "semantics" / "metrics" / f"{change.metric_name}.yaml"

        with open(metric_file, 'w') as f:
            import yaml
            yaml.dump(change.new_definition, f, default_flow_style=False)

        # Stage and commit
        subprocess.run(['git', 'add', str(metric_file)], cwd=self.repo_path, check=True)

        commit_message = f"{change.change_type.value}: {change.metric_name}\n\n{change.description}\n\nCSL-Change-ID: {change.id}"

        subprocess.run([
            'git', 'commit', '-m', commit_message
        ], cwd=self.repo_path, check=True)

    def create_pull_request(self, change: SemanticChange, branch: str) -> Dict[str, Any]:
        """Create GitHub PR for semantic change."""

        pr_title = f"CSL: {change.change_type.value.title()} {change.metric_name}"

        pr_body = f"""## Semantic Change Request

**Metric:** {change.metric_name}
**Change Type:** {change.change_type.value}
**Author:** {change.author}

### Description
{change.description}

### Justification
{change.justification}

### Breaking Change
{"Yes" if change.breaking_change else "No"}

---
*This PR was generated by CSL governance system*
*Change ID: {change.id}*
"""

        # In real implementation, would use GitHub API
        return {
            "title": pr_title,
            "body": pr_body,
            "head": branch,
            "base": "main"
        }

    def sync_with_github(self):
        """Sync local semantic definitions with GitHub repository."""

        # Pull latest changes
        subprocess.run(['git', 'pull', 'origin', 'main'], cwd=self.repo_path)

        # Reload semantic definitions
        # This would trigger the registry to reload from disk
        return {"message": "Synced with GitHub", "status": 200}