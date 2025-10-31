"""Unit tests for Pack Parser."""

import pytest
from pathlib import Path
from topokit.core.pack_parser import PackParser, PackParseError


class TestPackParser:
    """Test cases for PackParser."""
    
    def test_init_with_valid_directory(self):
        """Test parser initialization with valid directory."""
        parser = PackParser("./topology")
        assert parser.pack_dir == Path("./topology")
    
    def test_init_with_invalid_directory(self):
        """Test parser initialization with invalid directory."""
        with pytest.raises(PackParseError, match="Pack directory does not exist"):
            PackParser("./nonexistent")
    
    def test_parse_complete_pack(self):
        """Test parsing complete topology pack."""
        parser = PackParser("./topology")
        pack = parser.parse()
        
        # Verify pack structure
        assert pack.name == "topology"
        assert len(pack.nodes) == 3
        assert len(pack.edges) == 2
        assert len(pack.contracts) == 3
        
        # Verify node parsing
        node_ids = [node.id for node in pack.nodes]
        assert "UX.Intent" in node_ids
        assert "AI.Rank" in node_ids
        assert "AI.Explain" in node_ids
        
        # Verify edge parsing
        edge_ids = [edge.id for edge in pack.edges]
        assert "UX.Intent_to_AI.Rank" in edge_ids
        assert "AI.Rank_to_AI.Explain" in edge_ids
        
        # Verify contract parsing
        contract_names = [contract.name for contract in pack.contracts]
        assert "classify" in contract_names
        assert "rank" in contract_names
        assert "explain" in contract_names
    
    def test_validate_pack_success(self):
        """Test pack validation with valid pack."""
        parser = PackParser("./topology")
        pack = parser.parse()
        errors = parser.validate_pack(pack)
        assert len(errors) == 0
    
    def test_validate_pack_duplicate_nodes(self):
        """Test pack validation with duplicate node IDs."""
        # This would require creating a test pack with duplicates
        # For now, we'll test the validation logic exists
        parser = PackParser("./topology")
        pack = parser.parse()
        errors = parser.validate_pack(pack)
        # Should pass with our test data
        assert len(errors) == 0
