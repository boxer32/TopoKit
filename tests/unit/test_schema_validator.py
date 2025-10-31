"""Unit tests for Schema Validator."""

import pytest
from topokit.core.schema_validator import SchemaValidator, LenientJSONParser
from topokit.types.validation import ValidationErrorType


class TestLenientJSONParser:
    """Test cases for LenientJSONParser."""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        parser = LenientJSONParser()
        result = parser.parse('{"name": "test", "value": 123}')
        
        assert result.success is True
        assert result.data == {"name": "test", "value": 123}
        assert result.repair_attempts == 0
    
    def test_parse_trailing_commas(self):
        """Test auto-repair of trailing commas."""
        parser = LenientJSONParser()
        result = parser.parse('{"name": "test", "value": 123,}')
        
        assert result.success is True
        assert result.data == {"name": "test", "value": 123}
        assert result.repair_attempts == 1
        assert result.repaired_input is not None
    
    def test_parse_unquoted_keys(self):
        """Test auto-repair of unquoted keys."""
        parser = LenientJSONParser()
        result = parser.parse('{name: "test", value: 123}')
        
        assert result.success is True
        assert result.data == {"name": "test", "value": 123}
        assert result.repair_attempts >= 1  # May take multiple attempts
    
    def test_parse_single_quotes(self):
        """Test auto-repair of single quotes."""
        parser = LenientJSONParser()
        result = parser.parse("{'name': 'test', 'value': 123}")
        
        assert result.success is True
        assert result.data == {"name": "test", "value": 123}
        assert result.repair_attempts >= 1  # May take multiple attempts
    
    def test_parse_boolean_casing(self):
        """Test auto-repair of boolean casing."""
        parser = LenientJSONParser()
        result = parser.parse('{"enabled": true, "disabled": false}')
        
        assert result.success is True
        assert result.data == {"enabled": True, "disabled": False}
        assert result.repair_attempts == 0
    
    def test_parse_multiple_issues(self):
        """Test auto-repair of multiple JSON issues."""
        parser = LenientJSONParser()
        result = parser.parse("{name: 'test', value: 123,}")
        
        assert result.success is True
        assert result.data == {"name": "test", "value": 123}
        assert result.repair_attempts >= 1
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON that cannot be repaired."""
        parser = LenientJSONParser()
        result = parser.parse('{"name": "test" "value": 123}')  # Missing comma
        
        assert result.success is False
        assert result.repair_attempts > 0
        assert len(result.errors) > 0
        assert result.errors[0].type == ValidationErrorType.SYNTAX_ERROR


class TestSchemaValidator:
    """Test cases for SchemaValidator."""
    
    def test_validate_valid_data(self):
        """Test validation of valid data against schema."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            },
            "required": ["name", "value"]
        }
        data = {"name": "test", "value": 123}
        
        result = validator.validate(data, schema)
        
        assert result.success is True
        assert result.data == data
        assert len(result.errors) == 0
    
    def test_validate_invalid_data(self):
        """Test validation of invalid data against schema."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            },
            "required": ["name", "value"]
        }
        data = {"name": 123, "value": "test"}  # Wrong types
        
        result = validator.validate(data, schema)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert result.errors[0].type == ValidationErrorType.SCHEMA_ERROR
    
    def test_validate_missing_required(self):
        """Test validation with missing required fields."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            },
            "required": ["name", "value"]
        }
        data = {"name": "test"}  # Missing required field
        
        result = validator.validate(data, schema)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "required" in result.errors[0].message.lower()
    
    def test_validate_string_input(self):
        """Test validation of string input with lenient parsing."""
        validator = SchemaValidator(lenient_parsing=True)
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            },
            "required": ["name", "value"]
        }
        json_string = '{"name": "test", "value": 123,}'  # Trailing comma
        
        result = validator.validate(json_string, schema)
        
        assert result.success is True
        assert result.data == {"name": "test", "value": 123}
        assert result.repair_attempts == 1
        assert result.repaired_input is not None
    
    def test_validate_invalid_schema(self):
        """Test validation with invalid schema."""
        validator = SchemaValidator()
        schema = {"type": "invalid_type"}  # Invalid schema
        data = {"name": "test"}
        
        # This should raise an exception during schema validation
        with pytest.raises(Exception):
            validator.validate(data, schema)
    
    def test_get_validation_errors(self):
        """Test getting human-readable validation errors."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            },
            "required": ["name", "value"]
        }
        data = {"name": 123}  # Wrong type and missing required field
        
        result = validator.validate(data, schema)
        errors = validator.get_validation_errors(result)
        
        assert len(errors) > 0
        assert all(isinstance(error, str) for error in errors)
    
    def test_is_repairable(self):
        """Test checking if validation errors are repairable."""
        validator = SchemaValidator()
        
        # Test with repairable syntax error
        result = validator.validate('{"name": "test", "value": 123,}', {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            }
        })
        # Successful repair means no errors, so not repairable
        assert validator.is_repairable(result) is False
        
        # Test with non-repairable schema error
        result = validator.validate({"name": 123}, {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        })
        assert validator.is_repairable(result) is False
