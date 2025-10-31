#!/usr/bin/env python3
"""Validation script for Phase 6 (User Story 4) - Compliance & Governance implementation."""

import sys
import asyncio
from pathlib import Path

# Add packages/core to path
core_path = Path(__file__).parent / "packages" / "core"
sys.path.insert(0, str(core_path))

from datetime import datetime, timedelta

# Import directly from modules to avoid package __init__ dependencies
try:
    # Import types directly
    from topokit.types.compliance import (
        ComplianceFramework,
        ComplianceRule,
        AuditEvent,
        DataRetentionPolicy,
        ComplianceCheckResult,
        PIIDetectionResult,
        AuditReport
    )
    
    # Import core modules directly
    from topokit.core.compliance import ComplianceEngine, PIIDetector
    from topokit.core.audit import AuditTrailManager
    from topokit.core.data_lifecycle import DataLifecycleManager
    
    # Try to import config, use fallback if needed
    try:
        from topokit.core.config import ComplianceConfig
    except ImportError:
        from dataclasses import dataclass
        
        @dataclass
        class ComplianceConfig:
            enable_gdpr: bool = True
            enable_ccpa: bool = True
            enable_sox: bool = True
            enable_hipaa: bool = True
            audit_endpoint: str = None
            data_retention_days: int = 2555
            pii_redaction_enabled: bool = True
            audit_log_encryption: bool = True
    
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nNote: Some dependencies (like yaml) may not be installed.")
    print("This validation tests syntax and structure, not runtime execution.")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def test_compliance_types():
    """Test compliance type definitions."""
    print("\n📋 Testing Compliance Types...")
    
    # Test ComplianceFramework enum
    assert ComplianceFramework.GDPR == "gdpr"
    assert ComplianceFramework.CCPA == "ccpa"
    assert ComplianceFramework.SOX == "sox"
    assert ComplianceFramework.HIPAA == "hipaa"
    print("  ✅ ComplianceFramework enum works")
    
    # Test AuditEvent creation
    event = AuditEvent(
        id="test-001",
        timestamp=datetime.now(),
        user_id="user-123",
        event_type="test",
        resource="test-resource",
        action="test-action",
        result="success"
    )
    assert event.id == "test-001"
    print("  ✅ AuditEvent creation works")
    
    # Test ComplianceRule creation
    rule = ComplianceRule(
        id="test-rule",
        framework=ComplianceFramework.GDPR,
        name="Test Rule",
        description="Test",
        severity="high"
    )
    assert rule.framework == ComplianceFramework.GDPR
    print("  ✅ ComplianceRule creation works")
    
    # Test DataRetentionPolicy creation
    policy = DataRetentionPolicy(
        id="test-policy",
        name="Test Policy",
        data_types=["pii"],
        retention_period_days=365
    )
    assert policy.retention_period_days == 365
    print("  ✅ DataRetentionPolicy creation works")
    
    print("✅ All type tests passed")


def test_pii_detector():
    """Test PII detection and redaction."""
    print("\n🔍 Testing PII Detection...")
    
    detector = PIIDetector()
    
    # Test PII detection
    test_text = "Contact john.doe@example.com or call 555-123-4567"
    findings = detector.detect_pii(test_text)
    
    assert len(findings) > 0
    assert any(f["type"] == "email" for f in findings)
    print(f"  ✅ Detected {len(findings)} PII items")
    
    # Test PII redaction
    redacted = detector.redact_pii(test_text)
    assert "[REDACTED]" in redacted
    assert "john.doe@example.com" not in redacted
    print("  ✅ PII redaction works")
    
    print("✅ All PII detection tests passed")


def test_audit_trail_manager():
    """Test audit trail management."""
    print("\n📝 Testing Audit Trail Manager...")
    
    manager = AuditTrailManager()
    
    # Create and log event
    event = AuditEvent(
        id="audit-001",
        timestamp=datetime.now(),
        user_id="user-123",
        event_type="test_event",
        resource="test-resource",
        action="test-action",
        result="success"
    )
    
    logged_event = manager.log_event(event)
    
    assert logged_event.hash is not None
    assert len(logged_event.hash) == 64  # SHA-256 hex length
    print("  ✅ Audit event logged with tamper-evident hash")
    
    # Test integrity verification
    is_valid = manager.verify_event_integrity(logged_event)
    assert is_valid is True
    print("  ✅ Event integrity verification works")
    
    # Test tampered event
    tampered_event = AuditEvent(
        id="audit-001",
        timestamp=datetime.now(),
        user_id="user-hacked",  # Changed
        event_type="test_event",
        resource="test-resource",
        action="test-action",
        result="success",
        hash=logged_event.hash  # Old hash
    )
    
    is_valid_tampered = manager.verify_event_integrity(tampered_event)
    assert is_valid_tampered is False
    print("  ✅ Tampered event detection works")
    
    # Test report generation
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=1)
    
    report = manager.generate_audit_report(start_date, end_date)
    assert report.total_events >= 1
    assert "test_event" in report.events_by_type
    print("  ✅ Audit report generation works")
    
    print("✅ All audit trail tests passed")


