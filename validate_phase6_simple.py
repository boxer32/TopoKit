#!/usr/bin/env python3
"""Simple validation script for Phase 6 - tests syntax and structure without runtime dependencies."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Direct file imports to avoid package __init__ dependencies
base_path = Path(__file__).parent / "packages" / "core"

def validate_syntax():
    """Validate Python syntax of all Phase 6 files."""
    print("=" * 70)
    print("Phase 6 Validation - Syntax and Structure Check")
    print("=" * 70)
    
    files_to_check = [
        "topokit/types/compliance.py",
        "topokit/core/compliance.py",
        "topokit/core/audit.py",
        "topokit/core/data_lifecycle.py",
        "tests/contract/test_compliance.py",
        "tests/integration/test_audit_trails.py"
    ]
    
    print("\n📝 Checking Python syntax...")
    all_valid = True
    
    for file_path in files_to_check:
        full_path = base_path / file_path if file_path.startswith("topokit") else Path(__file__).parent / file_path
        if full_path.exists():
            try:
                with open(full_path, 'r') as f:
                    code = f.read()
                compile(code, str(full_path), 'exec')
                print(f"  ✅ {file_path}")
            except SyntaxError as e:
                print(f"  ❌ {file_path}: {e}")
                all_valid = False
        else:
            print(f"  ⚠️  {file_path}: File not found")
    
    return all_valid


def validate_structure():
    """Validate that required classes and functions exist."""
    print("\n🔍 Checking code structure...")
    
    # Check compliance.py structure
    compliance_file = base_path / "topokit" / "core" / "compliance.py"
    if compliance_file.exists():
        content = compliance_file.read_text()
        checks = [
            ("ComplianceEngine", "class ComplianceEngine"),
            ("PIIDetector", "class PIIDetector"),
            ("check_compliance", "async def check_compliance"),
            ("detect_and_redact_pii", "def detect_and_redact_pii"),
            ("log_audit_event", "async def log_audit_event"),
            ("get_audit_report", "def get_audit_report"),
            ("_check_gdpr_rule", "async def _check_gdpr_rule"),
            ("_check_ccpa_rule", "async def _check_ccpa_rule"),
            ("_check_sox_rule", "async def _check_sox_rule"),
            ("_check_hipaa_rule", "async def _check_hipaa_rule"),
        ]
        
        for name, pattern in checks:
            if pattern in content:
                print(f"  ✅ {name} found")
            else:
                print(f"  ❌ {name} not found")
                return False
    else:
        print("  ❌ compliance.py not found")
        return False
    
    # Check audit.py structure
    audit_file = base_path / "topokit" / "core" / "audit.py"
    if audit_file.exists():
        content = audit_file.read_text()
        checks = [
            ("AuditTrailManager", "class AuditTrailManager"),
            ("log_event", "def log_event"),
            ("verify_event_integrity", "def verify_event_integrity"),
            ("generate_audit_report", "def generate_audit_report"),
            ("_add_tamper_evident_hash", "def _add_tamper_evident_hash"),
        ]
        
        for name, pattern in checks:
            if pattern in content:
                print(f"  ✅ {name} found")
            else:
                print(f"  ❌ {name} not found")
                return False
    else:
        print("  ❌ audit.py not found")
        return False
    
    # Check data_lifecycle.py structure
    lifecycle_file = base_path / "topokit" / "core" / "data_lifecycle.py"
    if lifecycle_file.exists():
        content = lifecycle_file.read_text()
        checks = [
            ("DataLifecycleManager", "class DataLifecycleManager"),
            ("check_retention_requirement", "def check_retention_requirement"),
            ("identify_expired_data", "async def identify_expired_data"),
            ("execute_retention_policy", "async def execute_retention_policy"),
        ]
        
        for name, pattern in checks:
            if pattern in content:
                print(f"  ✅ {name} found")
            else:
                print(f"  ❌ {name} not found")
                return False
    else:
        print("  ❌ data_lifecycle.py not found")
        return False
    
    # Check types/compliance.py structure
    types_file = base_path / "topokit" / "types" / "compliance.py"
    if types_file.exists():
        content = types_file.read_text()
        checks = [
            ("ComplianceFramework", "class ComplianceFramework"),
            ("AuditEvent", "@dataclass"),
            ("ComplianceRule", "@dataclass"),
            ("DataRetentionPolicy", "@dataclass"),
            ("ComplianceCheckResult", "@dataclass"),
            ("PIIDetectionResult", "@dataclass"),
            ("AuditReport", "@dataclass"),
        ]
        
        for name, pattern in checks:
            if name == "AuditEvent" or name == "ComplianceRule" or name == "DataRetentionPolicy" or name == "ComplianceCheckResult" or name == "PIIDetectionResult" or name == "AuditReport":
                # Check for dataclass with this name
                if f"class {name}" in content or (f"@dataclass" in content and name in content):
                    print(f"  ✅ {name} found")
                else:
                    print(f"  ❌ {name} not found")
                    return False
            elif pattern in content:
                print(f"  ✅ {name} found")
            else:
                print(f"  ❌ {name} not found")
                return False
    else:
        print("  ❌ types/compliance.py not found")
        return False
    
    return True


def validate_compliance_frameworks():
    """Validate that all required compliance frameworks are implemented."""
    print("\n⚖️  Checking compliance framework implementations...")
    
    compliance_file = base_path / "topokit" / "core" / "compliance.py"
    if compliance_file.exists():
        content = compliance_file.read_text()
        
        frameworks = ["GDPR", "CCPA", "SOX", "HIPAA"]
        rules = [
            ("gdpr_data_minimization", "GDPR"),
            ("gdpr_consent", "GDPR"),
            ("ccpa_consumer_rights", "CCPA"),
            ("ccpa_opt_out", "CCPA"),
            ("sox_audit_trail", "SOX"),
            ("hipaa_phi_protection", "HIPAA"),
            ("hipaa_minimum_necessary", "HIPAA"),
        ]
        
        for rule_id, framework in rules:
            if f'"{rule_id}"' in content or f"'{rule_id}'" in content:
                print(f"  ✅ {framework} rule: {rule_id}")
            else:
                print(f"  ❌ {framework} rule: {rule_id} not found")
                return False
        
        # Check framework check methods
        check_methods = [
            "_check_gdpr_rule",
            "_check_ccpa_rule",
            "_check_sox_rule",
            "_check_hipaa_rule",
        ]
        
        for method in check_methods:
            if method in content:
                print(f"  ✅ Check method: {method}")
            else:
                print(f"  ❌ Check method: {method} not found")
                return False
        
        return True
    else:
        print("  ❌ compliance.py not found")
        return False


def validate_tests():
    """Validate test files structure."""
    print("\n🧪 Checking test files...")
    
    test_files = [
        ("tests/contract/test_compliance.py", [
            "TestComplianceReporting",
            "test_compliance_engine_creation_contract",
            "test_audit_event_logging_contract",
            "test_compliance_check_contract",
            "test_pii_detection_contract",
            "test_audit_report_generation_contract",
        ]),
        ("tests/integration/test_audit_trails.py", [
            "TestAuditTrailGeneration",
            "test_audit_trail_for_topology_execution",
            "test_audit_trail_for_compliance_checks",
            "test_audit_trail_for_pii_redaction",
            "test_audit_trail_persistence",
        ]),
    ]
    
    all_valid = True
    for test_file, test_items in test_files:
        full_path = Path(__file__).parent / test_file
        if full_path.exists():
            content = full_path.read_text()
            print(f"  ✅ {test_file} exists")
            for item in test_items:
                if item in content:
                    print(f"    ✅ {item}")
                else:
                    print(f"    ❌ {item} not found")
                    all_valid = False
        else:
            print(f"  ❌ {test_file} not found")
            all_valid = False
    
    return all_valid


def main():
    """Run all validations."""
    print("\n" + "=" * 70)
    print("Phase 6 (User Story 4) - Compliance & Governance Validation")
    print("=" * 70)
    
    results = []
    
    # Syntax validation
    results.append(("Syntax", validate_syntax()))
    
    # Structure validation
    results.append(("Structure", validate_structure()))
    
    # Compliance frameworks validation
    results.append(("Compliance Frameworks", validate_compliance_frameworks()))
    
    # Tests validation
    results.append(("Tests", validate_tests()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Validation Summary")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:25} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    if all_passed:
        print("✅ ALL VALIDATIONS PASSED")
        print("\nNote: This validates syntax and structure.")
        print("Runtime testing requires dependencies (yaml, pytest, etc.)")
        print("to be installed in a virtual environment.")
    else:
        print("❌ SOME VALIDATIONS FAILED")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

