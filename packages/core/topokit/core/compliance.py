"""Enterprise compliance and governance framework for TopoKit."""

import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime, timezone, timedelta
import logging
import re

from .config import ComplianceConfig
from .logging import get_logger
from .audit import AuditTrailManager
from .data_lifecycle import DataLifecycleManager
from ..types.compliance import (
    ComplianceFramework,
    DataClassification,
    PIIType,
    ComplianceRule,
    AuditEvent,
    DataRetentionPolicy,
    ComplianceCheckResult,
    PIIDetectionResult,
    AuditReport
)


class PIIDetector:
    """PII detection and redaction engine."""
    
    def __init__(self):
        """Initialize PII detector with patterns."""
        self.patterns = {
            PIIType.EMAIL: re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            PIIType.PHONE: re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
            PIIType.SSN: re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
            PIIType.CREDIT_CARD: re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            PIIType.IP_ADDRESS: re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
        }
    
    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """Detect PII in text."""
        findings = []
        
        for pii_type, pattern in self.patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                findings.append({
                    "type": pii_type.value,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9
                })
        
        return findings
    
    def redact_pii(self, text: str, replacement: str = "[REDACTED]") -> str:
        """Redact PII from text."""
        redacted_text = text
        
        for pii_type, pattern in self.patterns.items():
            redacted_text = pattern.sub(replacement, redacted_text)
        
        return redacted_text


