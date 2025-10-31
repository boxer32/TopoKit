"""Enhanced Schema Validator for TopoKit with lenient parsing, auto-repair, and streaming validation."""

import json
import re
import asyncio
import time
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
import logging

try:
    import jsonschema
    from jsonschema import Draft7Validator, Draft202012Validator, ValidationError as JsonSchemaError
    from jsonschema.exceptions import SchemaError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

try:
    import zod
    ZOD_AVAILABLE = True
except ImportError:
    ZOD_AVAILABLE = False

from ..types.validation import ValidationResult, ValidationError, ValidationErrorType
from .logging import get_logger


@dataclass
class ValidationMetrics:
    """Validation performance metrics."""
    total_validations: int = 0
    successful_validations: int = 0
    failed_validations: int = 0
    auto_repairs_applied: int = 0
    average_validation_time_ms: float = 0.0
    last_validation_time: Optional[datetime] = None


class LenientJSONParser:
    """Enhanced lenient JSON parser with auto-repair capabilities."""
    
    def __init__(self):
        """Initialize lenient parser."""
        self.repair_strategies = {
            'fix_trailing_commas': True,
            'fix_unquoted_keys': True,
            'fix_single_quotes': True,
            'fix_missing_commas': True,
            'fix_unescaped_quotes': True,
            'fix_boolean_casing': True,
            'fix_null_values': True,
            'fix_nan_values': True,
            'fix_infinity_values': True,
            'fix_undefined_values': True,
        }
        self.logger = get_logger(__name__)
    
    def parse(self, json_string: str) -> ValidationResult:
        """Parse JSON string with lenient parsing and auto-repair."""
        original_input = json_string
        repair_attempts = 0
        errors = []
        
        # Try parsing as-is first
        try:
            data = json.loads(json_string)
            return ValidationResult(
                success=True,
                data=data,
                original_input=original_input,
                repair_attempts=repair_attempts
            )
        except json.JSONDecodeError as e:
            errors.append(ValidationError(
                type=ValidationErrorType.SYNTAX_ERROR,
                message=f"JSON syntax error: {e.msg}",
                path=str(e.pos) if hasattr(e, 'pos') else "unknown",
                severity="medium",
                repairable=True,
                suggestion="Attempting auto-repair"
            ))
        
        # Apply repair strategies
        repaired_input = json_string
        for strategy_name, enabled in self.repair_strategies.items():
            if not enabled:
                continue
                
            repair_attempts += 1
            try:
                repaired_input = self._apply_repair_strategy(repaired_input, strategy_name)
                data = json.loads(repaired_input)
                return ValidationResult(
                    success=True,
                    data=data,
                    original_input=original_input,
                    repaired_input=repaired_input,
                    repair_attempts=repair_attempts
                )
            except json.JSONDecodeError:
                continue
        
        # If all repair attempts failed
        return ValidationResult(
            success=False,
            errors=errors,
            original_input=original_input,
            repair_attempts=repair_attempts
        )
    
    def _apply_repair_strategy(self, json_string: str, strategy: str) -> str:
        """Apply specific repair strategy to JSON string."""
        if strategy == 'fix_trailing_commas':
            # Remove trailing commas before closing brackets/braces
            json_string = re.sub(r',(\s*[}\]])', r'\1', json_string)
        
        elif strategy == 'fix_unquoted_keys':
            # Quote unquoted object keys
            json_string = re.sub(r'(\w+):', r'"\1":', json_string)
        
        elif strategy == 'fix_single_quotes':
            # Replace single quotes with double quotes
            json_string = json_string.replace("'", '"')
        
        elif strategy == 'fix_missing_commas':
            # Add missing commas between object/array elements
            json_string = re.sub(r'"\s*\n\s*"', '",\n"', json_string)
            json_string = re.sub(r'}\s*\n\s*{', '},\n{', json_string)
            json_string = re.sub(r']\s*\n\s*\[', '],\n[', json_string)
        
        elif strategy == 'fix_unescaped_quotes':
            # Escape unescaped quotes in strings
            json_string = re.sub(r'(?<!\\)"(?![,}\]\s])', r'\\"', json_string)
        
        elif strategy == 'fix_boolean_casing':
            # Fix boolean casing
            json_string = re.sub(r'\btrue\b', 'true', json_string, flags=re.IGNORECASE)
            json_string = re.sub(r'\bfalse\b', 'false', json_string, flags=re.IGNORECASE)
        
        elif strategy == 'fix_null_values':
            # Fix null values
            json_string = re.sub(r'\bnull\b', 'null', json_string, flags=re.IGNORECASE)
        
        elif strategy == 'fix_nan_values':
            # Fix NaN values
            json_string = re.sub(r'\bNaN\b', 'null', json_string, flags=re.IGNORECASE)
        
        elif strategy == 'fix_infinity_values':
            # Fix Infinity values
            json_string = re.sub(r'\bInfinity\b', 'null', json_string, flags=re.IGNORECASE)
            json_string = re.sub(r'\b-Infinity\b', 'null', json_string, flags=re.IGNORECASE)
        
        elif strategy == 'fix_undefined_values':
            # Fix undefined values
            json_string = re.sub(r'\bundefined\b', 'null', json_string, flags=re.IGNORECASE)
        
        return json_string
    
    async def parse_streaming(self, json_stream: AsyncGenerator[str, None]) -> AsyncGenerator[ValidationResult, None]:
        """Parse streaming JSON data with lenient parsing.
        
        Args:
            json_stream: Async generator yielding JSON chunks
            
        Yields:
            ValidationResult for each parsed chunk
        """
        buffer = ""
        async for chunk in json_stream:
            buffer += chunk
            
            # Try to parse complete JSON objects
            while buffer:
                try:
                    # Find the end of a complete JSON object
                    brace_count = 0
                    bracket_count = 0
                    in_string = False
                    escape_next = False
                    
                    for i, char in enumerate(buffer):
                        if escape_next:
                            escape_next = False
                            continue
                        
                        if char == '\\':
                            escape_next = True
                            continue
                        
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue
                        
                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                            elif char == '[':
                                bracket_count += 1
                            elif char == ']':
                                bracket_count -= 1
                            
                            # If we have a complete object/array
                            if brace_count == 0 and bracket_count == 0 and i > 0:
                                complete_json = buffer[:i+1]
                                buffer = buffer[i+1:]
                                
                                # Parse the complete JSON
                                result = self.parse(complete_json)
                                yield result
                                break
                    else:
                        # No complete JSON found, wait for more data
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error parsing streaming JSON: {e}")
                    yield ValidationResult(
                        success=False,
                        errors=[ValidationError(
                            type=ValidationErrorType.SYNTAX_ERROR,
                            message=f"Streaming parse error: {str(e)}",
                            path="stream",
                            severity="high",
                            repairable=False
                        )]
                    )
                    break


