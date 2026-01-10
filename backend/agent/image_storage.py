"""Image storage backends for local and cloud storage."""
from abc import ABC, abstractmethod
from pathlib import Path
import uuid
from typing import Tuple

from backend.config import config


class ImageStorage(ABC):
    """Abstract base class for image storage."""

    @abstractmethod
    def save(self, image_bytes: bytes, prompt: str) -> Tuple[str, str]:
        """
        Save image and return (url, filename).

        Args:
            image_bytes: Raw image data
            prompt: Image prompt (for metadata)

        Returns:
            Tuple of (public_url, filename)
        """
        pass


class LocalImageStorage(ImageStorage):
    """Store images on local filesystem."""

    def __init__(self):
        self.images_dir = config.STATIC_IMAGES_PATH
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def save(self, image_bytes: bytes, prompt: str) -> Tuple[str, str]:
        """Save image to local filesystem."""
        # Generate unique filename
        filename = f"{uuid.uuid4()}.png"
        filepath = self.images_dir / filename

        # Save to disk
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        # Return URL path (relative to static mount point)
        url = f"/static/images/{filename}"
        return url, filename


class SupabaseImageStorage(ImageStorage):
    """Store images in Supabase Storage."""

    def __init__(self):
        from supabase import create_client

        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY are required for Supabase storage"
            )

        self.client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        self.bucket = config.SUPABASE_BUCKET

        # Ensure bucket exists (will be created if it doesn't exist)
        try:
            self.client.storage.get_bucket(self.bucket)
        except Exception:
            # Bucket doesn't exist, try to create it
            try:
                self.client.storage.create_bucket(
                    self.bucket,
                    options={"public": True}  # Make images publicly accessible
                )
                print(f"Created Supabase bucket: {self.bucket}")
            except Exception as e:
                print(f"Warning: Could not create bucket {self.bucket}: {e}")

    def save(self, image_bytes: bytes, prompt: str) -> Tuple[str, str]:
        """Save image to Supabase Storage."""
        # Generate unique filename
        filename = f"{uuid.uuid4()}.png"
        file_path = f"designs/{filename}"

        try:
            # Upload to Supabase Storage
            self.client.storage.from_(self.bucket).upload(
                path=file_path,
                file=image_bytes,
                file_options={
                    "content-type": "image/png",
                    "cache-control": "3600",
                    "upsert": "false"
                }
            )

            # Get public URL
            url = self.client.storage.from_(self.bucket).get_public_url(file_path)

            return url, filename

        except Exception as e:
            print(f"Error uploading to Supabase: {e}")
            # Fall back to local storage on error
            print("Falling back to local storage...")
            local_storage = LocalImageStorage()
            return local_storage.save(image_bytes, prompt)


def get_image_storage() -> ImageStorage:
    """Get the configured image storage backend."""
    if config.IMAGE_STORAGE == "supabase":
        try:
            return SupabaseImageStorage()
        except Exception as e:
            print(f"Failed to initialize Supabase storage: {e}")
            print("Falling back to local storage")
            return LocalImageStorage()
    else:
        return LocalImageStorage()


# Global storage instance
image_storage = get_image_storage()
