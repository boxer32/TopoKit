#!/usr/bin/env python3
"""Debug EdgePolicy model with correct field names"""

import sys
from pathlib import Path

# Add the core package to the path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "core"))

from topokit.types.topology import EdgePolicy

# Test EdgePolicy creation with correct field names
try:
    edge = EdgePolicy(
        id="test_edge",
        from_node="node1",
        to_node="node2",
        version="1.0.0",
        contracts=["test"],
        allow=True,
        timeout_ms=5000,
        max_retries=1
    )
    print("✓ EdgePolicy created successfully with from_node/to_node")
    print(f"Edge: {edge}")
except Exception as e:
    print(f"✗ EdgePolicy creation with from_node/to_node failed: {e}")
    
    # Try with the aliases
    try:
        edge = EdgePolicy(
            id="test_edge",
            from_node="node1",
            to_node="node2", 
            version="1.0.0",
            contracts=["test"],
            allow=True,
            timeout_ms=5000,
            max_retries=1
        )
        print("✓ EdgePolicy created successfully with aliases")
        print(f"Edge: {edge}")
    except Exception as e2:
        print(f"✗ EdgePolicy creation with aliases also failed: {e2}")
        
        # Try with dict approach
        try:
            edge_data = {
                "id": "test_edge",
                "from": "node1",
                "to": "node2",
                "version": "1.0.0",
                "contracts": ["test"],
                "allow": True,
                "timeout_ms": 5000,
                "max_retries": 1
            }
            edge = EdgePolicy(**edge_data)
            print("✓ EdgePolicy created successfully with dict and aliases")
            print(f"Edge: {edge}")
        except Exception as e3:
            print(f"✗ EdgePolicy creation with dict also failed: {e3}")
