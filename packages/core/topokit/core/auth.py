"""Authentication and authorization framework for TopoKit with JWT integration and RBAC."""

import asyncio
import hashlib
import secrets
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging

try:
    import jwt
    from passlib.context import CryptContext
    from passlib.hash import bcrypt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

from .config import SecurityConfig
from .logging import get_logger


class UserRole(str, Enum):
    """User roles."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    VIEWER = "viewer"
    AUDITOR = "auditor"


class Permission(str, Enum):
    """System permissions."""
    # Topology management
    CREATE_TOPOLOGY = "create_topology"
    READ_TOPOLOGY = "read_topology"
    UPDATE_TOPOLOGY = "update_topology"
    DELETE_TOPOLOGY = "delete_topology"
    EXECUTE_TOPOLOGY = "execute_topology"
    
    # User management
    CREATE_USER = "create_user"
    READ_USER = "read_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # System administration
    MANAGE_SYSTEM = "manage_system"
    VIEW_LOGS = "view_logs"
    MANAGE_CONFIG = "manage_config"
    
    # Audit and compliance
    VIEW_AUDIT = "view_audit"
    EXPORT_DATA = "export_data"


class TokenType(str, Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


@dataclass
class User:
    """User model."""
    id: str
    username: str
    email: str
    roles: List[UserRole] = field(default_factory=list)
    permissions: List[Permission] = field(default_factory=list)
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenPayload:
    """JWT token payload."""
    user_id: str
    username: str
    roles: List[str]
    permissions: List[str]
    token_type: TokenType
    exp: datetime
    iat: datetime
    jti: str  # JWT ID for token revocation
    session_id: Optional[str] = None


@dataclass
class AuthResult:
    """Authentication result."""
    success: bool
    user: Optional[User] = None
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    message: str = ""
    expires_at: Optional[datetime] = None


class RoleBasedAccessControl:
    """Role-based access control system."""
    
    def __init__(self):
        """Initialize RBAC system."""
        self.logger = get_logger(__name__)
        
        # Define role-permission mappings
        self.role_permissions = {
            UserRole.ADMIN: [
                Permission.CREATE_TOPOLOGY,
                Permission.READ_TOPOLOGY,
                Permission.UPDATE_TOPOLOGY,
                Permission.DELETE_TOPOLOGY,
                Permission.EXECUTE_TOPOLOGY,
                Permission.CREATE_USER,
                Permission.READ_USER,
                Permission.UPDATE_USER,
                Permission.DELETE_USER,
                Permission.MANAGE_SYSTEM,
                Permission.VIEW_LOGS,
                Permission.MANAGE_CONFIG,
                Permission.VIEW_AUDIT,
                Permission.EXPORT_DATA
            ],
            UserRole.DEVELOPER: [
                Permission.CREATE_TOPOLOGY,
                Permission.READ_TOPOLOGY,
                Permission.UPDATE_TOPOLOGY,
                Permission.EXECUTE_TOPOLOGY,
                Permission.VIEW_LOGS,
                Permission.VIEW_AUDIT
            ],
            UserRole.OPERATOR: [
                Permission.READ_TOPOLOGY,
                Permission.EXECUTE_TOPOLOGY,
                Permission.VIEW_LOGS
            ],
            UserRole.VIEWER: [
                Permission.READ_TOPOLOGY
            ],
            UserRole.AUDITOR: [
                Permission.READ_TOPOLOGY,
                Permission.VIEW_AUDIT,
                Permission.EXPORT_DATA
            ]
        }
    
    def get_permissions_for_role(self, role: UserRole) -> List[Permission]:
        """Get permissions for a role.
        
        Args:
            role: User role
            
        Returns:
            List of permissions
        """
        return self.role_permissions.get(role, [])
    
    def get_permissions_for_roles(self, roles: List[UserRole]) -> Set[Permission]:
        """Get all permissions for multiple roles.
        
        Args:
            roles: List of user roles
            
        Returns:
            Set of permissions
        """
        permissions = set()
        for role in roles:
            permissions.update(self.get_permissions_for_role(role))
        return permissions
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission.
        
        Args:
            user: User object
            permission: Permission to check
            
        Returns:
            True if user has permission
        """
        if not user.is_active:
            return False
        
        # Check direct permissions
        if permission in user.permissions:
            return True
        
        # Check role-based permissions
        user_permissions = self.get_permissions_for_roles(user.roles)
        return permission in user_permissions
    
    def has_any_permission(self, user: User, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions.
        
        Args:
            user: User object
            permissions: List of permissions to check
            
        Returns:
            True if user has any permission
        """
        return any(self.has_permission(user, perm) for perm in permissions)
    
    def has_all_permissions(self, user: User, permissions: List[Permission]) -> bool:
        """Check if user has all specified permissions.
        
        Args:
            user: User object
            permissions: List of permissions to check
            
        Returns:
            True if user has all permissions
        """
        return all(self.has_permission(user, perm) for perm in permissions)


class AuthenticationManager:
    """Authentication manager with JWT support."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize authentication manager.
        
        Args:
            config: Security configuration
        """
        if not JWT_AVAILABLE:
            raise ImportError("JWT dependencies not available. Install PyJWT and passlib.")
        
        self.config = config
        self.logger = get_logger(__name__)
        
        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # RBAC system
        self.rbac = RoleBasedAccessControl()
        
        # Token revocation list (in production, use Redis or database)
        self._revoked_tokens: Set[str] = set()
        self._revocation_lock = asyncio.Lock()
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, user: User, session_id: Optional[str] = None) -> str:
        """Create JWT access token.
        
        Args:
            user: User object
            session_id: Session identifier
            
        Returns:
            JWT access token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.config.jwt_expire_minutes)
        
        # Get user permissions
        permissions = self.rbac.get_permissions_for_roles(user.roles)
        permissions.update(user.permissions)
        
        payload = TokenPayload(
            user_id=user.id,
            username=user.username,
            roles=[role.value for role in user.roles],
            permissions=[perm.value for perm in permissions],
            token_type=TokenType.ACCESS,
            exp=expire,
            iat=now,
            jti=secrets.token_urlsafe(32),
            session_id=session_id
        )
        
        return jwt.encode(
            payload.__dict__,
            self.config.secret_key,
            algorithm=self.config.jwt_algorithm
        )
    
    def create_refresh_token(self, user: User, session_id: Optional[str] = None) -> str:
        """Create JWT refresh token.
        
        Args:
            user: User object
            session_id: Session identifier
            
        Returns:
            JWT refresh token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.config.jwt_refresh_expire_days)
        
        payload = TokenPayload(
            user_id=user.id,
            username=user.username,
            roles=[role.value for role in user.roles],
            permissions=[],  # Refresh tokens don't need permissions
            token_type=TokenType.REFRESH,
            exp=expire,
            iat=now,
            jti=secrets.token_urlsafe(32),
            session_id=session_id
        )
        
        return jwt.encode(
            payload.__dict__,
            self.config.secret_key,
            algorithm=self.config.jwt_algorithm
        )
    
    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """Verify and decode JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Token payload or None if invalid
        """
        try:
            # Check if token is revoked
            if token in self._revoked_tokens:
                return None
            
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.jwt_algorithm]
            )
            
            # Convert to TokenPayload
            return TokenPayload(
                user_id=payload["user_id"],
                username=payload["username"],
                roles=payload["roles"],
                permissions=payload["permissions"],
                token_type=TokenType(payload["token_type"]),
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                jti=payload["jti"],
                session_id=payload.get("session_id")
            )
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Token verification error: {e}")
            return None
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke a token.
        
        Args:
            token: JWT token to revoke
            
        Returns:
            True if token was revoked
        """
        async with self._revocation_lock:
            self._revoked_tokens.add(token)
            return True
    
    async def is_token_revoked(self, token: str) -> bool:
        """Check if token is revoked.
        
        Args:
            token: JWT token
            
        Returns:
            True if token is revoked
        """
        async with self._revocation_lock:
            return token in self._revoked_tokens
    
    def create_api_key(self, user: User, name: str) -> str:
        """Create API key for user.
        
        Args:
            user: User object
            name: API key name
            
        Returns:
            API key
        """
        # Generate API key
        api_key = f"tk_{secrets.token_urlsafe(32)}"
        
        # In production, store API key in database with metadata
        self.logger.info(f"Created API key for user {user.username}: {name}")
        
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[User]:
        """Verify API key and return user.
        
        Args:
            api_key: API key
            
        Returns:
            User object or None if invalid
        """
        # In production, look up API key in database
        # For now, return None (placeholder)
        return None


