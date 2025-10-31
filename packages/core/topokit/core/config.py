"""Environment configuration management for TopoKit with validation and type safety."""

import os
import json
import yaml
from typing import Any, Dict, List, Optional, Union, Type, TypeVar
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, field_validator, model_validator
import logging

T = TypeVar('T')


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseModel):
    """Database configuration."""
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="topokit", description="Database name")
    user: str = Field(default="topokit", description="Database user")
    password: str = Field(default="", description="Database password")
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")
    echo: bool = Field(default=False, description="Enable SQL echo")
    
    @property
    def url(self) -> str:
        """Get database URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}?sslmode={self.ssl_mode}"


class RedisConfig(BaseModel):
    """Redis configuration."""
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")
    max_connections: int = Field(default=100, description="Max connections")
    socket_timeout: int = Field(default=5, description="Socket timeout")
    socket_connect_timeout: int = Field(default=5, description="Socket connect timeout")
    
    @property
    def url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class SecurityConfig(BaseModel):
    """Security configuration."""
    secret_key: str = Field(..., description="Secret key for JWT")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expire_minutes: int = Field(default=60, description="JWT expiration in minutes")
    jwt_refresh_expire_days: int = Field(default=7, description="JWT refresh expiration in days")
    password_min_length: int = Field(default=8, description="Minimum password length")
    password_require_special: bool = Field(default=True, description="Require special characters")
    password_require_numbers: bool = Field(default=True, description="Require numbers in password")
    password_require_uppercase: bool = Field(default=True, description="Require uppercase letters")
    password_expire_days: Optional[int] = Field(default=None, description="Password expiration in days")
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    max_failed_attempts: int = Field(default=5, description="Max failed login attempts before lockout")
    account_lockout_minutes: int = Field(default=30, description="Account lockout duration in minutes")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    cors_allow_credentials: bool = Field(default=True, description="CORS allow credentials")
    enable_mfa: bool = Field(default=False, description="Enable multi-factor authentication")
    require_mfa: bool = Field(default=False, description="Require MFA for all users")
    enable_account_lockout: bool = Field(default=True, description="Enable account lockout")
    enable_security_headers: bool = Field(default=True, description="Enable security headers")
    enable_input_sanitization: bool = Field(default=True, description="Enable input sanitization")
    strict_input_validation: bool = Field(default=False, description="Use strict input validation (reject instead of sanitize)")
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v
    
    @field_validator('max_failed_attempts')
    @classmethod
    def validate_max_attempts(cls, v):
        if v < 1:
            raise ValueError('Max failed attempts must be at least 1')
        return v


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = Field(default="openai", description="LLM provider")
    api_key: Optional[str] = Field(default=None, description="API key")
    base_url: Optional[str] = Field(default=None, description="Base URL")
    model: str = Field(default="gpt-3.5-turbo", description="Default model")
    max_tokens: int = Field(default=1000, description="Max tokens")
    temperature: float = Field(default=0.7, description="Temperature")
    timeout: int = Field(default=30, description="Request timeout")
    retry_attempts: int = Field(default=3, description="Retry attempts")
    retry_delay: float = Field(default=1.0, description="Retry delay in seconds")
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        return v


class ObservabilityConfig(BaseModel):
    """Observability configuration."""
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")
    enable_logging: bool = Field(default=True, description="Enable structured logging")
    metrics_port: int = Field(default=8080, description="Metrics port")
    tracing_endpoint: Optional[str] = Field(default=None, description="Tracing endpoint")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    log_format: str = Field(default="json", description="Log format")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    @field_validator('metrics_port')
    @classmethod
    def validate_metrics_port(cls, v):
        if not 1024 <= v <= 65535:
            raise ValueError('Metrics port must be between 1024 and 65535')
        return v


class PerformanceConfig(BaseModel):
    """Performance configuration."""
    max_concurrent_executions: int = Field(default=100, description="Max concurrent executions")
    execution_timeout: int = Field(default=300, description="Execution timeout in seconds")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    cache_max_size: int = Field(default=1000, description="Max cache size")
    parse_timeout: int = Field(default=100, description="Parse timeout in milliseconds")
    validation_timeout: int = Field(default=10, description="Validation timeout in milliseconds")
    context_cleanup_interval: int = Field(default=3600, description="Context cleanup interval in seconds")
    
    @field_validator('max_concurrent_executions')
    @classmethod
    def validate_max_concurrent(cls, v):
        if v <= 0:
            raise ValueError('Max concurrent executions must be positive')
        return v


class ComplianceConfig(BaseModel):
    """Compliance configuration."""
    enable_gdpr: bool = Field(default=True, description="Enable GDPR compliance")
    enable_ccpa: bool = Field(default=True, description="Enable CCPA compliance")
    enable_sox: bool = Field(default=True, description="Enable SOX compliance")
    enable_hipaa: bool = Field(default=True, description="Enable HIPAA compliance")
    audit_endpoint: Optional[str] = Field(default=None, description="External audit endpoint")
    data_retention_days: int = Field(default=2555, description="Data retention period in days (7 years)")
    pii_redaction_enabled: bool = Field(default=True, description="Enable PII redaction")
    audit_log_encryption: bool = Field(default=True, description="Encrypt audit logs")


class TopoKitConfig(BaseModel):
    """Main TopoKit configuration."""
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database config")
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis config")
    security: SecurityConfig = Field(..., description="Security config")
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig, description="Compliance config")
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM config")
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig, description="Observability config")
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig, description="Performance config")
    
    # Custom fields
    custom: Dict[str, Any] = Field(default_factory=dict, description="Custom configuration")
    
    @model_validator(mode='after')
    def validate_environment_specific(self):
        """Validate environment-specific settings."""
        if self.environment == Environment.PRODUCTION:
            if self.debug:
                raise ValueError('Debug mode cannot be enabled in production')
            
            # Production-specific validations
            if not self.security.secret_key:
                raise ValueError('Secret key is required in production')
        
        return self
    
    class Config:
        env_prefix = "TOPOKIT_"
        case_sensitive = False


class ConfigManager:
    """Configuration manager with environment variable support and validation."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self._config: Optional[TopoKitConfig] = None
        self._logger = logging.getLogger(__name__)
    
    def load(self) -> TopoKitConfig:
        """Load configuration from file and environment variables.
        
        Returns:
            TopoKitConfig instance
        """
        if self._config is not None:
            return self._config
        
        # Start with defaults
        config_data = {}
        
        # Load from file if provided
        if self.config_file and Path(self.config_file).exists():
            config_data = self._load_from_file(self.config_file)
        
        # Override with environment variables
        env_data = self._load_from_env()
        config_data = self._merge_configs(config_data, env_data)
        
        # Validate and create config
        try:
            self._config = TopoKitConfig(**config_data)
            self._logger.info(f"Configuration loaded successfully for environment: {self._config.environment}")
            return self._config
        except Exception as e:
            self._logger.error(f"Failed to load configuration: {e}")
            raise
    
    def reload(self) -> TopoKitConfig:
        """Reload configuration."""
        self._config = None
        return self.load()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        if self._config is None:
            self.load()
        
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                else:
                    value = getattr(value, k)
            return value
        except (KeyError, AttributeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key.
        
        Args:
            key: Configuration key (dot notation supported)
            value: Value to set
        """
        if self._config is None:
            self.load()
        
        keys = key.split('.')
        target = self._config
        
        # Navigate to parent of target key
        for k in keys[:-1]:
            if isinstance(target, dict):
                target = target[k]
            else:
                target = getattr(target, k)
        
        # Set the value
        final_key = keys[-1]
        if isinstance(target, dict):
            target[final_key] = value
        else:
            setattr(target, final_key, value)
    
    def save(self, file_path: Optional[str] = None) -> None:
        """Save configuration to file.
        
        Args:
            file_path: File path to save to (uses config_file if not provided)
        """
        if self._config is None:
            self.load()
        
        save_path = file_path or self.config_file
        if not save_path:
            raise ValueError("No file path provided for saving configuration")
        
        # Convert to dict and save
        config_dict = self._config.dict()
        
        if save_path.endswith('.yaml') or save_path.endswith('.yml'):
            with open(save_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
        elif save_path.endswith('.json'):
            with open(save_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        else:
            raise ValueError(f"Unsupported file format: {save_path}")
        
        self._logger.info(f"Configuration saved to {save_path}")
    
    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            if file_path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f) or {}
            elif file_path.suffix == '.json':
                return json.load(f) or {}
            else:
                raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")
    
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_data = {}
        
        # Map environment variables to config structure
        env_mappings = {
            'TOPOKIT_ENVIRONMENT': 'environment',
            'TOPOKIT_DEBUG': 'debug',
            'TOPOKIT_DATABASE_HOST': 'database.host',
            'TOPOKIT_DATABASE_PORT': 'database.port',
            'TOPOKIT_DATABASE_NAME': 'database.name',
            'TOPOKIT_DATABASE_USER': 'database.user',
            'TOPOKIT_DATABASE_PASSWORD': 'database.password',
            'TOPOKIT_REDIS_HOST': 'redis.host',
            'TOPOKIT_REDIS_PORT': 'redis.port',
            'TOPOKIT_REDIS_PASSWORD': 'redis.password',
            'TOPOKIT_SECURITY_SECRET_KEY': 'security.secret_key',
            'TOPOKIT_LLM_PROVIDER': 'llm.provider',
            'TOPOKIT_LLM_API_KEY': 'llm.api_key',
            'TOPOKIT_LLM_MODEL': 'llm.model',
            'TOPOKIT_OBSERVABILITY_LOG_LEVEL': 'observability.log_level',
            'TOPOKIT_OBSERVABILITY_METRICS_PORT': 'observability.metrics_port',
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert value to appropriate type
                converted_value = self._convert_env_value(value)
                self._set_nested_value(env_data, config_key, converted_value)
        
        return env_data
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Numeric values
        if value.isdigit():
            return int(value)
        
        try:
            # Try float
            return float(value)
        except ValueError:
            pass
        
        # String value
        return value
    
    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any) -> None:
        """Set nested dictionary value using dot notation."""
        keys = key.split('.')
        current = data
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config(config_file: Optional[str] = None) -> TopoKitConfig:
    """Get TopoKit configuration.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        TopoKitConfig instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    
    return _config_manager.load()


def reload_config() -> TopoKitConfig:
    """Reload configuration."""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    return _config_manager.reload()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value by key.
    
    Args:
        key: Configuration key (dot notation supported)
        default: Default value if key not found
        
    Returns:
        Configuration value
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    return _config_manager.get(key, default)


def set_config_value(key: str, value: Any) -> None:
    """Set configuration value by key.
    
    Args:
        key: Configuration key (dot notation supported)
        value: Value to set
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    _config_manager.set(key, value)
