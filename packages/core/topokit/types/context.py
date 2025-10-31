"""Context type definitions for TopoKit."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class ContextMetadata(BaseModel):
    """Metadata for context operations."""
    node_id: str
    trace_id: str
    user_id: Optional[str] = None
    session_id: str
    operation: str = Field(..., description="Operation type: create, update, merge, conflict_resolution")
    changes: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: Optional[float] = None


class ContextVersion(BaseModel):
    """Versioned context state."""
    version: int
    data: Dict[str, Any]
    metadata: ContextMetadata
    timestamp: datetime
    checksum: str
    parent_version: Optional[int] = None


class ContextStore:
    """Interface for context storage."""
    
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current context for session."""
        raise NotImplementedError
    
    async def upsert(self, session_id: str, patch: Dict[str, Any]) -> None:
        """Update context for session."""
        raise NotImplementedError
