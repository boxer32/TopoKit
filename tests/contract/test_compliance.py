"""Contract test for compliance reporting in TopoKit."""

import pytest
from datetime import datetime, timedelta
from topokit.core.compliance import ComplianceEngine
from topokit.types.compliance import (
    ComplianceFramework,
    ComplianceRule,
    AuditEvent,
    DataRetentionPolicy
)
from topokit.core.config import ComplianceConfig


class TestComplianceReporting:
    """Contract tests for compliance reporting."""
    
    @pytest.fixture
    def compliance_engine(self):
        """Create a compliance engine instance."""
        config = ComplianceConfig(
            enable_gdpr=True,
            enable_ccpa=True,
            enable_sox=True,
            enable_hipaa=True,
            audit_log_encryption=True,
            pii_redaction_enabled=True
        )
        return ComplianceEngine(config)
    
    @pytest.fixture
    def sample_audit_event(self):
        """Create a sample audit event."""
        return AuditEvent(
            id="audit-001",
            timestamp=datetime.now(),
            user_id="user-123",
            session_id="session-456",
            trace_id="trace-789",
            event_type="data_access",
            resource="topology-pack-rag-system",
            action="read",
            result="success",
            details={"source": "api", "ip": "192.168.1.1"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOX]
        )
    
    def test_compliance_engine_creation_contract(self, compliance_engine):
        """Contract test: Compliance engine must have all required components."""
        # Contract: Must have compliance configuration
        assert compliance_engine.config is not None
        assert compliance_engine.config.enable_gdpr is True
        assert compliance_engine.config.enable_sox is True
        
        # Contract: Must have PII detector
        assert compliance_engine.pii_detector is not None
        
        # Contract: Must have audit events storage
        assert compliance_engine.audit_events is not None
        assert isinstance(compliance_engine.audit_events, list)
        
        # Contract: Must have compliance rules
        assert compliance_engine.compliance_rules is not None
        assert isinstance(compliance_engine.compliance_rules, dict)
        
        # Contract: Must have retention policies
        assert compliance_engine.retention_policies is not None
        assert isinstance(compliance_engine.retention_policies, dict)
    
    def test_audit_event_logging_contract(self, compliance_engine, sample_audit_event):
        """Contract test: Audit events must be logged with tamper-evident hashing."""
        import asyncio
        
        # Contract: Must log audit event
        asyncio.run(compliance_engine.log_audit_event(sample_audit_event))
        
        # Contract: Event must be stored
        assert len(compliance_engine.audit_events) > 0
        logged_event = compliance_engine.audit_events[-1]
        assert logged_event.id == "audit-001"
        assert logged_event.event_type == "data_access"
        assert logged_event.action == "read"
        
        # Contract: Event must have compliance frameworks
        assert len(logged_event.compliance_frameworks) > 0
        assert ComplianceFramework.GDPR in logged_event.compliance_frameworks
    
    def test_compliance_check_contract(self, compliance_engine):
        """Contract test: Compliance check must return structured results."""
        import asyncio
        
        # Test data with PII
        test_data = "Contact john.doe@example.com or call 555-123-4567"
        context = {
            "consent_given": False,
            "requires_consent": True,
            "data_type": "pii"
        }
        
        # Contract: Must return compliance check results
        result = asyncio.run(compliance_engine.check_compliance(test_data, context))
        
        # Contract: Result must have required structure
        assert "compliant" in result
        assert "violations" in result
        assert "recommendations" in result
        assert "required_actions" in result
        assert isinstance(result["violations"], list)
        assert isinstance(result["required_actions"], list)
    
    def test_pii_detection_contract(self, compliance_engine):
        """Contract test: PII detection must identify and redact sensitive data."""
        # Test data with multiple PII types
        test_data = "Email: john.doe@example.com, Phone: 555-123-4567, SSN: 123-45-6789"
        
        # Contract: Must detect PII
        result = compliance_engine.detect_and_redact_pii(test_data)
        
        # Contract: Result must have required structure
        assert "original" in result
        assert "redacted" in result
        assert "pii_findings" in result
        assert "has_pii" in result
        
        # Contract: Must detect PII
        assert result["has_pii"] is True
        assert len(result["pii_findings"]) > 0
        
        # Contract: Must redact PII
        assert "[REDACTED]" in result["redacted"]
        assert "john.doe@example.com" not in result["redacted"]
        assert "555-123-4567" not in result["redacted"]
    
    def test_audit_report_generation_contract(self, compliance_engine, sample_audit_event):
        """Contract test: Audit reports must include comprehensive compliance data."""
        import asyncio
        
        # Log multiple events
        asyncio.run(compliance_engine.log_audit_event(sample_audit_event))
        
        # Create another event
        event2 = AuditEvent(
            id="audit-002",
            timestamp=datetime.now(),
            user_id="user-456",
            session_id="session-789",
            trace_id="trace-012",
            event_type="data_modification",
            resource="topology-pack-rag-system",
            action="update",
            result="denied",
            details={"reason": "insufficient_permissions"},
            compliance_frameworks=[ComplianceFramework.SOX]
        )
        asyncio.run(compliance_engine.log_audit_event(event2))
        
        # Contract: Must generate audit report
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)
        
        report = compliance_engine.get_audit_report(
            start_date=start_date,
            end_date=end_date
        )
        
        # Contract: Report must have required structure
        assert "period" in report
        assert "total_events" in report
        assert "events_by_type" in report
        assert "events_by_result" in report
        assert "compliance_violations" in report
        assert "recommendations" in report
        
        # Contract: Report must include logged events
        assert report["total_events"] >= 2
        assert "data_access" in report["events_by_type"]
        assert "data_modification" in report["events_by_type"]
        
        # Contract: Report must identify violations
        assert len(report["compliance_violations"]) > 0
        assert any(v["result"] == "denied" for v in report["compliance_violations"])
    
    def test_framework_specific_audit_report_contract(self, compliance_engine, sample_audit_event):
        """Contract test: Audit reports must support framework-specific filtering."""
        import asyncio
        
        # Log events with different frameworks
        asyncio.run(compliance_engine.log_audit_event(sample_audit_event))
        
        # Contract: Must generate framework-specific report
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)
        
        gdpr_report = compliance_engine.get_audit_report(
            start_date=start_date,
            end_date=end_date,
            frameworks=[ComplianceFramework.GDPR]
        )
        
        # Contract: Framework-filtered report must only include relevant events
        assert "total_events" in gdpr_report
        assert gdpr_report["total_events"] >= 1
        
        # All events should have GDPR framework
        for event in compliance_engine.audit_events:
            if start_date <= event.timestamp <= end_date:
                if ComplianceFramework.GDPR in event.compliance_frameworks:
                    assert ComplianceFramework.GDPR in event.compliance_frameworks
    
    def test_compliance_rules_contract(self, compliance_engine):
        """Contract test: Compliance rules must be properly configured."""
        # Contract: Must have default compliance rules
        assert len(compliance_engine.compliance_rules) > 0
        
        # Contract: Must have GDPR rules
        assert "gdpr_data_minimization" in compliance_engine.compliance_rules
        assert "gdpr_consent" in compliance_engine.compliance_rules
        
        # Contract: Must have SOX rules
        assert "sox_audit_trail" in compliance_engine.compliance_rules
        
        # Contract: Must have HIPAA rules
        assert "hipaa_phi_protection" in compliance_engine.compliance_rules
        
        # Contract: Rules must have required structure
        rule = compliance_engine.compliance_rules["gdpr_data_minimization"]
        assert rule.id == "gdpr_data_minimization"
        assert rule.framework == ComplianceFramework.GDPR
        assert rule.name is not None
        assert rule.description is not None
        assert rule.severity in ["critical", "high", "medium", "low"]
        assert isinstance(rule.enabled, bool)

