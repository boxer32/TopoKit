"""Compliance type definitions for TopoKit."""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    GDPR = "gdpr"
    CCPA = "ccpa"
    SOX = "sox"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"


class DataClassification(str, Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class PIIType(str, Enum):
    """Types of personally identifiable information."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    ADDRESS = "address"


@dataclass
class ComplianceRule:
    """Compliance rule definition."""
    id: str
    framework: ComplianceFramework
    name: str
    description: str
    severity: str  # critical, high, medium, low
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)


@dataclass
class AuditEvent:
    """Audit event record."""
    id: str
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    event_type: str = ""
    resource: str = ""
    action: str = ""
    result: str = ""  # success, failure, denied
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    compliance_frameworks: List[ComplianceFramework] = field(default_factory=list)
    hash: Optional[str] = None  # Tamper-evident hash


@dataclass
class DataRetentionPolicy:
    """Data retention policy."""
    id: str
    name: str
    data_types: List[str]
    retention_period_days: int
    auto_delete: bool = True
    encryption_required: bool = True
    audit_required: bool = True


@dataclass
class ComplianceCheckResult:
    """Result of a compliance check."""
    compliant: bool
    violations: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    required_actions: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.now)


@dataclass
class PIIDetectionResult:
    """Result of PII detection and redaction."""
    original: Any
    redacted: Any
    pii_findings: List[Dict[str, Any]] = field(default_factory=list)
    has_pii: bool = False
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class AuditReport:
    """Compliance audit report."""
    period: Dict[str, str]  # start, end ISO format
    total_events: int
    events_by_type: Dict[str, int] = field(default_factory=dict)
    events_by_result: Dict[str, int] = field(default_factory=dict)
    compliance_violations: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ComplianceConfig:
    """Compliance configuration."""
    enable_gdpr: bool = True
    enable_ccpa: bool = True
    enable_sox: bool = True
    enable_hipaa: bool = True
    audit_endpoint: Optional[str] = None
    data_retention_days: int = 2555  # 7 years default
    pii_redaction_enabled: bool = True
    audit_log_encryption: bool = True

