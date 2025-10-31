#!/usr/bin/env python3
"""Debug EdgePolicy model"""

import sys
from pathlib import Path

# Add the core package to the path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "core"))

from topokit.types.topology import EdgePolicy

# Test EdgePolicy creation
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
    print("✓ EdgePolicy created successfully")
    print(f"Edge: {edge}")
except Exception as e:
    print(f"✗ EdgePolicy creation failed: {e}")
    print(f"Error type: {type(e)}")
    
    # Try with aliases
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
        print("✓ EdgePolicy created with aliases")
    except Exception as e2:
        print(f"✗ EdgePolicy creation with aliases also failed: {e2}")
