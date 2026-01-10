"""JSON/SQLite storage for structured data that doesn't need vector search."""
import json
from pathlib import Path
from typing import Dict, List, Optional

from backend.config import config
from backend.models.schemas import (
    DesignImage,
    DesignVersion,
    Room,
    User,
    UserPreference,
)


class DataStorage:
    """Simple JSON-based storage for structured data."""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or config.DATA_STORAGE_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize storage files
        self.users_file = self.storage_path / "users.json"
        self.rooms_file = self.storage_path / "rooms.json"
        self.design_versions_file = self.storage_path / "design_versions.json"
        self.design_images_file = self.storage_path / "design_images.json"
        self.preferences_file = self.storage_path / "preferences.json"

        # Initialize empty files if they don't exist
        for file in [
            self.users_file,
            self.rooms_file,
            self.design_versions_file,
            self.design_images_file,
            self.preferences_file,
        ]:
            if not file.exists():
                file.write_text("{}")

    def _load_json(self, file_path: Path) -> Dict:
        """Load JSON from file."""
        try:
            return json.loads(file_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_json(self, file_path: Path, data: Dict) -> None:
        """Save JSON to file."""
        file_path.write_text(json.dumps(data, indent=2, default=str))

    # User operations
    def create_user(self, user: User) -> User:
        """Create a new user."""
        users = self._load_json(self.users_file)
        users[user.id] = user.model_dump()
        self._save_json(self.users_file, users)
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        users = self._load_json(self.users_file)
        user_data = users.get(user_id)
        return User(**user_data) if user_data else None

    # Room operations
    def create_room(self, room: Room) -> Room:
        """Create a new room."""
        rooms = self._load_json(self.rooms_file)
        rooms[room.id] = room.model_dump()
        self._save_json(self.rooms_file, rooms)
        return room

    def get_room(self, room_id: str) -> Optional[Room]:
        """Get room by ID."""
        rooms = self._load_json(self.rooms_file)
        room_data = rooms.get(room_id)
        return Room(**room_data) if room_data else None

    def get_user_rooms(self, user_id: str) -> List[Room]:
        """Get all rooms for a user."""
        rooms = self._load_json(self.rooms_file)
        user_rooms = [
            Room(**room_data)
            for room_data in rooms.values()
            if room_data.get("user_id") == user_id
        ]
        return sorted(user_rooms, key=lambda r: r.created_at, reverse=True)

    def update_room(self, room: Room) -> Room:
        """Update an existing room."""
        rooms = self._load_json(self.rooms_file)
        if room.id in rooms:
            from datetime import datetime
            room.updated_at = datetime.utcnow()
            rooms[room.id] = room.model_dump()
            self._save_json(self.rooms_file, rooms)
        return room

    # Design version operations
    def create_design_version(self, version: DesignVersion) -> DesignVersion:
        """Create a new design version."""
        versions = self._load_json(self.design_versions_file)
        versions[version.id] = version.model_dump()
        self._save_json(self.design_versions_file, versions)
        return version

    def get_design_version(self, version_id: str) -> Optional[DesignVersion]:
        """Get design version by ID."""
        versions = self._load_json(self.design_versions_file)
        version_data = versions.get(version_id)
        return DesignVersion(**version_data) if version_data else None

    def get_room_design_versions(self, room_id: str) -> List[DesignVersion]:
        """Get all design versions for a room."""
        versions = self._load_json(self.design_versions_file)
        room_versions = [
            DesignVersion(**version_data)
            for version_data in versions.values()
            if version_data.get("room_id") == room_id
        ]
        return sorted(room_versions, key=lambda v: v.version_number)

    def get_latest_design_version(self, room_id: str) -> Optional[DesignVersion]:
        """Get the latest design version for a room."""
        versions = self.get_room_design_versions(room_id)
        return versions[-1] if versions else None

    def update_design_version(self, version: DesignVersion) -> DesignVersion:
        """Update an existing design version."""
        versions = self._load_json(self.design_versions_file)
        if version.id not in versions:
            raise ValueError(f"Design version {version.id} not found")
        versions[version.id] = version.model_dump()
        self._save_json(self.design_versions_file, versions)
        return version

    # Design image operations
    def create_design_image(self, image: DesignImage) -> DesignImage:
        """Create a new design image."""
        images = self._load_json(self.design_images_file)
        images[image.id] = image.model_dump()
        self._save_json(self.design_images_file, images)
        return image

    def get_design_images(self, version_id: str) -> List[DesignImage]:
        """Get all images for a design version."""
        images = self._load_json(self.design_images_file)
        version_images = [
            DesignImage(**image_data)
            for image_data in images.values()
            if image_data.get("design_version_id") == version_id
        ]
        return sorted(version_images, key=lambda i: i.created_at)

    # Preference operations
    def create_preference(self, preference: UserPreference) -> UserPreference:
        """Create a new user preference."""
        preferences = self._load_json(self.preferences_file)
        preferences[preference.id] = preference.model_dump()
        self._save_json(self.preferences_file, preferences)
        return preference

    def update_preference(self, preference: UserPreference) -> UserPreference:
        """Update an existing preference."""
        preferences = self._load_json(self.preferences_file)
        if preference.id in preferences:
            from datetime import datetime
            preference.updated_at = datetime.utcnow()
            preferences[preference.id] = preference.model_dump()
            self._save_json(self.preferences_file, preferences)
        return preference

    def get_user_preferences(
        self, user_id: str, confidence_threshold: float = 0.0
    ) -> List[UserPreference]:
        """Get all preferences for a user above confidence threshold."""
        preferences = self._load_json(self.preferences_file)
        user_prefs = [
            UserPreference(**pref_data)
            for pref_data in preferences.values()
            if pref_data.get("user_id") == user_id
            and pref_data.get("confidence", 0.0) >= confidence_threshold
        ]
        return sorted(user_prefs, key=lambda p: p.confidence, reverse=True)

    def find_preference(
        self, user_id: str, preference_type: str, preference_value: str
    ) -> Optional[UserPreference]:
        """Find a specific preference."""
        preferences = self._load_json(self.preferences_file)
        for pref_data in preferences.values():
            if (
                pref_data.get("user_id") == user_id
                and pref_data.get("preference_type") == preference_type
                and pref_data.get("preference_value") == preference_value
            ):
                return UserPreference(**pref_data)
        return None


# Global storage instance
storage = DataStorage()
