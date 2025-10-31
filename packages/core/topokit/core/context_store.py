"""Enhanced Context Store for TopoKit with CRDT-based conflict resolution and versioning."""

import asyncio
import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict

from ..types.context import ContextStore, ContextVersion, ContextMetadata


class MergeStrategy(str, Enum):
    """CRDT merge strategies."""
    LAST_WRITE_WINS = "last_write_wins"
    FIELD_LEVEL_CRDT = "field_level_crdt"
    PRIORITY_BASED = "priority_based"
    CONSENSUS_BASED = "consensus_based"


class ConflictResolutionStrategy(str, Enum):
    """Conflict resolution strategies."""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    HYBRID = "hybrid"


@dataclass
class ContextOperation:
    """Context operation with metadata."""
    operation_id: str
    session_id: str
    node_id: str
    trace_id: str
    operation_type: str  # create, update, delete, merge
    data: Dict[str, Any]
    timestamp: datetime
    version: int
    parent_version: Optional[int] = None
    priority: int = 0
    checksum: str = ""
    
    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum for operation integrity."""
        data_str = json.dumps(self.data, sort_keys=True)
        return hashlib.sha256(f"{self.operation_id}:{data_str}".encode()).hexdigest()[:16]


@dataclass
class ConflictInfo:
    """Information about a conflict."""
    conflict_id: str
    session_id: str
    field_path: str
    conflicting_values: List[Any]
    conflicting_operations: List[ContextOperation]
    resolution_strategy: ConflictResolutionStrategy
    resolved_value: Optional[Any] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class EnhancedContextStore:
    """Enhanced context store with CRDT-based conflict resolution and versioning."""
    
    def __init__(self, 
                 merge_strategy: MergeStrategy = MergeStrategy.FIELD_LEVEL_CRDT,
                 conflict_resolution: ConflictResolutionStrategy = ConflictResolutionStrategy.AUTOMATIC,
                 max_version_history: int = 1000):
        """Initialize enhanced context store.
        
        Args:
            merge_strategy: CRDT merge strategy to use
            conflict_resolution: Conflict resolution strategy
            max_version_history: Maximum number of versions to keep per session
        """
        self.merge_strategy = merge_strategy
        self.conflict_resolution = conflict_resolution
        self.max_version_history = max_version_history
        
        # Storage
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._versions: Dict[str, List[ContextVersion]] = defaultdict(list)
        self._operations: Dict[str, List[ContextOperation]] = defaultdict(list)
        self._conflicts: Dict[str, List[ConflictInfo]] = defaultdict(list)
        
        # Thread safety
        self._lock = threading.RLock()
        self._operation_counter = 0
        self._operation_lock = threading.Lock()
    
    async def get(self, session_id: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get current context for session or specific version.
        
        Args:
            session_id: Session identifier
            version: Specific version to retrieve (None for latest)
            
        Returns:
            Context data or None if not found
        """
        with self._lock:
            if session_id not in self._sessions:
                return None
            
            if version is None:
                return self._sessions[session_id].copy()
            
            # Get specific version
            versions = self._versions[session_id]
            for ctx_version in reversed(versions):
                if ctx_version.version == version:
                    return ctx_version.data.copy()
            
            return None
    
    async def upsert(self, session_id: str, patch: Dict[str, Any], 
                    node_id: str, trace_id: str, user_id: Optional[str] = None) -> ContextVersion:
        """Update context for session with conflict resolution.
        
        Args:
            session_id: Session identifier
            patch: Data to update
            node_id: Node performing the update
            trace_id: Trace identifier
            user_id: User performing the update
            
        Returns:
            New context version
        """
        with self._lock:
            # Get current context
            current_context = self._sessions.get(session_id, {})
            current_version = self._get_latest_version(session_id)
            
            # Create operation
            operation = self._create_operation(
                session_id=session_id,
                node_id=node_id,
                trace_id=trace_id,
                operation_type="update",
                data=patch,
                parent_version=current_version.version if current_version else None
            )
            
            # Apply merge strategy
            if self.merge_strategy == MergeStrategy.LAST_WRITE_WINS:
                merged_data = self._merge_last_write_wins(current_context, patch)
            elif self.merge_strategy == MergeStrategy.FIELD_LEVEL_CRDT:
                merged_data = await self._merge_field_level_crdt(session_id, current_context, patch, operation)
            elif self.merge_strategy == MergeStrategy.PRIORITY_BASED:
                merged_data = self._merge_priority_based(current_context, patch, operation)
            else:
                merged_data = self._merge_consensus_based(session_id, current_context, patch, operation)
            
            # Create new version
            new_version = self._create_version(
                session_id=session_id,
                data=merged_data,
                operation=operation,
                user_id=user_id
            )
            
            # Store version and update session
            self._versions[session_id].append(new_version)
            self._operations[session_id].append(operation)
            self._sessions[session_id] = merged_data
            
            # Cleanup old versions
            self._cleanup_versions(session_id)
            
            return new_version
    
    async def merge(self, session_id: str, other_session_id: str, 
                   merge_strategy: Optional[MergeStrategy] = None) -> ContextVersion:
        """Merge contexts from two sessions.
        
        Args:
            session_id: Primary session ID
            other_session_id: Secondary session ID to merge from
            merge_strategy: Override merge strategy for this operation
            
        Returns:
            New merged context version
        """
        with self._lock:
            if other_session_id not in self._sessions:
                raise ValueError(f"Session {other_session_id} not found")
            
            primary_context = self._sessions[session_id]
            secondary_context = self._sessions[other_session_id]
            
            strategy = merge_strategy or self.merge_strategy
            
            if strategy == MergeStrategy.LAST_WRITE_WINS:
                merged_data = self._merge_last_write_wins(primary_context, secondary_context)
            elif strategy == MergeStrategy.FIELD_LEVEL_CRDT:
                merged_data = await self._merge_field_level_crdt(session_id, primary_context, secondary_context)
            else:
                merged_data = self._merge_priority_based(primary_context, secondary_context)
            
            # Create merge operation
            operation = self._create_operation(
                session_id=session_id,
                node_id="merge_engine",
                trace_id=f"merge_{int(time.time())}",
                operation_type="merge",
                data=merged_data
            )
            
            new_version = self._create_version(
                session_id=session_id,
                data=merged_data,
                operation=operation
            )
            
            self._versions[session_id].append(new_version)
            self._operations[session_id].append(operation)
            self._sessions[session_id] = merged_data
            
            return new_version
    
    def _create_operation(self, session_id: str, node_id: str, trace_id: str, 
                         operation_type: str, data: Dict[str, Any], 
                         parent_version: Optional[int] = None) -> ContextOperation:
        """Create a new context operation."""
        with self._operation_lock:
            self._operation_counter += 1
            operation_id = f"{session_id}_{self._operation_counter}_{int(time.time())}"
        
        return ContextOperation(
            operation_id=operation_id,
            session_id=session_id,
            node_id=node_id,
            trace_id=trace_id,
            operation_type=operation_type,
            data=data,
            timestamp=datetime.now(timezone.utc),
            version=self._operation_counter,
            parent_version=parent_version
        )
    
    def _create_version(self, session_id: str, data: Dict[str, Any], 
                       operation: ContextOperation, user_id: Optional[str] = None) -> ContextVersion:
        """Create a new context version."""
        current_version = self._get_latest_version(session_id)
        new_version_num = (current_version.version + 1) if current_version else 1
        
        metadata = ContextMetadata(
            node_id=operation.node_id,
            trace_id=operation.trace_id,
            user_id=user_id,
            session_id=session_id,
            operation=operation.operation_type,
            changes=[{key: value} for key, value in data.items()],
            confidence=1.0
        )
        
        return ContextVersion(
            version=new_version_num,
            data=data,
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
            checksum=operation.checksum,
            parent_version=operation.parent_version
        )
    
    def _get_latest_version(self, session_id: str) -> Optional[ContextVersion]:
        """Get the latest version for a session."""
        versions = self._versions[session_id]
        return versions[-1] if versions else None
    
    def _merge_last_write_wins(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Merge using last-write-wins strategy."""
        result = base.copy()
        result.update(update)
        return result
    
    async def _merge_field_level_crdt(self, session_id: str, base: Dict[str, Any], 
                                     update: Dict[str, Any], operation: Optional[ContextOperation] = None) -> Dict[str, Any]:
        """Merge using field-level CRDT strategy."""
        result = base.copy()
        conflicts = []
        
        for key, value in update.items():
            if key in result:
                # Check for conflicts
                if result[key] != value:
                    conflict = ConflictInfo(
                        conflict_id=f"{session_id}_{key}_{int(time.time())}",
                        session_id=session_id,
                        field_path=key,
                        conflicting_values=[result[key], value],
                        conflicting_operations=[],
                        resolution_strategy=self.conflict_resolution
                    )
                    conflicts.append(conflict)
                    
                    # Resolve conflict based on strategy
                    if self.conflict_resolution == ConflictResolutionStrategy.AUTOMATIC:
                        # Use timestamp-based resolution
                        result[key] = value
                    elif self.conflict_resolution == ConflictResolutionStrategy.MANUAL:
                        # Keep original value, mark for manual resolution
                        self._conflicts[session_id].append(conflict)
                        continue
                    else:  # HYBRID
                        # Use priority or timestamp
                        result[key] = value
            else:
                result[key] = value
        
        return result
    
    def _merge_priority_based(self, base: Dict[str, Any], update: Dict[str, Any], 
                            operation: Optional[ContextOperation] = None) -> Dict[str, Any]:
        """Merge using priority-based strategy."""
        result = base.copy()
        
        for key, value in update.items():
            if key in result:
                # Compare priorities (higher number = higher priority)
                base_priority = 0
                update_priority = operation.priority if operation else 0
                
                if update_priority >= base_priority:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    def _merge_consensus_based(self, session_id: str, base: Dict[str, Any], 
                              update: Dict[str, Any], operation: Optional[ContextOperation] = None) -> Dict[str, Any]:
        """Merge using consensus-based strategy."""
        # For now, implement as last-write-wins
        # In a full implementation, this would involve consensus algorithms
        return self._merge_last_write_wins(base, update)
    
    def _cleanup_versions(self, session_id: str):
        """Cleanup old versions to maintain max_version_history limit."""
        versions = self._versions[session_id]
        if len(versions) > self.max_version_history:
            # Keep only the most recent versions
            self._versions[session_id] = versions[-self.max_version_history:]
    
    async def get_conflicts(self, session_id: str) -> List[ConflictInfo]:
        """Get unresolved conflicts for a session."""
        with self._lock:
            return self._conflicts[session_id].copy()
    
    async def resolve_conflict(self, session_id: str, conflict_id: str, 
                             resolved_value: Any, resolved_by: str) -> bool:
        """Manually resolve a conflict.
        
        Args:
            session_id: Session identifier
            conflict_id: Conflict identifier
            resolved_value: Resolved value
            resolved_by: User who resolved the conflict
            
        Returns:
            True if conflict was resolved successfully
        """
        with self._lock:
            conflicts = self._conflicts[session_id]
            for conflict in conflicts:
                if conflict.conflict_id == conflict_id:
                    conflict.resolved_value = resolved_value
                    conflict.resolved_at = datetime.now(timezone.utc)
                    conflict.resolved_by = resolved_by
                    
                    # Apply resolution to current context
                    if session_id in self._sessions:
                        self._sessions[session_id][conflict.field_path] = resolved_value
                    
                    return True
            
            return False
    
    async def get_version_history(self, session_id: str, limit: int = 50) -> List[ContextVersion]:
        """Get version history for a session."""
        with self._lock:
            versions = self._versions[session_id]
            return versions[-limit:] if limit else versions.copy()
    
    async def rollback(self, session_id: str, target_version: int) -> bool:
        """Rollback session to a specific version.
        
        Args:
            session_id: Session identifier
            target_version: Version to rollback to
            
        Returns:
            True if rollback was successful
        """
        with self._lock:
            versions = self._versions[session_id]
            for version in reversed(versions):
                if version.version == target_version:
                    self._sessions[session_id] = version.data.copy()
                    return True
            
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context store statistics."""
        with self._lock:
            return {
                "total_sessions": len(self._sessions),
                "total_versions": sum(len(versions) for versions in self._versions.values()),
                "total_operations": sum(len(ops) for ops in self._operations.values()),
                "total_conflicts": sum(len(conflicts) for conflicts in self._conflicts.values()),
                "merge_strategy": self.merge_strategy.value,
                "conflict_resolution": self.conflict_resolution.value,
                "max_version_history": self.max_version_history
            }


# Backward compatibility
ContextStore = EnhancedContextStore