def test_data_lifecycle_manager():
    """Test data lifecycle management."""
    print("\n🔄 Testing Data Lifecycle Manager...")
    
    manager = DataLifecycleManager()
    
    # Check policies exist
    assert len(manager.retention_policies) > 0
    assert "gdpr_personal_data" in manager.retention_policies
    assert "sox_financial_records" in manager.retention_policies
    assert "hipaa_phi" in manager.retention_policies
    print(f"  ✅ {len(manager.retention_policies)} retention policies loaded")
    
    # Test retention requirement check
    creation_date = datetime.now() - timedelta(days=100)
    requirement = manager.check_retention_requirement("pii", creation_date)
    
    assert requirement["should_retain"] is True
    assert requirement["retention_days"] is not None
    print("  ✅ Retention requirement check works")
    
    # Test policy retrieval
    policies = manager.get_policies_for_data_type("pii")
    assert len(policies) > 0
    print(f"  ✅ Retrieved {len(policies)} policies for data type 'pii'")
    
    # Test summary
    summary = manager.get_retention_summary()
    assert summary["total_policies"] > 0
    print("  ✅ Retention summary generation works")
    
    print("✅ All data lifecycle tests passed")


async def test_compliance_engine():
    """Test compliance engine."""
    print("\n⚖️ Testing Compliance Engine...")
    
    config = ComplianceConfig(
        enable_gdpr=True,
        enable_ccpa=True,
        enable_sox=True,
        enable_hipaa=True
    )
    
    engine = ComplianceEngine(config)
    
    # Test engine initialization
    assert engine.config is not None
    assert engine.pii_detector is not None
    assert engine.audit_manager is not None
    assert engine.data_lifecycle_manager is not None
    print("  ✅ Compliance engine initialized")
    
    # Test compliance rules
    assert len(engine.compliance_rules) > 0
    assert "gdpr_data_minimization" in engine.compliance_rules
    assert "gdpr_consent" in engine.compliance_rules
    assert "ccpa_consumer_rights" in engine.compliance_rules
    assert "sox_audit_trail" in engine.compliance_rules
    assert "hipaa_phi_protection" in engine.compliance_rules
    print(f"  ✅ {len(engine.compliance_rules)} compliance rules loaded")
    
    # Test compliance check (GDPR)
    test_data = "Contact john.doe@example.com for information"
    context = {
        "consent_given": False,
        "requires_consent": True,
        "data_type": "pii"
    }
    
    result = await engine.check_compliance(test_data, context)
    assert isinstance(result, ComplianceCheckResult)
    print(f"  ✅ Compliance check returned {type(result).__name__}")
    
    # Test PII detection and redaction
    pii_result = engine.detect_and_redact_pii(test_data)
    assert isinstance(pii_result, PIIDetectionResult)
    assert pii_result.has_pii is True
    print("  ✅ PII detection and redaction works")
    
    # Test audit event logging
    audit_event = AuditEvent(
        id="test-audit",
        timestamp=datetime.now(),
        user_id="user-123",
        event_type="compliance_check",
        resource="test",
        action="check",
        result="success",
        compliance_frameworks=[ComplianceFramework.GDPR]
    )
    
    await engine.log_audit_event(audit_event)
    assert len(engine.audit_events) > 0
    print("  ✅ Audit event logging works")
    
    # Test audit report
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=1)
    
    report = engine.get_audit_report(start_date, end_date)
    assert isinstance(report, AuditReport)
    assert report.total_events > 0
    print("  ✅ Audit report generation works")
    
    print("✅ All compliance engine tests passed")


async def main():
    """Run all validation tests."""
    print("=" * 70)
    print("Phase 6 (User Story 4) - Compliance & Governance Validation")
    print("=" * 70)
    
    try:
        # Test types
        test_compliance_types()
        
        # Test PII detector
        test_pii_detector()
        
        # Test audit trail manager
        test_audit_trail_manager()
        
        # Test data lifecycle manager
        test_data_lifecycle_manager()
        
        # Test compliance engine
        await test_compliance_engine()
        
        print("\n" + "=" * 70)
        print("✅ ALL VALIDATION TESTS PASSED")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Assertion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

