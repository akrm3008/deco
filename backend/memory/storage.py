"""Supabase PostgreSQL storage for structured data."""
from datetime import datetime
from typing import List, Optional

from supabase import create_client
from postgrest.exceptions import APIError

from backend.config import config
from backend.models.schemas import (
    DesignImage,
    DesignVersion,
    Room,
    User,
    UserPreference,
)


class SupabaseDataStorage:
    """Supabase PostgreSQL-based storage for structured data."""

    def __init__(self):
        """Initialize Supabase client."""
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY are required for Supabase storage"
            )

        self.client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    def _serialize_model(self, model) -> dict:
        """Convert Pydantic model to dict suitable for Supabase."""
        data = model.model_dump()
        # Convert datetime objects to ISO format strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    # ==================== User operations ====================

    def create_user(self, user: User) -> User:
        """Create a new user."""
        try:
            data = self._serialize_model(user)
            result = self.client.table('users').insert(data).execute()
            return User(**result.data[0])
        except APIError as e:
            print(f"Error creating user: {e}")
            raise

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            result = (
                self.client.table('users')
                .select('*')
                .eq('id', user_id)
                .execute()
            )
            return User(**result.data[0]) if result.data else None
        except APIError as e:
            print(f"Error getting user: {e}")
            return None

    # ==================== Room operations ====================

    def create_room(self, room: Room) -> Room:
        """Create a new room."""
        try:
            data = self._serialize_model(room)
            result = self.client.table('rooms').insert(data).execute()
            return Room(**result.data[0])
        except APIError as e:
            print(f"Error creating room: {e}")
            raise

    def get_room(self, room_id: str) -> Optional[Room]:
        """Get room by ID."""
        try:
            result = (
                self.client.table('rooms')
                .select('*')
                .eq('id', room_id)
                .execute()
            )
            return Room(**result.data[0]) if result.data else None
        except APIError as e:
            print(f"Error getting room: {e}")
            return None

    def get_user_rooms(self, user_id: str) -> List[Room]:
        """Get all rooms for a user, sorted by created_at DESC."""
        try:
            result = (
                self.client.table('rooms')
                .select('*')
                .eq('user_id', user_id)
                .order('created_at', desc=True)
                .execute()
            )
            return [Room(**row) for row in result.data]
        except APIError as e:
            print(f"Error getting user rooms: {e}")
            return []

    def update_room(self, room: Room) -> Room:
        """Update an existing room."""
        try:
            # Update the updated_at timestamp
            room.updated_at = datetime.utcnow()
            data = self._serialize_model(room)

            result = (
                self.client.table('rooms')
                .update(data)
                .eq('id', room.id)
                .execute()
            )

            return Room(**result.data[0]) if result.data else room
        except APIError as e:
            print(f"Error updating room: {e}")
            return room

    # ==================== Design version operations ====================

    def create_design_version(self, version: DesignVersion) -> DesignVersion:
        """Create a new design version."""
        try:
            data = self._serialize_model(version)
            result = self.client.table('design_versions').insert(data).execute()
            return DesignVersion(**result.data[0])
        except APIError as e:
            print(f"Error creating design version: {e}")
            raise

    def get_design_version(self, version_id: str) -> Optional[DesignVersion]:
        """Get design version by ID."""
        try:
            result = (
                self.client.table('design_versions')
                .select('*')
                .eq('id', version_id)
                .execute()
            )
            return DesignVersion(**result.data[0]) if result.data else None
        except APIError as e:
            print(f"Error getting design version: {e}")
            return None

    def get_room_design_versions(self, room_id: str) -> List[DesignVersion]:
        """Get all design versions for a room, sorted by version_number ASC."""
        try:
            result = (
                self.client.table('design_versions')
                .select('*')
                .eq('room_id', room_id)
                .order('version_number', desc=False)
                .execute()
            )
            return [DesignVersion(**row) for row in result.data]
        except APIError as e:
            print(f"Error getting room design versions: {e}")
            return []

    def get_latest_design_version(self, room_id: str) -> Optional[DesignVersion]:
        """Get the latest design version for a room."""
        versions = self.get_room_design_versions(room_id)
        return versions[-1] if versions else None

    def update_design_version(self, version: DesignVersion) -> DesignVersion:
        """Update an existing design version."""
        try:
            data = self._serialize_model(version)
            result = (
                self.client.table('design_versions')
                .update(data)
                .eq('id', version.id)
                .execute()
            )

            if not result.data:
                raise ValueError(f"Design version {version.id} not found")

            return DesignVersion(**result.data[0])
        except APIError as e:
            print(f"Error updating design version: {e}")
            raise

    # ==================== Design image operations ====================

    def create_design_image(self, image: DesignImage) -> DesignImage:
        """Create a new design image."""
        try:
            data = self._serialize_model(image)
            result = self.client.table('design_images').insert(data).execute()
            return DesignImage(**result.data[0])
        except APIError as e:
            print(f"Error creating design image: {e}")
            raise

    def get_design_images(self, version_id: str) -> List[DesignImage]:
        """Get all images for a design version, sorted by created_at ASC."""
        try:
            result = (
                self.client.table('design_images')
                .select('*')
                .eq('design_version_id', version_id)
                .order('created_at', desc=False)
                .execute()
            )
            return [DesignImage(**row) for row in result.data]
        except APIError as e:
            print(f"Error getting design images: {e}")
            return []

    def update_design_image(self, image: DesignImage) -> DesignImage:
        """Update an existing design image."""
        try:
            data = self._serialize_model(image)

            result = (
                self.client.table('design_images')
                .update(data)
                .eq('id', image.id)
                .execute()
            )

            return DesignImage(**result.data[0]) if result.data else image
        except APIError as e:
            print(f"Error updating design image: {e}")
            return image

    # ==================== Preference operations ====================

    def create_preference(self, preference: UserPreference) -> UserPreference:
        """Create a new user preference."""
        try:
            data = self._serialize_model(preference)
            result = self.client.table('user_preferences').insert(data).execute()
            return UserPreference(**result.data[0])
        except APIError as e:
            print(f"Error creating preference: {e}")
            raise

    def update_preference(self, preference: UserPreference) -> UserPreference:
        """Update an existing preference."""
        try:
            # Update the updated_at timestamp
            preference.updated_at = datetime.utcnow()
            data = self._serialize_model(preference)

            result = (
                self.client.table('user_preferences')
                .update(data)
                .eq('id', preference.id)
                .execute()
            )

            return UserPreference(**result.data[0]) if result.data else preference
        except APIError as e:
            print(f"Error updating preference: {e}")
            return preference

    def get_user_preferences(
        self, user_id: str, confidence_threshold: float = 0.0
    ) -> List[UserPreference]:
        """Get all preferences for a user above confidence threshold, sorted by confidence DESC."""
        try:
            result = (
                self.client.table('user_preferences')
                .select('*')
                .eq('user_id', user_id)
                .gte('confidence', confidence_threshold)
                .order('confidence', desc=True)
                .execute()
            )
            return [UserPreference(**row) for row in result.data]
        except APIError as e:
            print(f"Error getting user preferences: {e}")
            return []

    def find_preference(
        self, user_id: str, preference_type: str, preference_value: str
    ) -> Optional[UserPreference]:
        """Find a specific preference."""
        try:
            result = (
                self.client.table('user_preferences')
                .select('*')
                .eq('user_id', user_id)
                .eq('preference_type', preference_type)
                .eq('preference_value', preference_value)
                .limit(1)
                .execute()
            )
            return UserPreference(**result.data[0]) if result.data else None
        except APIError as e:
            print(f"Error finding preference: {e}")
            return None


# Global storage instance
storage = SupabaseDataStorage()