class SchemaValidator:
    """Enhanced JSON Schema validator with lenient parsing, auto-repair, and streaming validation."""
    
    def __init__(self, 
                 lenient_parsing: bool = True, 
                 auto_repair: bool = True,
                 schema_version: str = "draft7",
                 enable_zod: bool = False,
                 validation_timeout_ms: int = 10000):
        """Initialize enhanced schema validator.
        
        Args:
            lenient_parsing: Enable lenient JSON parsing
            auto_repair: Enable auto-repair for common JSON issues
            schema_version: JSON Schema version (draft7, draft202012)
            enable_zod: Enable Zod validation (if available)
            validation_timeout_ms: Validation timeout in milliseconds
        """
        if not JSONSCHEMA_AVAILABLE:
            raise ImportError("jsonschema not available. Install jsonschema package.")
        
        self.lenient_parsing = lenient_parsing
        self.auto_repair = auto_repair
        self.schema_version = schema_version
        self.enable_zod = enable_zod and ZOD_AVAILABLE
        self.validation_timeout_ms = validation_timeout_ms
        
        self.lenient_parser = LenientJSONParser() if lenient_parsing else None
        self.logger = get_logger(__name__)
        
        # Performance metrics
        self.metrics = ValidationMetrics()
        
        # Schema cache
        self._schema_cache: Dict[str, Any] = {}
        self._validator_cache: Dict[str, Any] = {}
        
        # Custom validators
        self._custom_validators: Dict[str, Callable] = {}
        
        # Initialize Zod if enabled
        if self.enable_zod:
            self._init_zod()
    
    def _init_zod(self):
        """Initialize Zod validation."""
        if not ZOD_AVAILABLE:
            self.logger.warning("Zod not available, disabling Zod validation")
            self.enable_zod = False
            return
        
        try:
            # Initialize Zod schemas cache
            self._zod_schemas: Dict[str, Any] = {}
            self.logger.info("Zod validation enabled")
        except Exception as e:
            self.logger.error(f"Failed to initialize Zod: {e}")
            self.enable_zod = False
    
    def _get_validator(self, schema: Dict[str, Any]) -> Any:
        """Get or create validator for schema.
        
        Args:
            schema: JSON Schema
            
        Returns:
            Validator instance
        """
        schema_key = json.dumps(schema, sort_keys=True)
        
        if schema_key in self._validator_cache:
            return self._validator_cache[schema_key]
        
        # Create validator based on schema version
        if self.schema_version == "draft7":
            validator = Draft7Validator(schema)
        elif self.schema_version == "draft202012":
            validator = Draft202012Validator(schema)
        else:
            validator = Draft7Validator(schema)
        
        self._validator_cache[schema_key] = validator
        return validator
    
    def validate(self, data: Any, schema: Dict[str, Any]) -> ValidationResult:
        """Validate data against schema with enhanced features.
        
        Args:
            data: Data to validate (can be string or parsed object)
            schema: JSON Schema to validate against
            
        Returns:
            ValidationResult with validation outcome
        """
        start_time = time.time()
        self.metrics.total_validations += 1
        
        errors = []
        repair_attempts = 0
        original_input = ""
        repaired_input = None
        
        try:
            # Handle string input with lenient parsing
            if isinstance(data, str) and self.lenient_parsing:
                original_input = data
                parse_result = self.lenient_parser.parse(data)
                if not parse_result.success:
                    self.metrics.failed_validations += 1
                    return parse_result
                data = parse_result.data
                repair_attempts = parse_result.repair_attempts
                repaired_input = parse_result.repaired_input
                if repair_attempts > 0:
                    self.metrics.auto_repairs_applied += 1
            
            # Validate schema structure
            try:
                validator = self._get_validator(schema)
            except SchemaError as e:
                errors.append(ValidationError(
                    type=ValidationErrorType.SCHEMA_ERROR,
                    message=f"Invalid schema: {e.message}",
                    path="schema",
                    severity="critical",
                    repairable=False
                ))
                self.metrics.failed_validations += 1
                return ValidationResult(
                    success=False,
                    errors=errors,
                    original_input=original_input,
                    repair_attempts=repair_attempts
                )
            
            # Apply custom validators
            for validator_name, custom_validator in self._custom_validators.items():
                try:
                    custom_result = custom_validator(data, schema)
                    if not custom_result.success:
                        errors.extend(custom_result.errors)
                except Exception as e:
                    self.logger.error(f"Custom validator {validator_name} failed: {e}")
                    errors.append(ValidationError(
                        type=ValidationErrorType.CUSTOM_ERROR,
                        message=f"Custom validator {validator_name} failed: {str(e)}",
                        path="custom",
                        severity="medium",
                        repairable=False
                    ))
            
            # Validate data against schema
            try:
                validator.validate(data)
                self.metrics.successful_validations += 1
                
                # Update metrics
                validation_time = (time.time() - start_time) * 1000
                self._update_metrics(validation_time)
                
                return ValidationResult(
                    success=True,
                    data=data,
                    original_input=original_input,
                    repaired_input=repaired_input,
                    repair_attempts=repair_attempts
                )
            except JsonSchemaError as e:
                errors.append(ValidationError(
                    type=ValidationErrorType.SCHEMA_ERROR,
                    message=e.message,
                    path=".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root",
                    severity="high",
                    repairable=False,
                    suggestion=f"Expected: {e.validator} - {e.message}"
                ))
                
                self.metrics.failed_validations += 1
                validation_time = (time.time() - start_time) * 1000
                self._update_metrics(validation_time)
                
                return ValidationResult(
                    success=False,
                    data=data,
                    errors=errors,
                    original_input=original_input,
                    repaired_input=repaired_input,
                    repair_attempts=repair_attempts
                )
                
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            self.metrics.failed_validations += 1
            validation_time = (time.time() - start_time) * 1000
            self._update_metrics(validation_time)
            
            return ValidationResult(
                success=False,
                errors=[ValidationError(
                    type=ValidationErrorType.UNKNOWN_ERROR,
                    message=f"Validation error: {str(e)}",
                    path="unknown",
                    severity="critical",
                    repairable=False
                )],
                original_input=original_input,
                repair_attempts=repair_attempts
            )
    
    def _update_metrics(self, validation_time_ms: float):
        """Update validation metrics."""
        if self.metrics.average_validation_time_ms == 0:
            self.metrics.average_validation_time_ms = validation_time_ms
        else:
            # Update running average
            self.metrics.average_validation_time_ms = (
                (self.metrics.average_validation_time_ms * (self.metrics.total_validations - 1) + validation_time_ms) 
                / self.metrics.total_validations
            )
        
        self.metrics.last_validation_time = datetime.now(timezone.utc)
    
    def get_validation_errors(self, result: ValidationResult) -> List[str]:
        """Get human-readable validation errors.
        
        Args:
            result: Validation result
            
        Returns:
            List of error messages
        """
        return [f"{error.path}: {error.message}" for error in result.errors]
    
    def is_repairable(self, result: ValidationResult) -> bool:
        """Check if validation errors are repairable.
        
        Args:
            result: Validation result
            
        Returns:
            True if errors can be auto-repaired
        """
        return any(error.repairable for error in result.errors)
    
    def get_error_suggestions(self, result: ValidationResult) -> List[str]:
        """Get error suggestions for failed validations.
        
        Args:
            result: Validation result
            
        Returns:
            List of suggestions
        """
        suggestions = []
        for error in result.errors:
            if error.suggestion:
                suggestions.append(f"{error.path}: {error.suggestion}")
        return suggestions
    
    def add_custom_validator(self, name: str, validator_func: Callable) -> None:
        """Add custom validator function.
        
        Args:
            name: Validator name
            validator_func: Validator function that returns ValidationResult
        """
        self._custom_validators[name] = validator_func
        self.logger.info(f"Added custom validator: {name}")
    
    def remove_custom_validator(self, name: str) -> None:
        """Remove custom validator.
        
        Args:
            name: Validator name
        """
        if name in self._custom_validators:
            del self._custom_validators[name]
            self.logger.info(f"Removed custom validator: {name}")
    
    def clear_cache(self) -> None:
        """Clear schema and validator cache."""
        self._schema_cache.clear()
        self._validator_cache.clear()
        if self.enable_zod:
            self._zod_schemas.clear()
        self.logger.info("Cleared validation cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Cache statistics
        """
        stats = {
            "schema_cache_size": len(self._schema_cache),
            "validator_cache_size": len(self._validator_cache),
            "custom_validators_count": len(self._custom_validators)
        }
        
        if self.enable_zod:
            stats["zod_schemas_count"] = len(self._zod_schemas)
        
        return stats
    
    def get_metrics(self) -> ValidationMetrics:
        """Get validation metrics.
        
        Returns:
            Validation metrics
        """
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset validation metrics."""
        self.metrics = ValidationMetrics()
        self.logger.info("Reset validation metrics")
    
    def validate_batch(self, data_list: List[Any], schema: Dict[str, Any]) -> List[ValidationResult]:
        """Validate multiple data items against schema.
        
        Args:
            data_list: List of data items to validate
            schema: JSON Schema to validate against
            
        Returns:
            List of validation results
        """
        results = []
        for data in data_list:
            result = self.validate(data, schema)
            results.append(result)
        return results
    
    async def validate_async(self, data: Any, schema: Dict[str, Any]) -> ValidationResult:
        """Asynchronous validation with timeout.
        
        Args:
            data: Data to validate
            schema: JSON Schema to validate against
            
        Returns:
            Validation result
        """
        try:
            # Run validation with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(self.validate, data, schema),
                timeout=self.validation_timeout_ms / 1000.0
            )
            return result
        except asyncio.TimeoutError:
            self.logger.error(f"Validation timeout after {self.validation_timeout_ms}ms")
            return ValidationResult(
                success=False,
                errors=[ValidationError(
                    type=ValidationErrorType.TIMEOUT_ERROR,
                    message=f"Validation timeout after {self.validation_timeout_ms}ms",
                    path="timeout",
                    severity="high",
                    repairable=False
                )]
            )
        except Exception as e:
            self.logger.error(f"Async validation error: {e}")
            return ValidationResult(
                success=False,
                errors=[ValidationError(
                    type=ValidationErrorType.UNKNOWN_ERROR,
                    message=f"Async validation error: {str(e)}",
                    path="async",
                    severity="critical",
                    repairable=False
                )]
            )
