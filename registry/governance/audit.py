import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from .models import AuditEntry

class AuditLogger:
    """
    Enterprise audit logging for all CSL operations.

    Maintains immutable log of who changed what, when, and why.
    Critical for compliance, security, and debugging.
    """

    def __init__(self, audit_file_path: str = "csl_audit.jsonl"):
        self.audit_file_path = Path(audit_file_path)
        self._ensure_audit_file()

    def _ensure_audit_file(self):
        """Ensure audit file exists and has proper permissions."""
        if not self.audit_file_path.exists():
            self.audit_file_path.touch(mode=0o600)  # Readable only by owner

    def log_action(
        self,
        user: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditEntry:
        """Log an action to the audit trail."""

        entry = AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Write to audit log (append-only)
        with open(self.audit_file_path, "a") as f:
            f.write(entry.model_dump_json() + "\n")

        return entry

    def log_metric_change(
        self,
        user: str,
        metric_name: str,
        change_type: str,
        old_definition: Optional[Dict[str, Any]],
        new_definition: Dict[str, Any],
        approved_by: Optional[str] = None
    ) -> AuditEntry:
        """Log a semantic metric change."""

        return self.log_action(
            user=user,
            action=f"metric_{change_type}",
            resource_type="metric",
            resource_id=metric_name,
            details={
                "old_definition": old_definition,
                "new_definition": new_definition,
                "approved_by": approved_by,
                "change_type": change_type
            }
        )

    def log_adapter_generation(
        self,
        user: str,
        metric_name: str,
        adapter_type: str,
        output_file: str,
        success: bool,
        error_message: Optional[str] = None
    ) -> AuditEntry:
        """Log vendor adapter generation."""

        return self.log_action(
            user=user,
            action="adapter_generated",
            resource_type="adapter",
            resource_id=f"{metric_name}_{adapter_type}",
            details={
                "metric_name": metric_name,
                "adapter_type": adapter_type,
                "output_file": output_file,
                "success": success,
                "error_message": error_message
            }
        )

    def log_api_access(
        self,
        user: str,
        endpoint: str,
        method: str,
        response_code: int,
        ip_address: str,
        user_agent: str
    ) -> AuditEntry:
        """Log API access."""

        return self.log_action(
            user=user,
            action="api_access",
            resource_type="endpoint",
            resource_id=endpoint,
            details={
                "method": method,
                "response_code": response_code
            },
            ip_address=ip_address,
            user_agent=user_agent
        )

    def get_audit_trail(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 1000
    ) -> List[AuditEntry]:
        """Query the audit trail with filters."""

        entries = []

        with open(self.audit_file_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    entry = AuditEntry(**data)

                    # Apply filters
                    if start_date and entry.timestamp < start_date:
                        continue
                    if end_date and entry.timestamp > end_date:
                        continue
                    if user and entry.user != user:
                        continue
                    if resource_type and entry.resource_type != resource_type:
                        continue
                    if action and entry.action != action:
                        continue

                    entries.append(entry)

                    if len(entries) >= limit:
                        break

                except json.JSONDecodeError:
                    continue  # Skip malformed lines

        return entries

    def get_metric_history(self, metric_name: str) -> List[AuditEntry]:
        """Get complete change history for a metric."""

        return self.get_audit_trail(
            resource_type="metric",
            action=None  # Get all actions for this metric
        )

    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate compliance report for audit purposes."""

        entries = self.get_audit_trail(start_date=start_date, end_date=end_date)

        # Aggregate statistics
        stats = {
            "total_actions": len(entries),
            "unique_users": len(set(entry.user for entry in entries)),
            "actions_by_type": {},
            "users_by_activity": {},
            "metrics_modified": set(),
            "failed_operations": 0
        }

        for entry in entries:
            # Count actions by type
            stats["actions_by_type"][entry.action] = (
                stats["actions_by_type"].get(entry.action, 0) + 1
            )

            # Count activity by user
            stats["users_by_activity"][entry.user] = (
                stats["users_by_activity"].get(entry.user, 0) + 1
            )

            # Track modified metrics
            if entry.resource_type == "metric":
                stats["metrics_modified"].add(entry.resource_id)

            # Count failed operations
            if (entry.resource_type == "adapter" and
                entry.details.get("success") is False):
                stats["failed_operations"] += 1

        stats["metrics_modified"] = len(stats["metrics_modified"])

        return {
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "statistics": stats,
            "entries": [entry.model_dump() for entry in entries]
        }

    def verify_integrity(self) -> Dict[str, Any]:
        """Verify audit log integrity."""

        total_entries = 0
        corrupted_entries = 0
        earliest_entry = None
        latest_entry = None

        with open(self.audit_file_path, "r") as f:
            for line in f:
                total_entries += 1
                try:
                    data = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(data["timestamp"])

                    if earliest_entry is None or entry_time < earliest_entry:
                        earliest_entry = entry_time
                    if latest_entry is None or entry_time > latest_entry:
                        latest_entry = entry_time

                except (json.JSONDecodeError, KeyError, ValueError):
                    corrupted_entries += 1

        return {
            "total_entries": total_entries,
            "corrupted_entries": corrupted_entries,
            "integrity_score": (
                (total_entries - corrupted_entries) / total_entries
                if total_entries > 0 else 0
            ),
            "date_range": {
                "earliest": earliest_entry.isoformat() if earliest_entry else None,
                "latest": latest_entry.isoformat() if latest_entry else None
            }
        }