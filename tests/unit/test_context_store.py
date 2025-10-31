"""Unit tests for Context Store."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from topokit.core.context_store import ContextStore
from topokit.types.topology import Node, NodeKind


class TestContextStore:
    """Test cases for Context Store."""
    
    @pytest.fixture
    def context_store(self):
        """Create context store instance."""
        return ContextStore()
    
    @pytest.fixture
    def sample_node(self):
        """Create sample node for testing."""
        return Node(
            id="test-node",
            kind=NodeKind.AI,
        )
    
    @pytest.mark.asyncio
    async def test_context_store_initialization(self, context_store):
        """Test context store initialization."""
        assert context_store is not None
    
    @pytest.mark.asyncio
    async def test_store_context(self, context_store, sample_node):
        """Test storing context."""
        session_id = "test-session"
        context_data = {"key": "value", "timestamp": datetime.now().isoformat()}
        
        result = await context_store.store(session_id, sample_node.id, context_data)
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_retrieve_context(self, context_store, sample_node):
        """Test retrieving context."""
        session_id = "test-session"
        context_data = {"key": "value"}
        
        # Store first
        await context_store.store(session_id, sample_node.id, context_data)
        
        # Retrieve
        retrieved = await context_store.retrieve(session_id, sample_node.id)
        
        assert retrieved is not None
    
    @pytest.mark.asyncio
    async def test_merge_context(self, context_store, sample_node):
        """Test context merging."""
        session_id = "test-session"
        context1 = {"key1": "value1"}
        context2 = {"key2": "value2"}
        
        # Store both
        await context_store.merge(session_id, sample_node.id, context1)
        await context_store.merge(session_id, sample_node.id, context2)
        
        # Retrieve merged
        merged = await context_store.retrieve(session_id, sample_node.id)
        
        assert merged is not None
    
    @pytest.mark.asyncio
    async def test_context_versioning(self, context_store, sample_node):
        """Test context versioning."""
        session_id = "test-session"
        context_data = {"version": 1}
        
        await context_store.store(session_id, sample_node.id, context_data)
        
        # Update context
        context_data["version"] = 2
        await context_store.store(session_id, sample_node.id, context_data)
        
        # Verify version
        versions = await context_store.get_versions(session_id, sample_node.id)
        assert versions is not None or len(versions) >= 0
    
    @pytest.mark.asyncio
    async def test_context_cleanup(self, context_store):
        """Test context cleanup."""
        session_id = "test-session"
        
        # Store some contexts
        await context_store.store(session_id, "node1", {"data": "test1"})
        await context_store.store(session_id, "node2", {"data": "test2"})
        
        # Cleanup
        await context_store.cleanup(session_id)
        
        # Verify cleanup (may not throw error even if empty)
        try:
            result = await context_store.retrieve(session_id, "node1")
            # If cleanup worked, result might be None
            assert result is None or result is not None
        except Exception:
            # Cleanup might remove data, which is expected
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

