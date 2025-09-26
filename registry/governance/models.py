from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"

class ChangeType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

class UserRole(str, Enum):
    ANALYST = "analyst"
    STEWARD = "steward"
    ADMIN = "admin"

class User(BaseModel):
    username: str
    email: str
    role: UserRole
    teams: List[str] = []
    permissions: Dict[str, List[str]] = {}  # domain -> [read, write, approve]

class SemanticChange(BaseModel):
    id: str
    change_type: ChangeType
    metric_name: str
    old_definition: Optional[Dict[str, Any]] = None
    new_definition: Dict[str, Any]
    author: str
    author_email: str
    created_at: datetime
    description: str
    justification: str
    affected_adapters: List[str] = []
    breaking_change: bool = False

class ApprovalRequest(BaseModel):
    id: str
    change_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: Optional[str] = None
    approved_at: Optional[datetime] = None
    comments: str = ""
    auto_approved: bool = False
    approval_criteria: Dict[str, Any] = {}

class AuditEntry(BaseModel):
    id: str
    timestamp: datetime
    user: str
    action: str
    resource_type: str  # metric, dimension, approval
    resource_id: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class GovernancePolicy(BaseModel):
    name: str
    description: str
    rules: List[Dict[str, Any]]
    auto_approval_criteria: List[Dict[str, Any]] = []
    required_approvers: int = 1
    steward_domains: List[str] = []
    notification_channels: List[str] = []

class WorkflowConfig(BaseModel):
    approval_required: bool = True
    auto_approve_non_breaking: bool = False
    require_justification: bool = True
    require_testing: bool = True
    max_pending_days: int = 7
    notification_enabled: bool = True
    slack_webhook: Optional[str] = None
    teams_webhook: Optional[str] = None