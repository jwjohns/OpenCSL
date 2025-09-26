import json
import requests
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    def send(self, message: str, metadata: Dict[str, Any] = None) -> bool:
        pass

class SlackNotification(NotificationChannel):
    """Slack notification channel."""

    def __init__(self, webhook_url: str, channel: str = None):
        self.webhook_url = webhook_url
        self.default_channel = channel

    def send(self, message: str, metadata: Dict[str, Any] = None) -> bool:
        payload = {
            "text": message,
            "username": "CSL Governance",
            "icon_emoji": ":shield:"
        }

        if self.default_channel:
            payload["channel"] = self.default_channel

        # Add rich formatting for approval requests
        if metadata and metadata.get("approval_id"):
            payload["attachments"] = [{
                "color": "warning" if metadata.get("decision") != "approved" else "good",
                "fields": [
                    {
                        "title": "Approval ID",
                        "value": metadata["approval_id"],
                        "short": True
                    },
                    {
                        "title": "Change Type",
                        "value": metadata.get("change_type", "unknown"),
                        "short": True
                    }
                ]
            }]

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

class TeamsNotification(NotificationChannel):
    """Microsoft Teams notification channel."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, message: str, metadata: Dict[str, Any] = None) -> bool:
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": "CSL Governance Notification",
            "themeColor": "0078D4",
            "title": "Customer Semantic Layer",
            "text": message
        }

        # Add action buttons for approval requests
        if metadata and metadata.get("approval_id"):
            payload["potentialAction"] = [{
                "@type": "OpenUri",
                "name": "View Approval",
                "targets": [{
                    "os": "default",
                    "uri": f"https://your-csl-instance.com/approvals/{metadata['approval_id']}"
                }]
            }]

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

class EmailNotification(NotificationChannel):
    """Email notification channel."""

    def __init__(self, smtp_config: Dict[str, Any]):
        self.smtp_config = smtp_config

    def send(self, message: str, metadata: Dict[str, Any] = None) -> bool:
        # This would implement SMTP email sending
        # For now, just log the notification
        print(f"EMAIL NOTIFICATION: {message}")
        return True

class NotificationService:
    """
    Centralized notification service for CSL governance events.

    Routes notifications to appropriate channels based on event type and user preferences.
    """

    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}
        self.channel_routing: Dict[str, list[str]] = {
            "stewards": ["slack_stewards", "teams_stewards"],
            "general": ["slack_general"],
            "critical": ["slack_stewards", "teams_stewards", "email_admins"]
        }

    def add_channel(self, name: str, channel: NotificationChannel):
        """Add a notification channel."""
        self.channels[name] = channel

    def send_notification(
        self,
        channel: str,
        message: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, bool]:
        """Send notification to specified channel group."""

        if channel not in self.channel_routing:
            return {"error": f"Unknown channel group: {channel}"}

        results = {}
        target_channels = self.channel_routing[channel]

        for channel_name in target_channels:
            if channel_name in self.channels:
                success = self.channels[channel_name].send(message, metadata)
                results[channel_name] = success
            else:
                results[channel_name] = False

        return results

    def notify_approval_request(
        self,
        metric_name: str,
        change_type: str,
        author: str,
        approval_id: str,
        breaking_change: bool = False
    ):
        """Send notification for new approval request."""

        urgency = "critical" if breaking_change else "stewards"

        message = f"""
🔄 **Semantic Change Approval Required**

**Metric:** {metric_name}
**Type:** {change_type}
**Author:** {author}
**Breaking Change:** {"⚠️ YES" if breaking_change else "✅ No"}

Please review this change and approve/reject as appropriate.

**Approval ID:** {approval_id}
        """.strip()

        return self.send_notification(
            urgency,
            message,
            {
                "approval_id": approval_id,
                "change_type": change_type,
                "breaking_change": breaking_change
            }
        )

    def notify_approval_decision(
        self,
        metric_name: str,
        decision: str,
        approver: str,
        approval_id: str,
        comments: str = ""
    ):
        """Send notification for approval decision."""

        emoji = "✅" if decision == "approved" else "❌"

        message = f"""
{emoji} **Semantic Change {decision.title()}**

**Metric:** {metric_name}
**Decision:** {decision}
**Approver:** {approver}
**Comments:** {comments or "None"}

**Approval ID:** {approval_id}
        """.strip()

        return self.send_notification(
            "general",
            message,
            {
                "approval_id": approval_id,
                "decision": decision
            }
        )

    def notify_stale_approvals(self, stale_approvals: list[Dict[str, Any]]):
        """Send notification about stale approval requests."""

        if not stale_approvals:
            return

        message = f"""
⚠️ **{len(stale_approvals)} Stale Approval Requests**

The following approval requests have been pending for more than 7 days:

"""

        for approval in stale_approvals:
            message += f"• {approval['metric_name']} ({approval['change_type']}) - {approval['days_pending']} days\n"

        message += "\nPlease review these requests to maintain governance compliance."

        return self.send_notification("critical", message)

    def notify_system_event(self, event_type: str, details: Dict[str, Any]):
        """Send notification for system events."""

        message = f"""
🔧 **CSL System Event: {event_type}**

{details.get('message', 'No additional details')}

**Timestamp:** {details.get('timestamp', 'Unknown')}
**Affected Components:** {', '.join(details.get('components', []))}
        """.strip()

        channel = "critical" if details.get("severity") == "high" else "general"

        return self.send_notification(channel, message, details)

    def test_notifications(self) -> Dict[str, Any]:
        """Test all configured notification channels."""

        test_message = "🧪 CSL Notification System Test - This is a test message."
        results = {}

        for channel_name, channel in self.channels.items():
            try:
                success = channel.send(test_message, {"test": True})
                results[channel_name] = {
                    "status": "success" if success else "failed",
                    "error": None
                }
            except Exception as e:
                results[channel_name] = {
                    "status": "error",
                    "error": str(e)
                }

        return results