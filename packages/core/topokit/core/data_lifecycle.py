"""Data lifecycle management and retention policies for TopoKit."""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

from .logging import get_logger
from ..types.compliance import (
    DataRetentionPolicy,
    DataClassification
)


class DataLifecycleManager:
    """Manages data retention policies and lifecycle operations."""
    
    def __init__(self, retention_policies: Optional[List[DataRetentionPolicy]] = None):
        """Initialize data lifecycle manager."""
        self.logger = get_logger(__name__)
        self.retention_policies: Dict[str, DataRetentionPolicy] = {}
        
        # Load default retention policies
        self._load_default_policies()
        
        # Load custom policies if provided
        if retention_policies:
            for policy in retention_policies:
                self.retention_policies[policy.id] = policy
    
    def _load_default_policies(self):
        """Load default data retention policies."""
        # GDPR: Right to erasure - data must be deletable
        self.retention_policies["gdpr_personal_data"] = DataRetentionPolicy(
            id="gdpr_personal_data",
            name="GDPR Personal Data Retention",
            data_types=["pii", "personal_data"],
            retention_period_days=2555,  # 7 years
            auto_delete=False,  # Requires explicit deletion request
            encryption_required=True,
            audit_required=True
        )
        
        # CCPA: Consumer data retention
        self.retention_policies["ccpa_consumer_data"] = DataRetentionPolicy(
            id="ccpa_consumer_data",
            name="CCPA Consumer Data Retention",
            data_types=["consumer_data", "pii"],
            retention_period_days=2555,  # 7 years
            auto_delete=False,
            encryption_required=True,
            audit_required=True
        )
        
        # SOX: Financial records must be retained for 7 years
        self.retention_policies["sox_financial_records"] = DataRetentionPolicy(
            id="sox_financial_records",
            name="SOX Financial Records Retention",
            data_types=["financial", "accounting", "audit_logs"],
            retention_period_days=2555,  # 7 years
            auto_delete=False,  # Must not auto-delete SOX records
            encryption_required=True,
            audit_required=True
        )
        
        # HIPAA: PHI retention - typically 6 years
        self.retention_policies["hipaa_phi"] = DataRetentionPolicy(
            id="hipaa_phi",
            name="HIPAA PHI Retention",
            data_types=["phi", "medical", "health"],
            retention_period_days=2190,  # 6 years
            auto_delete=False,
            encryption_required=True,
            audit_required=True
        )
        
        # General audit logs - shorter retention
        self.retention_policies["audit_logs"] = DataRetentionPolicy(
            id="audit_logs",
            name="Audit Logs Retention",
            data_types=["audit_logs", "access_logs"],
            retention_period_days=365,  # 1 year
            auto_delete=True,
            encryption_required=True,
            audit_required=False
        )
    
    def add_policy(self, policy: DataRetentionPolicy):
        """Add a data retention policy."""
        self.retention_policies[policy.id] = policy
        self.logger.info(f"Added retention policy: {policy.name}")
    
    def get_policy(self, policy_id: str) -> Optional[DataRetentionPolicy]:
        """Get a retention policy by ID."""
        return self.retention_policies.get(policy_id)
    
    def get_policies_for_data_type(self, data_type: str) -> List[DataRetentionPolicy]:
        """Get all retention policies that apply to a data type."""
        applicable_policies = []
        
        for policy in self.retention_policies.values():
            if data_type in policy.data_types:
                applicable_policies.append(policy)
        
        return applicable_policies
    
    def check_retention_requirement(self, data_type: str, creation_date: datetime) -> Dict[str, Any]:
        """Check if data should be retained based on policies."""
        policies = self.get_policies_for_data_type(data_type)
        
        if not policies:
            return {
                "should_retain": True,
                "retention_days": None,
                "expiry_date": None,
                "policies": []
            }
        
        # Use the most restrictive policy (longest retention)
        primary_policy = max(policies, key=lambda p: p.retention_period_days)
        
        expiry_date = creation_date + timedelta(days=primary_policy.retention_period_days)
        should_retain = datetime.now() < expiry_date
        
        return {
            "should_retain": should_retain,
            "retention_days": primary_policy.retention_period_days,
            "expiry_date": expiry_date.isoformat(),
            "policies": [p.id for p in policies],
            "auto_delete": primary_policy.auto_delete,
            "encryption_required": primary_policy.encryption_required
        }
    
    async def identify_expired_data(self, data_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify data records that have exceeded retention periods."""
        expired_records = []
        
        for record in data_records:
            data_type = record.get("data_type", "unknown")
            creation_date_str = record.get("created_at") or record.get("timestamp")
            
            if not creation_date_str:
                continue
            
            # Parse creation date
            if isinstance(creation_date_str, str):
                creation_date = datetime.fromisoformat(creation_date_str.replace("Z", "+00:00"))
            else:
                creation_date = creation_date_str
            
            requirement = self.check_retention_requirement(data_type, creation_date)
            
            if not requirement["should_retain"]:
                expired_records.append({
                    **record,
                    "expired_at": requirement["expiry_date"],
                    "retention_policy": requirement["policies"]
                })
        
        return expired_records
    
    async def execute_retention_policy(self, policy_id: str, data_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a retention policy on data records."""
        policy = self.retention_policies.get(policy_id)
        
        if not policy:
            return {
                "success": False,
                "error": f"Policy {policy_id} not found",
                "processed": 0,
                "deleted": 0
            }
        
        # Filter records by policy data types
        applicable_records = [
            r for r in data_records
            if any(dt in r.get("data_type", "") for dt in policy.data_types)
        ]
        
        expired_records = await self.identify_expired_data(applicable_records)
        
        # Delete if auto_delete is enabled
        deleted_count = 0
        if policy.auto_delete and expired_records:
            # In a real implementation, this would actually delete the records
            # For now, we just mark them
            deleted_count = len(expired_records)
            self.logger.info(f"Would delete {deleted_count} records per policy {policy_id}")
        
        return {
            "success": True,
            "policy_id": policy_id,
            "policy_name": policy.name,
            "processed": len(applicable_records),
            "expired": len(expired_records),
            "deleted": deleted_count if policy.auto_delete else 0,
            "auto_delete_enabled": policy.auto_delete
        }
    
    async def schedule_retention_cleanup(self, data_store: Any) -> Dict[str, Any]:
        """Schedule and execute retention policy cleanup across all policies."""
        results = {}
        
        for policy_id, policy in self.retention_policies.items():
            # In a real implementation, this would fetch data from the data store
            # For now, we return the policy execution structure
            result = await self.execute_retention_policy(policy_id, [])
            results[policy_id] = result
        
        return {
            "executed_at": datetime.now().isoformat(),
            "policies_processed": len(self.retention_policies),
            "results": results
        }
    
    def get_retention_summary(self) -> Dict[str, Any]:
        """Get a summary of all retention policies."""
        return {
            "total_policies": len(self.retention_policies),
            "policies": [
                {
                    "id": policy.id,
                    "name": policy.name,
                    "data_types": policy.data_types,
                    "retention_days": policy.retention_period_days,
                    "auto_delete": policy.auto_delete,
                    "encryption_required": policy.encryption_required,
                    "audit_required": policy.audit_required
                }
                for policy in self.retention_policies.values()
            ]
        }

