"""Type definitions and enums for the interior design agent."""
from enum import Enum


class RoomType(str, Enum):
    """Types of rooms."""
    BEDROOM = "bedroom"
    LIVING_ROOM = "living_room"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    OFFICE = "office"
    DINING_ROOM = "dining_room"
    OTHER = "other"


class MessageRole(str, Enum):
    """Role of message sender."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class PreferenceType(str, Enum):
    """Types of user preferences."""
    STYLE = "style"
    COLOR = "color"
    WARMTH = "warmth"
    COMPLEXITY = "complexity"
    LIGHTING = "lighting"
    FURNITURE = "furniture"
    MATERIAL = "material"
    OTHER = "other"
