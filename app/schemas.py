"""Pydantic schemas for creating and returning users and calculations."""

from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.calculation_factory import CalculationType
from app.security import MAX_PASSWORD_BYTES


class UserCreate(BaseModel):
    """Data required to register a new user."""

    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Store emails in lowercase so Alice@x.com and alice@x.com can't both register."""
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        """Reject passwords that bcrypt can't hash (it counts bytes, not characters)."""
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
        return value


class UserRead(BaseModel):
    """User details that are safe to return. The password hash is never included."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime


class CalculationCreate(BaseModel):
    """Data a client sends to request a calculation. The result is computed, not supplied."""

    a: float = Field(allow_inf_nan=False)
    b: float = Field(allow_inf_nan=False)
    type: CalculationType

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        """Accept 'add', 'ADD', or ' Add ' for 'Add'. Anything else fails the enum check."""
        if isinstance(value, str):
            return value.strip().capitalize()
        return value

    @model_validator(mode="after")
    def reject_zero_divisor(self):
        """Dividing by zero is rejected up front, before anything reaches the database."""
        if self.type == CalculationType.DIVIDE and self.b == 0:
            raise ValueError("Cannot divide by zero")
        return self


class CalculationRead(BaseModel):
    """A saved calculation as returned to a client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    a: float
    b: float
    type: CalculationType
    result: float
    user_id: Optional[int] = None
    created_at: datetime
    
class UserLogin(BaseModel):
    """Credentials sent to log in. The 'username' may be a username or an email address."""

    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    """Returned after a successful login. It carries only the public user details."""

    message: str
    user: UserRead