class ComplianceEngine:
    """Enterprise compliance and governance engine."""
    
    def __init__(self, config: Optional[ComplianceConfig] = None):
        """Initialize compliance engine."""
        self.config = config or ComplianceConfig()
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.pii_detector = PIIDetector()
        self.audit_manager = AuditTrailManager(audit_endpoint=self.config.audit_endpoint)
        self.data_lifecycle_manager = DataLifecycleManager()
        self.compliance_rules: Dict[str, ComplianceRule] = {}
        
        # Load default compliance rules
        self._load_default_rules()
    
    @property
    def retention_policies(self) -> Dict[str, DataRetentionPolicy]:
        """Get retention policies from data lifecycle manager."""
        return self.data_lifecycle_manager.retention_policies
    
    @property
    def audit_events(self) -> List[AuditEvent]:
        """Get audit events from audit manager."""
        return self.audit_manager.audit_events
    
    def _load_default_rules(self):
        """Load default compliance rules."""
        # GDPR rules
        self.compliance_rules["gdpr_data_minimization"] = ComplianceRule(
            id="gdpr_data_minimization",
            framework=ComplianceFramework.GDPR,
            name="Data Minimization",
            description="Ensure only necessary data is collected and processed",
            severity="high",
            conditions={"data_types": ["pii", "sensitive"]},
            actions=["audit", "encrypt", "retention_check"]
        )
        
        self.compliance_rules["gdpr_consent"] = ComplianceRule(
            id="gdpr_consent",
            framework=ComplianceFramework.GDPR,
            name="Consent Management",
            description="Ensure proper consent is obtained for data processing",
            severity="critical",
            conditions={"requires_consent": True},
            actions=["audit", "block_if_no_consent"]
        )
        
        # SOX rules
        self.compliance_rules["sox_audit_trail"] = ComplianceRule(
            id="sox_audit_trail",
            framework=ComplianceFramework.SOX,
            name="Audit Trail",
            description="Maintain comprehensive audit trails for financial data",
            severity="critical",
            conditions={"data_types": ["financial", "accounting"]},
            actions=["audit", "immutable_log", "retention_7_years"]
        )
        
        # CCPA rules
        self.compliance_rules["ccpa_consumer_rights"] = ComplianceRule(
            id="ccpa_consumer_rights",
            framework=ComplianceFramework.CCPA,
            name="Consumer Rights",
            description="Respect consumer rights to know, delete, and opt-out",
            severity="high",
            conditions={"data_types": ["consumer_data", "pii"]},
            actions=["audit", "allow_deletion", "opt_out_mechanism"]
        )
        
        self.compliance_rules["ccpa_opt_out"] = ComplianceRule(
            id="ccpa_opt_out",
            framework=ComplianceFramework.CCPA,
            name="Opt-Out Mechanism",
            description="Provide mechanism for consumers to opt-out of data sale",
            severity="critical",
            conditions={"requires_opt_out": True},
            actions=["audit", "block_sale_if_opted_out"]
        )
        
        # HIPAA rules
        self.compliance_rules["hipaa_phi_protection"] = ComplianceRule(
            id="hipaa_phi_protection",
            framework=ComplianceFramework.HIPAA,
            name="PHI Protection",
            description="Protect protected health information",
            severity="critical",
            conditions={"data_types": ["phi", "medical"]},
            actions=["encrypt", "audit", "access_control"]
        )
        
        self.compliance_rules["hipaa_minimum_necessary"] = ComplianceRule(
            id="hipaa_minimum_necessary",
            framework=ComplianceFramework.HIPAA,
            name="Minimum Necessary",
            description="Only access minimum necessary PHI",
            severity="high",
            conditions={"data_types": ["phi"]},
            actions=["audit", "access_control", "restrict_scope"]
        )
    
    async def check_compliance(self, data: Any, context: Dict[str, Any]) -> ComplianceCheckResult:
        """Check data against compliance rules."""
        results = ComplianceCheckResult(
            compliant=True,
            violations=[],
            recommendations=[],
            required_actions=[]
        )
        
        # Check each compliance rule
        for rule_id, rule in self.compliance_rules.items():
            if not rule.enabled:
                continue
            
            violation = await self._check_rule(rule, data, context)
            if violation:
                results.violations.append(violation)
                results.compliant = False
                results.required_actions.extend(rule.actions)
        
        return results
    
    async def _check_rule(self, rule: ComplianceRule, data: Any, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check a specific compliance rule."""
        # Check conditions
        if rule.framework == ComplianceFramework.GDPR:
            return await self._check_gdpr_rule(rule, data, context)
        elif rule.framework == ComplianceFramework.CCPA:
            return await self._check_ccpa_rule(rule, data, context)
        elif rule.framework == ComplianceFramework.SOX:
            return await self._check_sox_rule(rule, data, context)
        elif rule.framework == ComplianceFramework.HIPAA:
            return await self._check_hipaa_rule(rule, data, context)
        
        return None
    
    async def _check_gdpr_rule(self, rule: ComplianceRule, data: Any, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check GDPR compliance rules."""
        if rule.id == "gdpr_data_minimization":
            # Check if data contains unnecessary PII
            if isinstance(data, str):
                pii_findings = self.pii_detector.detect_pii(data)
                if pii_findings and not context.get("consent_given", False):
                    return {
                        "rule_id": rule.id,
                        "severity": rule.severity,
                        "message": "PII detected without proper consent",
                        "pii_findings": pii_findings
                    }
        
        elif rule.id == "gdpr_consent":
            # Check if consent is properly obtained
            if not context.get("consent_given", False) and context.get("requires_consent", False):
                return {
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "message": "Data processing requires explicit consent"
                }
        
        return None
    
    async def _check_ccpa_rule(self, rule: ComplianceRule, data: Any, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check CCPA compliance rules."""
        if rule.id == "ccpa_consumer_rights":
            # Check if consumer data is being processed with proper consent
            if context.get("data_type") in ["consumer_data", "pii"] and not context.get("consumer_consent", False):
                return {
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "message": "Consumer data processing requires proper consent"
                }
        
        elif rule.id == "ccpa_opt_out":
            # Check if consumer has opted out
            if context.get("requires_opt_out", False) and context.get("consumer_opted_out", False):
                return {
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "message": "Consumer has opted out of data sale"
                }
        
        return None
    
    async def _check_sox_rule(self, rule: ComplianceRule, data: Any, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check SOX compliance rules."""
        if rule.id == "sox_audit_trail":
            # Ensure audit trail is maintained
            if not context.get("audit_logged", False) and context.get("data_type") == "financial":
                return {
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "message": "Financial data must be audit logged"
                }
        
        return None
    
    async def _check_hipaa_rule(self, rule: ComplianceRule, data: Any, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check HIPAA compliance rules."""
        if rule.id == "hipaa_phi_protection":
            # Check if PHI is properly protected
            if context.get("data_type") == "phi" and not context.get("encrypted", False):
                return {
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "message": "PHI must be encrypted"
                }
        
        elif rule.id == "hipaa_minimum_necessary":
            # Check if minimum necessary PHI is being accessed
            if context.get("data_type") == "phi" and context.get("access_scope") and context.get("access_scope") != "minimum_necessary":
                return {
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "message": "HIPAA requires minimum necessary PHI access"
                }
        
        return None
    
    async def log_audit_event(self, event: AuditEvent):
        """Log an audit event."""
        # Use audit manager for logging
        self.audit_manager.log_event(event)
    
    def detect_and_redact_pii(self, data: Any, enforce_privacy_layer: bool = True) -> PIIDetectionResult:
        """Detect and redact PII from data with privacy layer enforcement."""
        if not self.config.pii_redaction_enabled and enforce_privacy_layer:
            # Privacy layer enforcement: if redaction is disabled but enforcement is required,
            # we still need to detect and log PII presence
            result = self._detect_only(data)
            if result.has_pii:
                self.logger.warning("PII detected but redaction is disabled - privacy risk")
            return result
        
        if isinstance(data, str):
            findings = self.pii_detector.detect_pii(data)
            redacted_data = self.pii_detector.redact_pii(data) if enforce_privacy_layer else data
            
            return PIIDetectionResult(
                original=data,
                redacted=redacted_data,
                pii_findings=findings,
                has_pii=len(findings) > 0
            )
        elif isinstance(data, dict):
            redacted_data = {}
            all_findings = []
            
            for key, value in data.items():
                if isinstance(value, str):
                    findings = self.pii_detector.detect_pii(value)
                    redacted_value = self.pii_detector.redact_pii(value) if enforce_privacy_layer else value
                    redacted_data[key] = redacted_value
                    all_findings.extend(findings)
                elif isinstance(value, dict):
                    # Recursively process nested dictionaries
                    nested_result = self.detect_and_redact_pii(value, enforce_privacy_layer)
                    redacted_data[key] = nested_result.redacted
                    all_findings.extend(nested_result.pii_findings)
                elif isinstance(value, list):
                    # Process list items
                    redacted_list = []
                    for item in value:
                        if isinstance(item, (str, dict)):
                            item_result = self.detect_and_redact_pii(item, enforce_privacy_layer)
                            redacted_list.append(item_result.redacted)
                            all_findings.extend(item_result.pii_findings)
                        else:
                            redacted_list.append(item)
                    redacted_data[key] = redacted_list
                else:
                    redacted_data[key] = value
            
            return PIIDetectionResult(
                original=data,
                redacted=redacted_data,
                pii_findings=all_findings,
                has_pii=len(all_findings) > 0
            )
        
        return PIIDetectionResult(
            original=data,
            redacted=data,
            pii_findings=[],
            has_pii=False
        )
    
    def _detect_only(self, data: Any) -> PIIDetectionResult:
        """Detect PII without redaction (for logging/monitoring)."""
        if isinstance(data, str):
            findings = self.pii_detector.detect_pii(data)
            return PIIDetectionResult(
                original=data,
                redacted=data,
                pii_findings=findings,
                has_pii=len(findings) > 0
            )
        elif isinstance(data, dict):
            all_findings = []
            for key, value in data.items():
                if isinstance(value, str):
                    findings = self.pii_detector.detect_pii(value)
                    all_findings.extend(findings)
                elif isinstance(value, dict):
                    nested_result = self._detect_only(value)
                    all_findings.extend(nested_result.pii_findings)
            
            return PIIDetectionResult(
                original=data,
                redacted=data,
                pii_findings=all_findings,
                has_pii=len(all_findings) > 0
            )
        
        return PIIDetectionResult(
            original=data,
            redacted=data,
            pii_findings=[],
            has_pii=False
        )
    
    def get_audit_report(self, start_date: datetime, end_date: datetime, 
                        frameworks: Optional[List[ComplianceFramework]] = None) -> AuditReport:
        """Generate compliance audit report."""
        return self.audit_manager.generate_audit_report(start_date, end_date, frameworks)
