"""Validation type definitions for TopoKit."""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum


class ValidationErrorType(str, Enum):
    """Types of validation errors."""
    SYNTAX_ERROR = "syntax_error"
    SEMANTIC_ERROR = "semantic_error"
    TYPE_ERROR = "type_error"
    SCHEMA_ERROR = "schema_error"
    STREAMING_ERROR = "streaming_error"
    CUSTOM_ERROR = "custom_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


class ValidationError(BaseModel):
    """Validation error details."""
    type: ValidationErrorType
    message: str
    path: str
    severity: str = Field(..., description="Error severity: low, medium, high, critical")
    repairable: bool = False
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validation operation."""
    success: bool
    data: Optional[Any] = None
    errors: List[ValidationError] = Field(default_factory=list)
    repair_attempts: int = 0
    original_input: str = ""
    repaired_input: Optional[str] = None


class Contract(BaseModel):
    """JSON Schema contract for data exchange between nodes."""
    name: str
    version: str = Field(default="1.0.0")
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    description: Optional[str] = None
