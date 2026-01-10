"""Main design agent using Claude API and memory system."""
import re
from typing import List, Optional, Tuple

from llama_index.llms.anthropic import Anthropic

from backend.agent.image_generator import image_generator
from backend.agent.prompts import DESIGN_GENERATION_PROMPT, SYSTEM_PROMPT
from backend.config import config
from backend.memory.manager import memory_manager
from backend.memory.storage import storage
from backend.models.schemas import (
    DesignImage,
    DesignVersion,
    Room,
)
from backend.models.types import MessageRole, RoomType


class DesignAgent:
    """Main interior design agent."""

    def __init__(self):
        self.memory = memory_manager
        self.storage = storage
        self.image_gen = image_generator

        # Initialize Claude LLM
        self.llm = Anthropic(
            api_key=config.ANTHROPIC_API_KEY,
            model=config.CLAUDE_MODEL,
            max_tokens=config.CLAUDE_MAX_TOKENS,
        )

    async def chat(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        room_id: Optional[str] = None,
    ) -> Tuple[str, Optional[str], List[str]]:
        """
        Process user message and generate response.

        Args:
            user_message: User's message
            user_id: User ID
            session_id: Session ID
            room_id: Optional current room ID

        Returns:
            Tuple of (response_text, room_id, image_urls)
        """
        # Store user message
        self.memory.store_conversation(
            user_id=user_id,
            session_id=session_id,
            message=user_message,
            role=MessageRole.USER,
            room_id=room_id,
        )

        # Detect if user is referencing an existing room
        room_id, room_name = await self._detect_room_reference(
            user_message, user_id, room_id
        )

        # Get context for LLM
        context = self.memory.format_context_for_llm(user_message, user_id, room_id)

        # Generate response
        prompt = DESIGN_GENERATION_PROMPT.format(
            user_message=user_message, context=context or "No previous context."
        )

        response = await self.llm.acomplete(prompt, formatted=False)
        response_text = str(response)

        # Store agent response
        self.memory.store_conversation(
            user_id=user_id,
            session_id=session_id,
            message=response_text,
            role=MessageRole.AGENT,
            room_id=room_id,
        )

        # Determine if this is a design generation response
        images = []
        if self._is_design_response(response_text):
            # Create/update room if needed
            if not room_id:
                room_id = await self._create_room_from_context(
                    user_message, user_id, session_id
                )

            # Generate design version and images
            if room_id:
                images = await self._generate_design_version(
                    room_id, response_text, user_id
                )

        return response_text, room_id, images

    async def _detect_room_reference(
        self, user_message: str, user_id: str, current_room_id: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Detect if user is referencing an existing room."""
        if current_room_id:
            return current_room_id, None

        # Get user's rooms
        rooms = self.storage.get_user_rooms(user_id)
        if not rooms:
            return None, None

        # Simple keyword matching for room references
        message_lower = user_message.lower()
        for room in rooms:
            if room.name.lower() in message_lower:
                return room.id, room.name

            # Check room type
            if room.room_type.value in message_lower:
                return room.id, room.name

        return None, None

    async def _create_room_from_context(
        self, user_message: str, user_id: str, session_id: str
    ) -> Optional[str]:
        """Create a new room based on conversation context."""
        # Extract room type from message
        message_lower = user_message.lower()

        room_type = RoomType.OTHER
        room_name = "New Room"

        if "bedroom" in message_lower:
            room_type = RoomType.BEDROOM
            room_name = "Bedroom"
        elif "living room" in message_lower:
            room_type = RoomType.LIVING_ROOM
            room_name = "Living Room"
        elif "kitchen" in message_lower:
            room_type = RoomType.KITCHEN
            room_name = "Kitchen"
        elif "bathroom" in message_lower:
            room_type = RoomType.BATHROOM
            room_name = "Bathroom"
        elif "office" in message_lower:
            room_type = RoomType.OFFICE
            room_name = "Home Office"
        elif "dining" in message_lower:
            room_type = RoomType.DINING_ROOM
            room_name = "Dining Room"

        # Create room
        room = Room(user_id=user_id, name=room_name, room_type=room_type)
        room = self.storage.create_room(room)

        return room.id

    def _is_design_response(self, response: str) -> bool:
        """Check if response contains a design description."""
        # Simple heuristic: check for design-related keywords
        design_indicators = [
            "furniture",
            "color",
            "wall",
            "floor",
            "lighting",
            "layout",
            "design",
            "style",
        ]
        response_lower = response.lower()
        return (
            sum(1 for indicator in design_indicators if indicator in response_lower)
            >= 3
        )

    async def _generate_design_version(
        self, room_id: str, design_description: str, user_id: str
    ) -> List[str]:
        """Generate a design version with images."""
        # Get existing versions
        versions = self.storage.get_room_design_versions(room_id)
        version_number = len(versions) + 1

        # Get parent version (latest)
        parent_id = versions[-1].id if versions else None

        # Create design version
        design_version = DesignVersion(
            room_id=room_id,
            version_number=version_number,
            description=design_description[:500],  # Truncate if too long
            parent_version_id=parent_id,
        )
        design_version = self.storage.create_design_version(design_version)

        # Generate images (3-5 variations)
        num_images = 3
        image_urls = []

        for i in range(num_images):
            # Create variation prompt
            variation_prompt = f"{design_description[:200]} - variation {i+1}"

            # Generate image
            image_url = await self.image_gen.generate(variation_prompt)

            # Store image
            design_image = DesignImage(
                design_version_id=design_version.id,
                image_url=image_url,
                prompt=variation_prompt,
            )
            self.storage.create_design_image(design_image)
            image_urls.append(image_url)

        return image_urls

    async def select_design(
        self, user_id: str, design_version_id: str, image_id: Optional[str] = None
    ):
        """Mark a design as selected and learn preferences."""
        # Get design version
        version = self.storage.get_design_version(design_version_id)
        if not version:
            return

        # Mark as selected
        version.selected = True
        self.storage.create_design_version(version)  # Update

        # Mark image as selected if specified
        if image_id:
            images = self.storage.get_design_images(design_version_id)
            for img in images:
                if img.id == image_id:
                    img.selected = True
                    self.storage.create_design_image(img)

        # Learn preferences from selection
        self.memory.learn_from_design_selection(
            user_id, version.description, version.room_id
        )


# Global agent instance
design_agent = DesignAgent()
