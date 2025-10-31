"""Audit trail generation and management for TopoKit."""

import hashlib
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from .logging import get_logger
from ..types.compliance import (
    AuditEvent,
    ComplianceFramework,
    AuditReport
)


class AuditTrailManager:
    """Manages audit trail generation and tamper-evident logging."""
    
    def __init__(self, audit_endpoint: Optional[str] = None):
        """Initialize audit trail manager."""
        self.audit_endpoint = audit_endpoint
        self.logger = get_logger(__name__)
        self.audit_events: List[AuditEvent] = []
    
    def log_event(self, event: AuditEvent) -> AuditEvent:
        """Log an audit event with tamper-evident hashing."""
        # Create tamper-evident hash
        event = self._add_tamper_evident_hash(event)
        
        # Store event
        self.audit_events.append(event)
        
        # Log to external audit system if configured
        if self.audit_endpoint:
            self._send_to_audit_system(event)
        
        self.logger.info(f"Audit event logged: {event.event_type} - {event.action}")
        
        return event
    
    def _add_tamper_evident_hash(self, event: AuditEvent) -> AuditEvent:
        """Add tamper-evident hash to audit event."""
        # Prepare event data for hashing (exclude hash field)
        event_data = {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "session_id": event.session_id,
            "trace_id": event.trace_id,
            "event_type": event.event_type,
            "resource": event.resource,
            "action": event.action,
            "result": event.result,
            "details": event.details,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "compliance_frameworks": [f.value for f in event.compliance_frameworks]
        }
        
        # Create tamper-evident hash using SHA-256
        event_json = json.dumps(event_data, sort_keys=True)
        event_hash = hashlib.sha256(event_json.encode()).hexdigest()
        
        # Add hash to event
        event.hash = event_hash
        
        return event
    
    def verify_event_integrity(self, event: AuditEvent) -> bool:
        """Verify the integrity of an audit event by checking its hash."""
        if not event.hash:
            return False
        
        # Recalculate hash
        event_data = {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "session_id": event.session_id,
            "trace_id": event.trace_id,
            "event_type": event.event_type,
            "resource": event.resource,
            "action": event.action,
            "result": event.result,
            "details": event.details,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "compliance_frameworks": [f.value for f in event.compliance_frameworks]
        }
        
        event_json = json.dumps(event_data, sort_keys=True)
        calculated_hash = hashlib.sha256(event_json.encode()).hexdigest()
        
        return calculated_hash == event.hash
    
    def _send_to_audit_system(self, event: AuditEvent):
        """Send audit event to external system."""
        # Placeholder for external audit system integration
        # This would typically send to a secure audit log service
        event_data = {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "session_id": event.session_id,
            "trace_id": event.trace_id,
            "event_type": event.event_type,
            "resource": event.resource,
            "action": event.action,
            "result": event.result,
            "details": event.details,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "compliance_frameworks": [f.value for f in event.compliance_frameworks],
            "hash": event.hash
        }
        
        # TODO: Implement actual HTTP/HTTPS call to audit endpoint
        self.logger.debug(f"Would send audit event to {self.audit_endpoint}: {event.id}")
    
    def generate_audit_report(
        self,
        start_date: datetime,
        end_date: datetime,
        frameworks: Optional[List[ComplianceFramework]] = None
    ) -> AuditReport:
        """Generate compliance audit report."""
        # Filter events by date range
        filtered_events = [
            event for event in self.audit_events
            if start_date <= event.timestamp <= end_date
        ]
        
        # Filter by frameworks if specified
        if frameworks:
            filtered_events = [
                event for event in filtered_events
                if any(fw in event.compliance_frameworks for fw in frameworks)
            ]
        
        # Categorize events
        events_by_type: Dict[str, int] = {}
        events_by_result: Dict[str, int] = {}
        compliance_violations: List[Dict[str, Any]] = []
        
        for event in filtered_events:
            # By type
            if event.event_type not in events_by_type:
                events_by_type[event.event_type] = 0
            events_by_type[event.event_type] += 1
            
            # By result
            if event.result not in events_by_result:
                events_by_result[event.result] = 0
            events_by_result[event.result] += 1
            
            # Check for violations
            if event.result == "denied" or event.result == "failure":
                compliance_violations.append({
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": event.event_type,
                    "action": event.action,
                    "resource": event.resource,
                    "details": event.details
                })
        
        return AuditReport(
            period={
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            total_events=len(filtered_events),
            events_by_type=events_by_type,
            events_by_result=events_by_result,
            compliance_violations=compliance_violations,
            recommendations=[]
        )
    
    def get_events_by_trace(self, trace_id: str) -> List[AuditEvent]:
        """Get all audit events for a specific trace ID."""
        return [event for event in self.audit_events if event.trace_id == trace_id]
    
    def get_events_by_user(self, user_id: str, start_date: Optional[datetime] = None, 
                          end_date: Optional[datetime] = None) -> List[AuditEvent]:
        """Get all audit events for a specific user."""
        events = [event for event in self.audit_events if event.user_id == user_id]
        
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        
        return events
    
    def get_events_by_resource(self, resource: str, start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> List[AuditEvent]:
        """Get all audit events for a specific resource."""
        events = [event for event in self.audit_events if event.resource == resource]
        
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        
        return events
    
    def verify_all_events_integrity(self) -> Dict[str, bool]:
        """Verify integrity of all stored audit events."""
        results = {}
        for event in self.audit_events:
            results[event.id] = self.verify_event_integrity(event)
        return results

