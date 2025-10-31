"""Unit tests for Compliance Engine."""

import pytest
from datetime import datetime, timezone, timedelta
from topokit.core.compliance import (
    ComplianceEngine, ComplianceFramework, PIIDetector, PIIType,
    AuditEvent, DataRetentionPolicy, ComplianceRule
)
from topokit.core.config import ComplianceConfig


class TestComplianceEngine:
    """Test cases for Compliance Engine."""
    
    @pytest.fixture
    def compliance_engine(self):
        """Create a compliance engine for testing."""
        config = ComplianceConfig()
        return ComplianceEngine(config)
    
    def test_pii_detection_email(self):
        """Test PII detection for email addresses."""
        detector = PIIDetector()
        text = "Contact us at john.doe@example.com for more information"
        
        findings = detector.detect_pii(text)
        
        assert len(findings) == 1
        assert findings[0]["type"] == PIIType.EMAIL.value
        assert findings[0]["value"] == "john.doe@example.com"
    
    def test_pii_detection_phone(self):
        """Test PII detection for phone numbers."""
        detector = PIIDetector()
        text = "Call us at (555) 123-4567 or 555-123-4567"
        
        findings = detector.detect_pii(text)
        
        assert len(findings) >= 1
        phone_types = [f["type"] for f in findings]
        assert PIIType.PHONE.value in phone_types
    
    def test_pii_redaction(self):
        """Test PII redaction."""
        detector = PIIDetector()
        text = "Email: john@example.com, Phone: (555) 123-4567"
        
        redacted = detector.redact_pii(text)
        
        assert "[REDACTED]" in redacted
        assert "john@example.com" not in redacted
        assert "(555) 123-4567" not in redacted
    
    def test_compliance_engine_initialization(self, compliance_engine):
        """Test compliance engine initialization."""
        assert compliance_engine is not None
        assert len(compliance_engine.compliance_rules) > 0
        assert "gdpr_data_minimization" in compliance_engine.compliance_rules
        assert "sox_audit_trail" in compliance_engine.compliance_rules
        assert "hipaa_phi_protection" in compliance_engine.compliance_rules
    
    @pytest.mark.asyncio
    async def test_gdpr_data_minimization_check(self, compliance_engine):
        """Test GDPR data minimization compliance check."""
        # Test with PII data without consent
        data = "User email: john@example.com"
        context = {"consent_given": False}
        
        result = await compliance_engine.check_compliance(data, context)
        
        # Should have violations due to PII without consent
        assert not result["compliant"]
        assert len(result["violations"]) > 0
        assert any("gdpr_data_minimization" in v["rule_id"] for v in result["violations"])
    
    @pytest.mark.asyncio
    async def test_gdpr_consent_check(self, compliance_engine):
        """Test GDPR consent compliance check."""
        # Test without consent when required
        data = {"user_data": "some data"}
        context = {"requires_consent": True, "consent_given": False}
        
        result = await compliance_engine.check_compliance(data, context)
        
        assert not result["compliant"]
        assert len(result["violations"]) > 0
        assert any("gdpr_consent" in v["rule_id"] for v in result["violations"])
    
    @pytest.mark.asyncio
    async def test_sox_audit_trail_check(self, compliance_engine):
        """Test SOX audit trail compliance check."""
        # Test financial data without audit logging
        data = {"amount": 1000, "account": "12345"}
        context = {"data_type": "financial", "audit_logged": False}
        
        result = await compliance_engine.check_compliance(data, context)
        
        assert not result["compliant"]
        assert len(result["violations"]) > 0
        assert any("sox_audit_trail" in v["rule_id"] for v in result["violations"])
    
    @pytest.mark.asyncio
    async def test_hipaa_phi_protection_check(self, compliance_engine):
        """Test HIPAA PHI protection compliance check."""
        # Test PHI data without encryption
        data = {"patient_id": "12345", "diagnosis": "diabetes"}
        context = {"data_type": "phi", "encrypted": False}
        
        result = await compliance_engine.check_compliance(data, context)
        
        assert not result["compliant"]
        assert len(result["violations"]) > 0
        assert any("hipaa_phi_protection" in v["rule_id"] for v in result["violations"])
    
    def test_detect_and_redact_pii_string(self, compliance_engine):
        """Test PII detection and redaction for string data."""
        data = "Contact: john@example.com, Phone: (555) 123-4567"
        
        result = compliance_engine.detect_and_redact_pii(data)
        
        assert result["has_pii"] is True
        assert len(result["pii_findings"]) > 0
        assert "[REDACTED]" in result["redacted"]
        assert "john@example.com" not in result["redacted"]
    
    def test_detect_and_redact_pii_dict(self, compliance_engine):
        """Test PII detection and redaction for dictionary data."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "(555) 123-4567",
            "id": 12345
        }
        
        result = compliance_engine.detect_and_redact_pii(data)
        
        assert result["has_pii"] is True
        assert len(result["pii_findings"]) > 0
        assert result["redacted"]["email"] == "[REDACTED]"
        assert "[REDACTED]" in result["redacted"]["phone"]
        assert result["redacted"]["id"] == 12345  # Non-PII data unchanged
    
    @pytest.mark.asyncio
    async def test_audit_event_logging(self, compliance_engine):
        """Test audit event logging."""
        event = AuditEvent(
            id="test_event_1",
            timestamp=datetime.now(timezone.utc),
            user_id="user123",
            session_id="session456",
            trace_id="trace789",
            event_type="data_access",
            resource="topology_execution",
            action="read",
            result="success",
            details={"node_id": "ai_node"},
            compliance_frameworks=[ComplianceFramework.GDPR]
        )
        
        await compliance_engine.log_audit_event(event)
        
        assert len(compliance_engine.audit_events) == 1
        assert compliance_engine.audit_events[0].id == "test_event_1"
    
    def test_audit_report_generation(self, compliance_engine):
        """Test audit report generation."""
        # Add some test events
        now = datetime.now(timezone.utc)
        compliance_engine.audit_events = [
            AuditEvent(
                id="event1",
                timestamp=now - timedelta(hours=1),
                user_id="user1",
                session_id="session1",
                trace_id="trace1",
                event_type="data_access",
                resource="topology",
                action="read",
                result="success",
                compliance_frameworks=[ComplianceFramework.GDPR]
            ),
            AuditEvent(
                id="event2",
                timestamp=now - timedelta(minutes=30),
                user_id="user2",
                session_id="session2",
                trace_id="trace2",
                event_type="data_access",
                resource="topology",
                action="write",
                result="denied",
                compliance_frameworks=[ComplianceFramework.SOX]
            )
        ]
        
        start_date = now - timedelta(hours=2)
        end_date = now
        
        report = compliance_engine.get_audit_report(start_date, end_date)
        
        assert report["total_events"] == 2
        assert report["events_by_type"]["data_access"] == 2
        assert report["events_by_result"]["success"] == 1
        assert report["events_by_result"]["denied"] == 1
        assert len(report["compliance_violations"]) == 1
