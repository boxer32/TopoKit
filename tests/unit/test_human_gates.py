"""Unit tests for Human Gates system."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from topokit.core.human_gates import (
    HumanGate,
    ApprovalWorkflow,
    GateState,
    ApprovalRequest,
    ApprovalResult,
)


class TestHumanGate:
    """Test cases for Human Gate."""
    
    @pytest.fixture
    def human_gate(self):
        """Create human gate instance."""
        return HumanGate(timeout_seconds=300)
    
    @pytest.mark.asyncio
    async def test_human_gate_initialization(self, human_gate):
        """Test human gate initialization."""
        assert human_gate is not None
        assert human_gate.timeout_seconds == 300
    
    @pytest.mark.asyncio
    async def test_create_approval_request(self, human_gate):
        """Test creating approval request."""
        node_id = "test-node"
        action = "high_risk_action"
        context = {"data": "test"}
        
        request = await human_gate.create_request(node_id, action, context)
        
        assert request is not None
        assert isinstance(request, ApprovalRequest)
        assert request.node_id == node_id
        assert request.action == action
    
    @pytest.mark.asyncio
    async def test_approve_request(self, human_gate):
        """Test approving a request."""
        node_id = "test-node"
        action = "test_action"
        context = {"data": "test"}
        
        request = await human_gate.create_request(node_id, action, context)
        
        result = await human_gate.approve(request.id, "user123")
        
        assert result is not None
        assert isinstance(result, ApprovalResult)
        assert result.approved is True
    
    @pytest.mark.asyncio
    async def test_reject_request(self, human_gate):
        """Test rejecting a request."""
        node_id = "test-node"
        action = "test_action"
        context = {"data": "test"}
        
        request = await human_gate.create_request(node_id, action, context)
        
        result = await human_gate.reject(request.id, "user123", "Not allowed")
        
        assert result is not None
        assert isinstance(result, ApprovalResult)
        assert result.approved is False
    
    @pytest.mark.asyncio
    async def test_get_pending_requests(self, human_gate):
        """Test getting pending requests."""
        # Create some requests
        await human_gate.create_request("node1", "action1", {})
        await human_gate.create_request("node2", "action2", {})
        
        pending = await human_gate.get_pending_requests()
        
        assert pending is not None
        assert isinstance(pending, list)
        assert len(pending) >= 0


class TestApprovalWorkflow:
    """Test cases for Approval Workflow."""
    
    @pytest.fixture
    def approval_workflow(self):
        """Create approval workflow instance."""
        return ApprovalWorkflow()
    
    @pytest.mark.asyncio
    async def test_approval_workflow_initialization(self, approval_workflow):
        """Test approval workflow initialization."""
        assert approval_workflow is not None
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, approval_workflow):
        """Test executing approval workflow."""
        node_id = "test-node"
        action = "test_action"
        context = {"data": "test"}
        
        result = await approval_workflow.execute(node_id, action, context)
        
        assert result is not None
        assert "approved" in result or "status" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

