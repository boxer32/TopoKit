"""Human-in-the-Loop Gates for TopoKit with approval workflows and timeout handling."""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Set, Callable, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging

from .logging import get_logger


class GateType(str, Enum):
    """Types of human gates."""
    APPROVAL = "approval"          # Simple approval/rejection
    REVIEW = "review"              # Review with comments
    CONFIRMATION = "confirmation"  # Confirmation with details
    ESCALATION = "escalation"      # Escalation to higher authority


class GateStatus(str, Enum):
    """Gate status."""
    PENDING = "pending"            # Waiting for human response
    APPROVED = "approved"          # Approved by human
    REJECTED = "rejected"          # Rejected by human
    TIMEOUT = "timeout"            # Timed out
    CANCELLED = "cancelled"        # Cancelled by system
    ESCALATED = "escalated"        # Escalated to higher authority


class GatePriority(str, Enum):
    """Gate priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GateRequest:
    """Human gate request."""
    id: str
    gate_type: GateType
    priority: GatePriority
    title: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    timeout_seconds: int = 3600  # 1 hour default
    escalation_chain: List[str] = field(default_factory=list)
    status: GateStatus = GateStatus.PENDING
    response: Optional[Dict[str, Any]] = None
    responded_at: Optional[datetime] = None
    responded_by: Optional[str] = None
    escalation_level: int = 0


@dataclass
class GateResponse:
    """Human gate response."""
    request_id: str
    approved: bool
    comments: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    responded_by: Optional[str] = None
    responded_at: Optional[datetime] = None


@dataclass
class GateMetrics:
    """Gate metrics."""
    total_requests: int = 0
    pending_requests: int = 0
    approved_requests: int = 0
    rejected_requests: int = 0
    timeout_requests: int = 0
    escalated_requests: int = 0
    average_response_time_minutes: float = 0.0
    last_request_time: Optional[datetime] = None


class HumanGate:
    """Human-in-the-loop gate with approval workflows."""
    
    def __init__(self, 
                 identifier: str,
                 gate_type: GateType,
                 priority: GatePriority = GatePriority.MEDIUM,
                 timeout_seconds: int = 3600,
                 escalation_chain: Optional[List[str]] = None,
                 auto_approve: bool = False,
                 auto_reject: bool = False):
        """Initialize human gate.
        
        Args:
            identifier: Gate identifier
            gate_type: Type of gate
            priority: Priority level
            timeout_seconds: Timeout in seconds
            escalation_chain: List of users for escalation
            auto_approve: Auto-approve after timeout
            auto_reject: Auto-reject after timeout
        """
        self.identifier = identifier
        self.gate_type = gate_type
        self.priority = priority
        self.timeout_seconds = timeout_seconds
        self.escalation_chain = escalation_chain or []
        self.auto_approve = auto_approve
        self.auto_reject = auto_reject
        
        self.logger = get_logger(__name__)
        
        # Request management
        self._requests: Dict[str, GateRequest] = {}
        self._pending_requests: Set[str] = set()
        self._timeout_tasks: Dict[str, asyncio.Task] = {}
        
        # Metrics
        self.metrics = GateMetrics()
        
        # Event callbacks
        self._event_callbacks: List[Callable[[GateRequest], None]] = []
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def request_approval(self, 
                             title: str,
                             description: str,
                             data: Any = None,
                             context: Optional[Dict[str, Any]] = None,
                             created_by: Optional[str] = None,
                             assigned_to: Optional[str] = None,
                             timeout_seconds: Optional[int] = None) -> str:
        """Request human approval.
        
        Args:
            title: Request title
            description: Request description
            data: Data to be approved
            context: Additional context
            created_by: User who created the request
            assigned_to: User assigned to handle the request
            timeout_seconds: Custom timeout
            
        Returns:
            Request ID
        """
        request_id = str(uuid.uuid4())
        
        async with self._lock:
            # Create gate request
            request = GateRequest(
                id=request_id,
                gate_type=self.gate_type,
                priority=self.priority,
                title=title,
                description=description,
                context=context or {},
                data=data,
                created_by=created_by,
                assigned_to=assigned_to or self._get_next_assignee(),
                timeout_seconds=timeout_seconds or self.timeout_seconds,
                escalation_chain=self.escalation_chain.copy()
            )
            
            # Store request
            self._requests[request_id] = request
            self._pending_requests.add(request_id)
            
            # Update metrics
            self.metrics.total_requests += 1
            self.metrics.pending_requests += 1
            self.metrics.last_request_time = datetime.now(timezone.utc)
            
            # Start timeout task
            timeout_task = asyncio.create_task(
                self._handle_timeout(request_id)
            )
            self._timeout_tasks[request_id] = timeout_task
            
            self.logger.info(f"Created gate request {request_id}: {title}")
            
            # Emit event
            await self._emit_event(request)
            
            return request_id
    
    async def approve_request(self, 
                            request_id: str, 
                            approved_by: str,
                            comments: Optional[str] = None,
                            response_data: Optional[Dict[str, Any]] = None) -> bool:
        """Approve a gate request.
        
        Args:
            request_id: Request ID
            approved_by: User who approved
            comments: Approval comments
            response_data: Additional response data
            
        Returns:
            True if approved successfully
        """
        async with self._lock:
            if request_id not in self._requests:
                return False
            
            request = self._requests[request_id]
            if request.status != GateStatus.PENDING:
                return False
            
            # Update request
            request.status = GateStatus.APPROVED
            request.response = {
                "approved": True,
                "comments": comments,
                "response_data": response_data
            }
            request.responded_at = datetime.now(timezone.utc)
            request.responded_by = approved_by
            
            # Remove from pending
            self._pending_requests.discard(request_id)
            
            # Cancel timeout task
            if request_id in self._timeout_tasks:
                self._timeout_tasks[request_id].cancel()
                del self._timeout_tasks[request_id]
            
            # Update metrics
            self.metrics.pending_requests -= 1
            self.metrics.approved_requests += 1
            
            self.logger.info(f"Approved gate request {request_id} by {approved_by}")
            
            # Emit event
            await self._emit_event(request)
            
            return True
    
    async def reject_request(self, 
                           request_id: str, 
                           rejected_by: str,
                           comments: Optional[str] = None,
                           response_data: Optional[Dict[str, Any]] = None) -> bool:
        """Reject a gate request.
        
        Args:
            request_id: Request ID
            rejected_by: User who rejected
            comments: Rejection comments
            response_data: Additional response data
            
        Returns:
            True if rejected successfully
        """
        async with self._lock:
            if request_id not in self._requests:
                return False
            
            request = self._requests[request_id]
            if request.status != GateStatus.PENDING:
                return False
            
            # Update request
            request.status = GateStatus.REJECTED
            request.response = {
                "approved": False,
                "comments": comments,
                "response_data": response_data
            }
            request.responded_at = datetime.now(timezone.utc)
            request.responded_by = rejected_by
            
            # Remove from pending
            self._pending_requests.discard(request_id)
            
            # Cancel timeout task
            if request_id in self._timeout_tasks:
                self._timeout_tasks[request_id].cancel()
                del self._timeout_tasks[request_id]
            
            # Update metrics
            self.metrics.pending_requests -= 1
            self.metrics.rejected_requests += 1
            
            self.logger.info(f"Rejected gate request {request_id} by {rejected_by}")
            
            # Emit event
            await self._emit_event(request)
            
            return True
    
    async def escalate_request(self, request_id: str, escalated_by: str) -> bool:
        """Escalate a gate request.
        
        Args:
            request_id: Request ID
            escalated_by: User who escalated
            
        Returns:
            True if escalated successfully
        """
        async with self._lock:
            if request_id not in self._requests:
                return False
            
            request = self._requests[request_id]
            if request.status != GateStatus.PENDING:
                return False
            
            # Check if escalation is possible
            if request.escalation_level >= len(request.escalation_chain):
                self.logger.warning(f"Cannot escalate request {request_id}: no more escalation levels")
                return False
            
            # Update request
            request.escalation_level += 1
            request.assigned_to = request.escalation_chain[request.escalation_level - 1]
            request.status = GateStatus.ESCALATED
            
            # Update metrics
            self.metrics.escalated_requests += 1
            
            self.logger.info(f"Escalated gate request {request_id} to level {request.escalation_level}")
            
            # Emit event
            await self._emit_event(request)
            
            return True
    
    async def cancel_request(self, request_id: str, cancelled_by: str) -> bool:
        """Cancel a gate request.
        
        Args:
            request_id: Request ID
            cancelled_by: User who cancelled
            
        Returns:
            True if cancelled successfully
        """
        async with self._lock:
            if request_id not in self._requests:
                return False
            
            request = self._requests[request_id]
            if request.status != GateStatus.PENDING:
                return False
            
            # Update request
            request.status = GateStatus.CANCELLED
            request.responded_at = datetime.now(timezone.utc)
            request.responded_by = cancelled_by
            
            # Remove from pending
            self._pending_requests.discard(request_id)
            
            # Cancel timeout task
            if request_id in self._timeout_tasks:
                self._timeout_tasks[request_id].cancel()
                del self._timeout_tasks[request_id]
            
            # Update metrics
            self.metrics.pending_requests -= 1
            
            self.logger.info(f"Cancelled gate request {request_id} by {cancelled_by}")
            
            # Emit event
            await self._emit_event(request)
            
            return True
    
    async def _handle_timeout(self, request_id: str):
        """Handle request timeout."""
        try:
            await asyncio.sleep(self._requests[request_id].timeout_seconds)
            
            async with self._lock:
                if request_id not in self._requests:
                    return
                
                request = self._requests[request_id]
                if request.status != GateStatus.PENDING:
                    return
                
                # Handle timeout based on configuration
                if self.auto_approve:
                    await self.approve_request(request_id, "system", "Auto-approved due to timeout")
                elif self.auto_reject:
                    await self.reject_request(request_id, "system", "Auto-rejected due to timeout")
                else:
                    # Mark as timeout
                    request.status = GateStatus.TIMEOUT
                    request.responded_at = datetime.now(timezone.utc)
                    request.responded_by = "system"
                    
                    # Remove from pending
                    self._pending_requests.discard(request_id)
                    
                    # Update metrics
                    self.metrics.pending_requests -= 1
                    self.metrics.timeout_requests += 1
                    
                    self.logger.warning(f"Gate request {request_id} timed out")
                    
                    # Emit event
                    await self._emit_event(request)
                
        except asyncio.CancelledError:
            # Request was handled before timeout
            pass
        except Exception as e:
            self.logger.error(f"Error handling timeout for request {request_id}: {e}")
    
    def _get_next_assignee(self) -> Optional[str]:
        """Get next assignee from escalation chain."""
        if not self.escalation_chain:
            return None
        return self.escalation_chain[0]
    
    async def _emit_event(self, request: GateRequest):
        """Emit gate event."""
        for callback in self._event_callbacks:
            try:
                callback(request)
            except Exception as e:
                self.logger.error(f"Error in gate event callback: {e}")
    
    def add_event_callback(self, callback: Callable[[GateRequest], None]):
        """Add event callback.
        
        Args:
            callback: Callback function
        """
        self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[GateRequest], None]):
        """Remove event callback.
        
        Args:
            callback: Callback function
        """
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    def get_request(self, request_id: str) -> Optional[GateRequest]:
        """Get gate request by ID.
        
        Args:
            request_id: Request ID
            
        Returns:
            Gate request or None
        """
        return self._requests.get(request_id)
    
    def get_pending_requests(self) -> List[GateRequest]:
        """Get all pending requests.
        
        Returns:
            List of pending requests
        """
        return [self._requests[req_id] for req_id in self._pending_requests]
    
    def get_requests_by_user(self, user_id: str) -> List[GateRequest]:
        """Get requests assigned to a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of requests
        """
        return [
            req for req in self._requests.values()
            if req.assigned_to == user_id
        ]
    
    def get_requests_by_status(self, status: GateStatus) -> List[GateRequest]:
        """Get requests by status.
        
        Args:
            status: Request status
            
        Returns:
            List of requests
        """
        return [
            req for req in self._requests.values()
            if req.status == status
        ]
    
    def get_metrics(self) -> GateMetrics:
        """Get gate metrics.
        
        Returns:
            Gate metrics
        """
        return self.metrics
    
    def get_stats(self) -> Dict[str, Any]:
        """Get gate statistics.
        
        Returns:
            Gate statistics
        """
        return {
            "identifier": self.identifier,
            "gate_type": self.gate_type.value,
            "priority": self.priority.value,
            "total_requests": self.metrics.total_requests,
            "pending_requests": self.metrics.pending_requests,
            "approved_requests": self.metrics.approved_requests,
            "rejected_requests": self.metrics.rejected_requests,
            "timeout_requests": self.metrics.timeout_requests,
            "escalated_requests": self.metrics.escalated_requests,
            "approval_rate": self.metrics.approved_requests / self.metrics.total_requests if self.metrics.total_requests > 0 else 0.0,
            "average_response_time_minutes": self.metrics.average_response_time_minutes,
            "last_request_time": self.metrics.last_request_time.isoformat() if self.metrics.last_request_time else None
        }


class HumanGateManager:
    """Manager for multiple human gates."""
    
    def __init__(self):
        """Initialize human gate manager."""
        self.logger = get_logger(__name__)
        self._gates: Dict[str, HumanGate] = {}
    
    def create_gate(self, 
                   identifier: str,
                   gate_type: GateType,
                   priority: GatePriority = GatePriority.MEDIUM,
                   timeout_seconds: int = 3600,
                   escalation_chain: Optional[List[str]] = None,
                   auto_approve: bool = False,
                   auto_reject: bool = False) -> HumanGate:
        """Create a new human gate.
        
        Args:
            identifier: Gate identifier
            gate_type: Type of gate
            priority: Priority level
            timeout_seconds: Timeout in seconds
            escalation_chain: List of users for escalation
            auto_approve: Auto-approve after timeout
            auto_reject: Auto-reject after timeout
            
        Returns:
            Human gate instance
        """
        if identifier in self._gates:
            raise ValueError(f"Human gate {identifier} already exists")
        
        gate = HumanGate(
            identifier=identifier,
            gate_type=gate_type,
            priority=priority,
            timeout_seconds=timeout_seconds,
            escalation_chain=escalation_chain,
            auto_approve=auto_approve,
            auto_reject=auto_reject
        )
        
        self._gates[identifier] = gate
        self.logger.info(f"Created human gate {identifier} of type {gate_type.value}")
        
        return gate
    
    def get_gate(self, identifier: str) -> Optional[HumanGate]:
        """Get human gate by identifier.
        
        Args:
            identifier: Gate identifier
            
        Returns:
            Human gate instance or None
        """
        return self._gates.get(identifier)
    
    def remove_gate(self, identifier: str) -> bool:
        """Remove human gate.
        
        Args:
            identifier: Gate identifier
            
        Returns:
            True if removed successfully
        """
        if identifier in self._gates:
            del self._gates[identifier]
            self.logger.info(f"Removed human gate {identifier}")
            return True
        return False
    
    def get_all_gates(self) -> List[HumanGate]:
        """Get all human gates.
        
        Returns:
            List of human gates
        """
        return list(self._gates.values())
    
    def get_gates_by_type(self, gate_type: GateType) -> List[HumanGate]:
        """Get gates by type.
        
        Args:
            gate_type: Gate type
            
        Returns:
            List of gates
        """
        return [gate for gate in self._gates.values() if gate.gate_type == gate_type]
    
    def get_gates_by_priority(self, priority: GatePriority) -> List[HumanGate]:
        """Get gates by priority.
        
        Args:
            priority: Gate priority
            
        Returns:
            List of gates
        """
        return [gate for gate in self._gates.values() if gate.priority == priority]
    
    def get_all_pending_requests(self) -> List[GateRequest]:
        """Get all pending requests across all gates.
        
        Returns:
            List of pending requests
        """
        pending_requests = []
        for gate in self._gates.values():
            pending_requests.extend(gate.get_pending_requests())
        return pending_requests
    
    def get_requests_by_user(self, user_id: str) -> List[GateRequest]:
        """Get all requests assigned to a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of requests
        """
        requests = []
        for gate in self._gates.values():
            requests.extend(gate.get_requests_by_user(user_id))
        return requests
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics.
        
        Returns:
            System statistics
        """
        total_gates = len(self._gates)
        total_requests = sum(gate.metrics.total_requests for gate in self._gates.values())
        pending_requests = sum(gate.metrics.pending_requests for gate in self._gates.values())
        approved_requests = sum(gate.metrics.approved_requests for gate in self._gates.values())
        rejected_requests = sum(gate.metrics.rejected_requests for gate in self._gates.values())
        timeout_requests = sum(gate.metrics.timeout_requests for gate in self._gates.values())
        
        return {
            "total_gates": total_gates,
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "timeout_requests": timeout_requests,
            "approval_rate": approved_requests / total_requests if total_requests > 0 else 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global human gate manager
_human_gate_manager: Optional[HumanGateManager] = None


def get_human_gate_manager() -> HumanGateManager:
    """Get global human gate manager.
    
    Returns:
        HumanGateManager instance
    """
    global _human_gate_manager
    
    if _human_gate_manager is None:
        _human_gate_manager = HumanGateManager()
    
    return _human_gate_manager
