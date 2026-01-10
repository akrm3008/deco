"""Pydantic models for data structures."""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from backend.models.types import MessageRole, PreferenceType, RoomType


class User(BaseModel):
    """User model with authentication."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    username: Optional[str] = None
    password_hash: Optional[str] = None  # Never expose this in responses
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Room(BaseModel):
    """Room model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    name: str
    room_type: RoomType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DesignVersion(BaseModel):
    """Design version model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    room_id: str
    version_number: int
    description: str
    selected: bool = False
    rejected: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    parent_version_id: Optional[str] = None


class DesignImage(BaseModel):
    """Design image model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    design_version_id: str
    image_url: str
    prompt: str
    selected: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserPreference(BaseModel):
    """User preference model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    preference_type: PreferenceType
    preference_value: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.3)
    source_room_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationMessage(BaseModel):
    """Conversation message model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    room_id: Optional[str] = None
    session_id: str
    message: str
    role: MessageRole
    created_at: datetime = Field(default_factory=datetime.utcnow)


# API Request/Response models
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    user_id: str
    room_id: Optional[str] = None
    session_id: str


class ImageData(BaseModel):
    """Image data for chat response."""
    id: str
    url: str


class ChatResponse(BaseModel):
    """Chat response model."""
    message: str
    room_id: Optional[str] = None
    design_version_id: Optional[str] = None
    images: list[ImageData] = Field(default_factory=list)


class RoomListResponse(BaseModel):
    """Room list response."""
    rooms: list[Room]


class DesignVersionListResponse(BaseModel):
    """Design version list response."""
    versions: list[DesignVersion]
    images: dict[str, list[DesignImage]]  # version_id -> list of images


class PreferenceListResponse(BaseModel):
    """Preference list response."""
    preferences: list[UserPreference]


# Authentication models
class UserResponse(BaseModel):
    """User response (without password)."""
    id: str
    username: str
    created_at: datetime


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """Registration request."""
    username: str
    password: str
