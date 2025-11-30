"""
Authentication service for user management and authentication
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ..models.user import User, UserRole, UserCreate, UserResponse
from ..core.security import (
    get_password_hash,
    verify_password,
    create_token_pair,
    decode_token,
    validate_password_strength,
    TokenPair
)
from ..core.config import settings


class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(
        self,
        user_data: UserCreate,
        role: UserRole = UserRole.ANALYST
    ) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data
            role: User role (default: analyst)

        Returns:
            Created user object

        Raises:
            ValueError: If email already exists or password is weak
        """
        # Check if email already exists
        existing = await self.get_user_by_email(user_data.email)
        if existing:
            raise ValueError("Email already registered")

        # Validate password strength
        is_valid, error_msg = validate_password_strength(user_data.password)
        if not is_valid:
            raise ValueError(error_msg)

        # Create user
        user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            name=user_data.name,
            organization=user_data.organization,
            role=role
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return None

        result = await self.db.execute(
            select(User).where(User.id == uid)
        )
        return result.scalar_one_or_none()

    async def authenticate(
        self,
        email: str,
        password: str
    ) -> Optional[tuple[User, TokenPair]]:
        """
        Authenticate user and return tokens.

        Args:
            email: User email
            password: User password

        Returns:
            Tuple of (user, token_pair) if successful, None otherwise
        """
        user = await self.get_user_by_email(email)

        if not user:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        await self.db.flush()

        # Create tokens
        token_pair = create_token_pair(str(user.id), user.role.value)

        return user, token_pair

    async def refresh_tokens(self, refresh_token: str) -> Optional[tuple[User, TokenPair]]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: The refresh token

        Returns:
            Tuple of (user, new_token_pair) if successful, None otherwise
        """
        payload = decode_token(refresh_token)

        if not payload:
            return None

        if payload.type != "refresh":
            return None

        user = await self.get_user_by_id(payload.sub)

        if not user or not user.is_active:
            return None

        # Create new tokens
        token_pair = create_token_pair(str(user.id), user.role.value)

        return user, token_pair

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            True if successful

        Raises:
            ValueError: If current password is wrong or new password is weak
        """
        user = await self.get_user_by_id(user_id)

        if not user:
            raise ValueError("User not found")

        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        # Validate new password
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)

        # Update password
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        await self.db.flush()

        return True

    async def update_user(
        self,
        user_id: str,
        name: Optional[str] = None,
        organization: Optional[str] = None
    ) -> User:
        """Update user profile."""
        user = await self.get_user_by_id(user_id)

        if not user:
            raise ValueError("User not found")

        if name is not None:
            user.name = name
        if organization is not None:
            user.organization = organization

        user.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(user)

        return user

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        user = await self.get_user_by_id(user_id)

        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.utcnow()
        await self.db.flush()

        return True

    @staticmethod
    def user_to_response(user: User) -> UserResponse:
        """Convert User model to UserResponse schema."""
        return UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            organization=user.organization,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
