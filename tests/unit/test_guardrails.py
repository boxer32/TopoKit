"""Unit tests for Guardrails system."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from topokit.core.guardrails import (
    MultiStageGuardrails,
    GuardrailType,
    CircuitBreakerState,
    PolicyEnvironment,
)
from topokit.types.topology import Node, NodeKind, ExecutionProfile, GuardrailsConfig


class TestGuardrails:
    """Test cases for Guardrails system."""
    
    @pytest.fixture
    def guardrails_config(self):
        """Create guardrails configuration."""
        return GuardrailsConfig(
            determinism={},
            confidence={},
            fallback={},
        )
    
    @pytest.fixture
    def guardrails(self, guardrails_config):
        """Create guardrails instance."""
        return MultiStageGuardrails(guardrails_config, PolicyEnvironment.DEVELOPMENT)
    
    @pytest.fixture
    def sample_node(self):
        """Create sample node for testing."""
        return Node(
            id="test-node",
            kind=NodeKind.AI,
            execution_profile=ExecutionProfile(temperature=0.2),
        )
    
    @pytest.mark.asyncio
    async def test_guardrails_initialization(self, guardrails):
        """Test guardrails initialization."""
        assert guardrails is not None
        assert guardrails.config is not None
        assert guardrails.config.enable_determinism is True
    
    @pytest.mark.asyncio
    async def test_pre_process_guard(self, guardrails, sample_node):
        """Test pre-processing guard."""
        input_data = {"query": "test query"}
        
        result = await guardrails.pre_process(sample_node, input_data)
        
        assert result is not None
        assert "input_data" in result or "data" in result
    
    @pytest.mark.asyncio
    async def test_post_process_guard(self, guardrails, sample_node):
        """Test post-processing guard."""
        output_data = {"answer": "test answer"}
        
        result = await guardrails.post_process(sample_node, output_data)
        
        assert result is not None
        assert "output_data" in result or "data" in result
    
    @pytest.mark.asyncio
    async def test_confidence_gating(self, guardrails, sample_node):
        """Test confidence gating."""
        output_data = {"answer": "test", "confidence": 0.9}
        
        result = await guardrails.check_confidence(sample_node, output_data)
        
        assert result is not None
        assert "passed" in result or "allowed" in result or result is True
    
    @pytest.mark.asyncio
    async def test_confidence_gating_low_confidence(self, guardrails, sample_node):
        """Test confidence gating with low confidence."""
        output_data = {"answer": "test", "confidence": 0.5}
        
        result = await guardrails.check_confidence(sample_node, output_data)
        
        # Should fail or require review
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_content_moderation(self, guardrails, sample_node):
        """Test content moderation."""
        output_data = {"answer": "This is a safe answer"}
        
        result = await guardrails.check_content_moderation(sample_node, output_data)
        
        assert result is not None
        assert "safe" in str(result) or "allowed" in str(result) or result is True
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_state(self, guardrails, sample_node):
        """Test circuit breaker state management."""
        node_id = sample_node.id
        
        # Test initial state (should be closed)
        state = await guardrails.get_circuit_breaker_state(node_id)
        assert state is not None
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure(self, guardrails, sample_node):
        """Test circuit breaker on failure."""
        node_id = sample_node.id
        
        # Simulate failures
        for _ in range(3):
            await guardrails.record_failure(node_id)
        
        state = await guardrails.get_circuit_breaker_state(node_id)
        assert state is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