class AuthorizationManager:
    """Authorization manager with permission checking."""
    
    def __init__(self, auth_manager: AuthenticationManager):
        """Initialize authorization manager.
        
        Args:
            auth_manager: Authentication manager instance
        """
        self.auth_manager = auth_manager
        self.logger = get_logger(__name__)
    
    async def check_permission(self, 
                             token: str, 
                             permission: Permission,
                             resource_id: Optional[str] = None) -> bool:
        """Check if token has permission.
        
        Args:
            token: JWT token
            permission: Permission to check
            resource_id: Optional resource ID for context
            
        Returns:
            True if permission is granted
        """
        # Verify token
        payload = self.auth_manager.verify_token(token)
        if not payload:
            return False
        
        # Check if token is revoked
        if await self.auth_manager.is_token_revoked(token):
            return False
        
        # Get user (in production, fetch from database)
        user = await self._get_user_by_id(payload.user_id)
        if not user or not user.is_active:
            return False
        
        # Check permission
        has_permission = self.auth_manager.rbac.has_permission(user, permission)
        
        if has_permission:
            self.logger.info(f"Permission granted: {permission.value} for user {user.username}")
        else:
            self.logger.warning(f"Permission denied: {permission.value} for user {user.username}")
        
        return has_permission
    
    async def check_permissions(self, 
                              token: str, 
                              permissions: List[Permission],
                              require_all: bool = True) -> bool:
        """Check if token has permissions.
        
        Args:
            token: JWT token
            permissions: List of permissions to check
            require_all: If True, require all permissions; if False, require any
            
        Returns:
            True if permissions are granted
        """
        # Verify token
        payload = self.auth_manager.verify_token(token)
        if not payload:
            return False
        
        # Get user
        user = await self._get_user_by_id(payload.user_id)
        if not user or not user.is_active:
            return False
        
        # Check permissions
        if require_all:
            return self.auth_manager.rbac.has_all_permissions(user, permissions)
        else:
            return self.auth_manager.rbac.has_any_permission(user, permissions)
    
    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID (placeholder - in production, fetch from database).
        
        Args:
            user_id: User ID
            
        Returns:
            User object or None
        """
        # This is a placeholder implementation
        # In production, this would query the database
        return None


class AuditLogger:
    """Audit logger for security events."""
    
    def __init__(self):
        """Initialize audit logger."""
        self.logger = get_logger(__name__)
    
    def log_auth_event(self, 
                      event_type: str,
                      user_id: Optional[str],
                      username: Optional[str],
                      success: bool,
                      details: Optional[Dict[str, Any]] = None,
                      ip_address: Optional[str] = None,
                      user_agent: Optional[str] = None):
        """Log authentication event.
        
        Args:
            event_type: Type of event (login, logout, token_refresh, etc.)
            user_id: User ID
            username: Username
            success: Whether event was successful
            details: Additional details
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.logger.info(
            f"Auth event: {event_type}",
            extra={
                "audit_event": event_type,
                "user_id": user_id,
                "username": username,
                "success": success,
                "details": details or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def log_permission_check(self,
                           user_id: str,
                           permission: str,
                           resource_id: Optional[str],
                           granted: bool,
                           ip_address: Optional[str] = None):
        """Log permission check.
        
        Args:
            user_id: User ID
            permission: Permission checked
            resource_id: Resource ID
            granted: Whether permission was granted
            ip_address: Client IP address
        """
        self.logger.info(
            f"Permission check: {permission}",
            extra={
                "audit_event": "permission_check",
                "user_id": user_id,
                "permission": permission,
                "resource_id": resource_id,
                "granted": granted,
                "ip_address": ip_address,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


# Global instances
_auth_manager: Optional[AuthenticationManager] = None
_authz_manager: Optional[AuthorizationManager] = None
_audit_logger: Optional[AuditLogger] = None


def get_auth_manager(config: Optional[SecurityConfig] = None) -> AuthenticationManager:
    """Get authentication manager instance.
    
    Args:
        config: Security configuration
        
    Returns:
        AuthenticationManager instance
    """
    global _auth_manager
    
    if _auth_manager is None:
        if config is None:
            from .config import get_config
            config = get_config().security
        
        _auth_manager = AuthenticationManager(config)
    
    return _auth_manager


def get_authz_manager() -> AuthorizationManager:
    """Get authorization manager instance.
    
    Returns:
        AuthorizationManager instance
    """
    global _authz_manager
    
    if _authz_manager is None:
        _authz_manager = AuthorizationManager(get_auth_manager())
    
    return _authz_manager


def get_audit_logger() -> AuditLogger:
    """Get audit logger instance.
    
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    
    return _audit_logger
