"""Workflow type definitions for TopoKit advanced workflows."""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from topokit.types.topology import TopologyPack


class WorkflowStatus(str, Enum):
    """Workflow execution status types."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkflowStep(BaseModel):
    """A step in a workflow execution."""
    id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Step name")
    topology_id: str = Field(..., description="Topology pack identifier to execute")
    input_mapping: Dict[str, Any] = Field(default_factory=dict, description="Input data mapping")
    output_mapping: Dict[str, Any] = Field(default_factory=dict, description="Output data mapping")
    depends_on: List[str] = Field(default_factory=list, description="Step dependencies")
    timeout_seconds: int = Field(gt=0, default=300, description="Step timeout in seconds")
    retry_count: int = Field(ge=0, default=0, description="Number of retries on failure")
    enabled: bool = Field(default=True, description="Whether step is enabled")


class WorkflowConfig(BaseModel):
    """Workflow execution configuration."""
    max_parallel_steps: int = Field(gt=0, default=1, description="Maximum parallel step executions")
    failure_policy: str = Field(default="stop", description="Failure policy: stop, continue, retry")
    timeout_seconds: int = Field(gt=0, default=3600, description="Overall workflow timeout")
    retry_on_failure: bool = Field(default=False, description="Retry failed steps automatically")
    resume_on_restart: bool = Field(default=True, description="Resume workflow from last checkpoint")
    checkpoints_enabled: bool = Field(default=True, description="Enable checkpoint saving")


class WorkflowExecution(BaseModel):
    """Workflow execution instance."""
    id: str = Field(..., description="Unique execution identifier")
    workflow_id: str = Field(..., description="Workflow definition identifier")
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="Current execution status")
    started_at: Optional[datetime] = Field(default=None, description="Execution start time")
    completed_at: Optional[datetime] = Field(default=None, description="Execution completion time")
    steps_completed: List[str] = Field(default_factory=list, description="Completed step IDs")
    steps_failed: List[str] = Field(default_factory=list, description="Failed step IDs")
    current_step: Optional[str] = Field(default=None, description="Currently executing step ID")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Workflow input data")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="Workflow output data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    checkpoint_data: Optional[Dict[str, Any]] = Field(default=None, description="Checkpoint data for resume")
    
    def mark_step_completed(self, step_id: str) -> None:
        """Mark a step as completed."""
        if step_id not in self.steps_completed:
            self.steps_completed.append(step_id)
        if step_id in self.steps_failed:
            self.steps_failed.remove(step_id)
        if self.current_step == step_id:
            self.current_step = None
    
    def mark_step_failed(self, step_id: str, error: str) -> None:
        """Mark a step as failed."""
        if step_id not in self.steps_failed:
            self.steps_failed.append(step_id)
        self.error = error
        if self.current_step == step_id:
            self.current_step = None
    
    def is_complete(self) -> bool:
        """Check if workflow execution is complete."""
        return self.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]
    
    def get_progress_percentage(self, total_steps: int) -> float:
        """Get execution progress percentage."""
        if total_steps == 0:
            return 100.0
        return (len(self.steps_completed) / total_steps) * 100.0


class WorkflowPolicy(BaseModel):
    """Policy configuration for workflow execution."""
    require_approval: bool = Field(default=False, description="Require human approval before execution")
    approval_timeout_minutes: int = Field(gt=0, default=60, description="Approval timeout in minutes")
    allowed_users: Optional[List[str]] = Field(default=None, description="Allowed users for execution")
    allowed_roles: Optional[List[str]] = Field(default=None, description="Allowed roles for execution")
    rate_limit_per_hour: Optional[int] = Field(default=None, description="Rate limit per hour")
    cost_limit_usd: Optional[float] = Field(default=None, description="Cost limit in USD per execution")
    guardrails_enabled: bool = Field(default=True, description="Enable guardrails for workflow")


class WorkflowMetadata(BaseModel):
    """Workflow metadata and information."""
    description: Optional[str] = Field(default=None, description="Workflow description")
    author: str = Field(..., description="Workflow author")
    version: str = Field(default="1.0.0", description="Workflow version")
    tags: List[str] = Field(default_factory=list, description="Workflow tags")
    category: Optional[str] = Field(default=None, description="Workflow category")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    last_executed_at: Optional[datetime] = Field(default=None, description="Last execution timestamp")
    execution_count: int = Field(ge=0, default=0, description="Total execution count")
    success_count: int = Field(ge=0, default=0, description="Successful execution count")
    failure_count: int = Field(ge=0, default=0, description="Failed execution count")


class Workflow(BaseModel):
    """Workflow model for advanced multi-step workflows."""
    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Workflow name")
    steps: List[WorkflowStep] = Field(..., description="Workflow steps")
    config: WorkflowConfig = Field(default_factory=WorkflowConfig, description="Workflow configuration")
    policy: WorkflowPolicy = Field(default_factory=WorkflowPolicy, description="Workflow policy")
    metadata: WorkflowMetadata = Field(..., description="Workflow metadata")
    topology_references: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of step IDs to topology pack paths/IDs"
    )
    variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow-level variables and configuration"
    )
    integrations: Dict[str, Any] = Field(
        default_factory=dict,
        description="External system integrations configuration"
    )
    
    def validate(self) -> List[str]:
        """Validate workflow definition and return list of errors."""
        errors = []
        
        # Check for duplicate step IDs
        step_ids = [step.id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("Duplicate step IDs found")
        
        # Check for circular dependencies
        step_map = {step.id: step for step in self.steps}
        for step in self.steps:
            visited = set()
            if self._has_circular_dependency(step.id, step.depends_on, step_map, visited):
                errors.append(f"Circular dependency detected for step {step.id}")
        
        # Check that all dependencies exist
        all_step_ids = set(step_ids)
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in all_step_ids:
                    errors.append(f"Step {step.id} depends on non-existent step {dep}")
        
        # Check topology references
        for step in self.steps:
            if step.topology_id not in self.topology_references:
                errors.append(f"Step {step.id} references unknown topology {step.topology_id}")
        
        return errors
    
    def _has_circular_dependency(
        self,
        current_step: str,
        dependencies: List[str],
        step_map: Dict[str, WorkflowStep],
        visited: set
    ) -> bool:
        """Check for circular dependencies using DFS."""
        if current_step in visited:
            return True
        visited.add(current_step)
        
        for dep in dependencies:
            if dep in step_map:
                if self._has_circular_dependency(dep, step_map[dep].depends_on, step_map, visited.copy()):
                    return True
        return False
    
    def get_entry_steps(self) -> List[WorkflowStep]:
        """Get workflow entry steps (steps with no dependencies)."""
        return [step for step in self.steps if len(step.depends_on) == 0 and step.enabled]
    
    def get_exit_steps(self) -> List[WorkflowStep]:
        """Get workflow exit steps (steps that no other steps depend on)."""
        all_dependencies = set()
        for step in self.steps:
            all_dependencies.update(step.depends_on)
        return [step for step in self.steps if step.id not in all_dependencies and step.enabled]
    
    def get_ready_steps(self, completed_steps: List[str]) -> List[WorkflowStep]:
        """Get steps that are ready to execute (all dependencies completed)."""
        completed_set = set(completed_steps)
        return [
            step for step in self.steps
            if step.enabled
            and step.id not in completed_set
            and all(dep in completed_set for dep in step.depends_on)
        ]
    
    def update_metadata(self) -> None:
        """Update workflow metadata timestamps."""
        self.metadata.updated_at = datetime.utcnow()
    
    def record_execution(self, success: bool) -> None:
        """Record workflow execution result."""
        self.metadata.execution_count += 1
        if success:
            self.metadata.success_count += 1
        else:
            self.metadata.failure_count += 1
        self.metadata.last_executed_at = datetime.utcnow()
        self.update_metadata()

