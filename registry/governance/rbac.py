from typing import Dict, List, Set, Optional
from enum import Enum
from .models import User, UserRole

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    APPROVE = "approve"
    DELETE = "delete"
    ADMIN = "admin"

class Resource(str, Enum):
    METRIC = "metric"
    DIMENSION = "dimension"
    ADAPTER = "adapter"
    APPROVAL = "approval"
    AUDIT = "audit"
    USER = "user"

class AccessControlManager:
    """
    Role-Based Access Control for CSL semantic definitions.

    Ensures proper permissions while maintaining enterprise security.
    Domain-based access control allows teams to manage their own metrics.
    """

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.domain_stewards: Dict[str, List[str]] = {}  # domain -> list of stewards
        self.metric_domains: Dict[str, str] = {}  # metric_name -> domain

        # Default role permissions
        self.role_permissions = {
            UserRole.ANALYST: {
                Resource.METRIC: [Permission.READ],
                Resource.DIMENSION: [Permission.READ],
                Resource.ADAPTER: [Permission.READ],
            },
            UserRole.STEWARD: {
                Resource.METRIC: [Permission.READ, Permission.WRITE, Permission.APPROVE],
                Resource.DIMENSION: [Permission.READ, Permission.WRITE, Permission.APPROVE],
                Resource.ADAPTER: [Permission.READ, Permission.WRITE],
                Resource.APPROVAL: [Permission.READ, Permission.WRITE],
                Resource.AUDIT: [Permission.READ],
            },
            UserRole.ADMIN: {
                Resource.METRIC: [Permission.READ, Permission.WRITE, Permission.APPROVE, Permission.DELETE, Permission.ADMIN],
                Resource.DIMENSION: [Permission.READ, Permission.WRITE, Permission.APPROVE, Permission.DELETE, Permission.ADMIN],
                Resource.ADAPTER: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
                Resource.APPROVAL: [Permission.READ, Permission.WRITE, Permission.APPROVE, Permission.DELETE, Permission.ADMIN],
                Resource.AUDIT: [Permission.READ, Permission.ADMIN],
                Resource.USER: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
            }
        }

    def add_user(self, user: User):
        """Add a user to the RBAC system."""
        self.users[user.username] = user

    def assign_domain_steward(self, domain: str, username: str):
        """Assign a user as steward for a specific domain."""
        if domain not in self.domain_stewards:
            self.domain_stewards[domain] = []

        if username not in self.domain_stewards[domain]:
            self.domain_stewards[domain].append(username)

        # Update user's teams
        if username in self.users:
            user = self.users[username]
            if domain not in user.teams:
                user.teams.append(domain)

    def set_metric_domain(self, metric_name: str, domain: str):
        """Assign a metric to a domain."""
        self.metric_domains[metric_name] = domain

    def check_permission(
        self,
        username: str,
        resource: Resource,
        permission: Permission,
        resource_id: Optional[str] = None
    ) -> bool:
        """Check if user has specific permission for a resource."""

        if username not in self.users:
            return False

        user = self.users[username]

        # Check role-based permissions
        role_perms = self.role_permissions.get(user.role, {})
        if resource not in role_perms:
            return False

        if permission not in role_perms[resource]:
            return False

        # For domain-specific resources, check domain access
        if resource in [Resource.METRIC, Resource.DIMENSION] and resource_id:
            return self._check_domain_access(user, resource_id)

        # Check custom user permissions
        user_perms = user.permissions.get(resource.value, [])
        if permission.value in user_perms:
            return True

        return True  # Default allow if role permits

    def _check_domain_access(self, user: User, resource_id: str) -> bool:
        """Check if user has access to a specific domain resource."""

        # Admins have access to everything
        if user.role == UserRole.ADMIN:
            return True

        # Check if resource belongs to a domain the user has access to
        domain = self.metric_domains.get(resource_id)
        if not domain:
            # If no domain assigned, allow access based on role
            return True

        # Check if user is in the domain team
        if domain in user.teams:
            return True

        # Check if user is a steward for this domain
        if domain in self.domain_stewards:
            if user.username in self.domain_stewards[domain]:
                return True

        return False

    def can_read_metric(self, username: str, metric_name: str) -> bool:
        """Check if user can read a specific metric."""
        return self.check_permission(username, Resource.METRIC, Permission.READ, metric_name)

    def can_write_metric(self, username: str, metric_name: str) -> bool:
        """Check if user can modify a specific metric."""
        return self.check_permission(username, Resource.METRIC, Permission.WRITE, metric_name)

    def can_approve_changes(self, username: str, metric_name: str) -> bool:
        """Check if user can approve changes to a specific metric."""
        return self.check_permission(username, Resource.METRIC, Permission.APPROVE, metric_name)

    def can_delete_metric(self, username: str, metric_name: str) -> bool:
        """Check if user can delete a specific metric."""
        return self.check_permission(username, Resource.METRIC, Permission.DELETE, metric_name)

    def can_generate_adapter(self, username: str) -> bool:
        """Check if user can generate adapter outputs."""
        return self.check_permission(username, Resource.ADAPTER, Permission.READ)

    def can_view_audit(self, username: str) -> bool:
        """Check if user can view audit logs."""
        return self.check_permission(username, Resource.AUDIT, Permission.READ)

    def get_user_domains(self, username: str) -> List[str]:
        """Get domains a user has access to."""
        if username not in self.users:
            return []

        user = self.users[username]
        domains = set(user.teams)

        # Add domains where user is a steward
        for domain, stewards in self.domain_stewards.items():
            if username in stewards:
                domains.add(domain)

        return list(domains)

    def get_accessible_metrics(self, username: str) -> List[str]:
        """Get all metrics a user can access."""
        if username not in self.users:
            return []

        user = self.users[username]

        # Admins can access everything
        if user.role == UserRole.ADMIN:
            return list(self.metric_domains.keys())

        accessible = []
        user_domains = self.get_user_domains(username)

        for metric_name, domain in self.metric_domains.items():
            if domain in user_domains or domain is None:
                accessible.append(metric_name)

        return accessible

    def create_api_token(self, username: str, permissions: Dict[str, List[str]]) -> str:
        """Create API token with specific permissions."""
        # This would integrate with JWT or similar token system
        # For now, return a placeholder
        import uuid
        return f"csl_token_{uuid.uuid4().hex}"

    def validate_api_token(self, token: str) -> Optional[Dict[str, any]]:
        """Validate API token and return user info and permissions."""
        # This would validate JWT or lookup in token store
        # For now, return placeholder
        if token.startswith("csl_token_"):
            return {
                "username": "api_user",
                "permissions": {"metric": ["read", "write"]},
                "expires_at": None
            }
        return None

    def get_permission_summary(self, username: str) -> Dict[str, any]:
        """Get comprehensive permission summary for a user."""
        if username not in self.users:
            return {"error": "User not found"}

        user = self.users[username]
        domains = self.get_user_domains(username)
        accessible_metrics = self.get_accessible_metrics(username)

        return {
            "username": user.username,
            "role": user.role.value,
            "teams": user.teams,
            "domains": domains,
            "accessible_metrics_count": len(accessible_metrics),
            "permissions": {
                "can_read_metrics": len(accessible_metrics) > 0,
                "can_write_metrics": user.role in [UserRole.STEWARD, UserRole.ADMIN],
                "can_approve_changes": user.role in [UserRole.STEWARD, UserRole.ADMIN],
                "can_delete_metrics": user.role == UserRole.ADMIN,
                "can_manage_users": user.role == UserRole.ADMIN,
                "can_view_audit": user.role in [UserRole.STEWARD, UserRole.ADMIN]
            }
        }