from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from datetime import datetime
from typing import Optional


class CamelModel(BaseModel):
    """Base model that accepts and produces camelCase field names."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ---------- Auth ----------

class LoginRequest(CamelModel):
    email: str
    password: str


class LoginResponse(CamelModel):
    token: str
    user: "UserResponse"


# ---------- User ----------

class UserBase(CamelModel):
    name: str
    email: str
    role: str = "RESIDENT"
    apartment: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(CamelModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    apartment: Optional[str] = None


class UserResponse(CamelModel):
    id: int
    name: str
    email: str
    role: str
    apartment: Optional[str]
    phone: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


LoginResponse.model_rebuild()


# ---------- Notification ----------

class NotificationResponse(CamelModel):
    id: int
    user_id: int
    message: str
    type: str
    read: bool
    created_at: Optional[datetime]
