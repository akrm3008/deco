"""Main design agent using Claude API and memory system."""
import re
from typing import List, Optional, Tuple

import anthropic

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

        # Initialize Claude client
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    async def chat(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
        room_id: Optional[str] = None,
    ) -> Tuple[str, Optional[str], Optional[str], List[dict]]:
        """
        Process user message and generate response.

        Args:
            user_message: User's message
            user_id: User ID
            session_id: Session ID
            room_id: Optional current room ID

        Returns:
            Tuple of (response_text, room_id, version_id, image_data)
        """
        # Store user message
        self.memory.store_conversation(
            user_id=user_id,
            session_id=session_id,
            message=user_message,
            role=MessageRole.USER,
            room_id=room_id,
        )

        # Detect if user is referencing an existing room or creating a new one
        room_id, room_name, target_room_type = await self._detect_room_reference(
            user_message, user_id, room_id
        )

        # Get context for LLM
        context = self.memory.format_context_for_llm(user_message, user_id, room_id)

        # Generate response
        prompt = DESIGN_GENERATION_PROMPT.format(
            user_message=user_message, context=context or "No previous context."
        )

        # Call Claude API
        message = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.CLAUDE_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text

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
        version_id = None
        is_design = self._is_design_response(response_text)
        print(f"DEBUG: Is design response? {is_design}")
        if is_design:
            # Create room if this is a new room request (target_room_type was identified)
            if not room_id and target_room_type:
                room_id = await self._create_room_from_context(
                    user_id, target_room_type
                )
            print(f"DEBUG: Room ID: {room_id}")

            # Generate design version and images
            if room_id:
                version_id, images = await self._generate_design_version(
                    room_id, response_text, user_id, user_message
                )
                print(f"DEBUG: Generated version {version_id} with {len(images)} images")

        return response_text, room_id, version_id, images

    async def _detect_room_reference(
        self, user_message: str, user_id: str, current_room_id: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Detect if user is referencing an existing room using Claude classifier.

        Returns: (room_id, room_name, target_room_type)
        - If existing room: (room_id, room_name, None)
        - If new room: (None, None, room_type)
        """
        # Don't assume current room is correct - always classify to detect if user wants a different room
        # e.g., "design a bedroom" while in Living Room context should create a new Bedroom

        # Get user's rooms
        rooms = self.storage.get_user_rooms(user_id)

        # If no existing rooms, still classify to identify room type for new users
        if not rooms:
            rooms_list = "(No existing rooms - this will be your first room)"
        else:
            rooms_list = "\n".join([f"- {room.name} ({room.room_type.value})" for room in rooms])

        # Add current room context if available
        current_room_context = ""
        if current_room_id:
            current_room = self.storage.get_room(current_room_id)
            if current_room:
                current_room_context = f"\nCurrent active room: {current_room.name} ({current_room.room_type.value})"

        classifier_prompt = f"""You are a room classification assistant. Your ONLY job is to output one line.

User's existing rooms:
{rooms_list}{current_room_context}

User message: "{user_message}"

INSTRUCTIONS:
1. Identify the TARGET room (the room they want to design/work on)
2. Ignore REFERENCE rooms (rooms mentioned for inspiration like "same as bedroom")
3. Determine if they want to create a NEW room or modify an EXISTING one

OUTPUT ONLY ONE OF THESE FORMATS (nothing else):
- NEW bedroom
- NEW living_room
- NEW dining_room
- NEW kitchen
- NEW bathroom
- NEW office
- EXISTING [room name from list above]

Examples:
"design a living room like my bedroom" -> NEW living_room
"make the bedroom nicer" -> EXISTING Bedroom
"show me images" -> [skip classification, return nothing]

OUTPUT (one line only):"""

        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Use fast Haiku for classification
                max_tokens=20,  # Reduced to force concise answers
                temperature=0,  # Deterministic output
                messages=[{"role": "user", "content": classifier_prompt}]
            )
            classification = response.content[0].text.strip().upper()
            print(f"DEBUG: Room classification (raw): {classification}")

            # Parse the classification, being tolerant of verbose responses
            if "EXISTING" in classification:
                # Only try to match existing rooms if user has rooms
                if rooms:
                    # Extract room name from classification
                    for room in rooms:
                        if room.name.upper() in classification or room.room_type.value.upper() in classification:
                            print(f"DEBUG: Matched existing room: {room.name}")
                            return room.id, room.name, None
                    # Fallback: check message for room names
                    message_lower = user_message.lower()
                    for room in rooms:
                        if room.name.lower() in message_lower or room.room_type.value in message_lower:
                            print(f"DEBUG: Fallback matched existing room: {room.name}")
                            return room.id, room.name, None
                # No rooms to match or no match found
                print(f"DEBUG: EXISTING mentioned but no room match, returning None")
                return None, None, None

            elif "NEW" in classification:
                # Extract room type from classification - be tolerant of format
                # Look for room type keywords in the classification
                room_type_keywords = {
                    "LIVING": "living_room",
                    "LIVING_ROOM": "living_room",
                    "BEDROOM": "bedroom",
                    "DINING": "dining_room",
                    "DINING_ROOM": "dining_room",
                    "KITCHEN": "kitchen",
                    "BATHROOM": "bathroom",
                    "OFFICE": "office",
                }

                for keyword, room_type in room_type_keywords.items():
                    if keyword in classification:
                        print(f"DEBUG: Extracted room type: {room_type}")
                        return None, None, room_type

                # Default to "other" if we can't identify the room type
                print(f"DEBUG: Could not identify room type, defaulting to 'other'")
                return None, None, "other"

            # Classification doesn't contain NEW or EXISTING - unclear intent
            print(f"DEBUG: Classification unclear, returning None")
            return None, None, None

        except Exception as e:
            print(f"DEBUG: Classifier error: {e}, falling back to None")
            return None, None, None

    async def _create_room_from_context(
        self, user_id: str, room_type_str: str
    ) -> Optional[str]:
        """Create a new room based on identified room type.

        Args:
            user_id: User ID
            room_type_str: Room type string from classifier (e.g., "living_room", "bedroom")

        Returns:
            Room ID of created room
        """
        # Map room type string to RoomType enum and display name
        room_type_map = {
            "bedroom": (RoomType.BEDROOM, "Bedroom"),
            "living_room": (RoomType.LIVING_ROOM, "Living Room"),
            "dining_room": (RoomType.DINING_ROOM, "Dining Room"),
            "kitchen": (RoomType.KITCHEN, "Kitchen"),
            "bathroom": (RoomType.BATHROOM, "Bathroom"),
            "office": (RoomType.OFFICE, "Home Office"),
            "other": (RoomType.OTHER, "New Room"),
        }

        room_type, room_name = room_type_map.get(room_type_str, (RoomType.OTHER, "New Room"))
        print(f"DEBUG: Creating room: type={room_type.value}, name={room_name}")

        # Create room
        room = Room(user_id=user_id, name=room_name, room_type=room_type)
        room = self.storage.create_room(room)

        return room.id

    async def _get_reference_image(
        self, user_id: str, room_id: str, parent_version_id: Optional[str], user_message: str
    ) -> Optional[str]:
        """
        Get reference image URL for image editing mode or cross-room inspiration.

        Returns reference image if:
        1. Iterating on existing design (parent version exists with selected image)
        2. Cross-room inspiration detected in user message

        Args:
            user_id: User ID
            room_id: Current room ID
            parent_version_id: Parent version ID (if iterating)
            user_message: User's original message

        Returns:
            Reference image URL or None
        """
        # Case 1: Iterating on existing design (parent version exists)
        if parent_version_id:
            parent_images = self.storage.get_design_images(parent_version_id)
            # Find selected image from parent version
            for img in parent_images:
                if img.selected:
                    print(f"DEBUG: Using parent version image as reference for iteration: {img.image_url}")
                    return img.image_url

        # Case 2: Cross-room inspiration - check user message for room references
        message_lower = user_message.lower()

        # Patterns to detect cross-room references
        cross_room_patterns = [
            r"same (?:as|vibe as|style as|design as) (?:the |my )?(\w+)",
            r"like (?:the |my )?(\w+)(?: room)?",
            r"inspired by (?:the |my )?(\w+)",
            r"similar to (?:the |my )?(\w+)",
            r"match(?:ing)? (?:the |my )?(\w+)",
        ]

        referenced_room_name = None
        for pattern in cross_room_patterns:
            match = re.search(pattern, message_lower)
            if match:
                referenced_room_name = match.group(1).strip()
                print(f"DEBUG: Detected cross-room reference: '{referenced_room_name}'")
                break

        # Find the referenced room and get its selected design image
        if referenced_room_name:
            user_rooms = self.storage.get_user_rooms(user_id)
            for room in user_rooms:
                # Skip current room
                if room.id == room_id:
                    continue

                # Match by name or type
                room_name_lower = room.name.lower()
                room_type_lower = room.room_type.value.lower().replace('_', ' ')

                if (
                    referenced_room_name in room_name_lower
                    or referenced_room_name in room_type_lower
                    or room_name_lower in referenced_room_name
                    or room_type_lower in referenced_room_name
                ):
                    print(f"DEBUG: Found matching room: {room.name} (type: {room.room_type.value})")
                    # Get selected design from this room
                    room_versions = self.storage.get_room_design_versions(room.id)
                    for version in reversed(room_versions):  # Start with latest
                        if version.selected:
                            version_images = self.storage.get_design_images(version.id)
                            for img in version_images:
                                if img.selected:
                                    print(
                                        f"DEBUG: Using cross-room reference image from {room.name}: {img.image_url}"
                                    )
                                    return img.image_url

                    # If no selected version, use latest version's first image
                    if room_versions:
                        latest_version = room_versions[-1]
                        latest_images = self.storage.get_design_images(latest_version.id)
                        if latest_images:
                            print(f"DEBUG: Using latest image from {room.name} (no selection): {latest_images[0].image_url}")
                            return latest_images[0].image_url

        # No reference image found (new design from scratch)
        return None

    def _is_design_response(self, response: str) -> bool:
        """Check if response contains an actual design description."""
        response_lower = response.lower()

        # Check for design option indicators (Option 1, Option 2, etc.)
        has_options = bool(re.search(r'option\s+\d|design\s+\d|concept\s+\d', response_lower))

        # Check for structured design sections
        design_sections = [
            "color palette",
            "layout & furniture",
            "materials & textures",
            "furniture:",
            "lighting:",
            "color scheme",
            "materials:",
            "textures:",
            "seating & layout",
            "seating area"
        ]
        has_sections = any(section in response_lower for section in design_sections)
        print(f"DEBUG: has_options={has_options}, has_sections={has_sections}")

        # Check for comprehensive design keywords (need multiple)
        design_keywords = [
            "furniture",
            "palette",
            "materials",
            "lighting",
            "textures",
            "layout",
            "upholstered",
            "nightstand",
            "dresser",
            "rug",
            "curtain",
            "sofa",
            "sectional",
            "armchair",
            "coffee table",
            "shelves",
            "pendant",
            "cushion"
        ]
        keyword_count = sum(1 for keyword in design_keywords if keyword in response_lower)
        print(f"DEBUG: keyword_count={keyword_count}")

        # It's a design if: has options OR (has sections AND multiple keywords)
        is_design = has_options or (has_sections and keyword_count >= 4)
        print(f"DEBUG: Final is_design={is_design} (has_options={has_options} OR (has_sections={has_sections} AND keyword_count={keyword_count}>=4))")
        return is_design

    async def _generate_design_version(
        self, room_id: str, design_description: str, user_id: str, user_message: str
    ) -> Tuple[str, List[dict]]:
        """Generate a design version with images."""
        # Get existing versions
        versions = self.storage.get_room_design_versions(room_id)
        version_number = len(versions) + 1

        # Get parent version (latest)
        parent_id = versions[-1].id if versions else None

        # Get reference image for editing mode or cross-room inspiration
        reference_image_url = await self._get_reference_image(
            user_id, room_id, parent_id, user_message
        )

        # Create design version
        design_version = DesignVersion(
            room_id=room_id,
            version_number=version_number,
            description=design_description[:500],  # Truncate if too long
            parent_version_id=parent_id,
        )
        design_version = self.storage.create_design_version(design_version)

        # Generate images (3 variations)
        num_images = 3
        image_data = []

        for i in range(num_images):
            # Create variation prompt
            variation_prompt = f"{design_description[:200]} - variation {i+1}"

            # Generate image (with reference if available for editing)
            image_url = await self.image_gen.generate(
                variation_prompt,
                reference_image_url=reference_image_url
            )

            # Store image
            design_image = DesignImage(
                design_version_id=design_version.id,
                image_url=image_url,
                prompt=variation_prompt,
            )
            created_image = self.storage.create_design_image(design_image)
            image_data.append({"id": created_image.id, "url": image_url})

        return design_version.id, image_data

    async def select_design(
        self, user_id: str, design_version_id: str, image_id: Optional[str] = None
    ):
        """Mark a design as selected and learn preferences."""
        import asyncio

        # Get design version
        version = self.storage.get_design_version(design_version_id)
        if not version:
            return

        # Mark as selected
        version.selected = True
        self.storage.update_design_version(version)

        # Mark image as selected if specified
        selected_image_url = None
        if image_id:
            images = self.storage.get_design_images(design_version_id)
            for img in images:
                if img.id == image_id:
                    img.selected = True
                    self.storage.update_design_image(img)
                    selected_image_url = img.image_url
                    break

        # ALL PREFERENCE LEARNING HAPPENS IN BACKGROUND (NON-BLOCKING)
        # This ensures instant response to frontend
        asyncio.create_task(
            self._learn_preferences_background(
                user_id, version.description, version.room_id, selected_image_url
            )
        )

    async def _learn_preferences_background(
        self, user_id: str, description: str, room_id: Optional[str], image_url: Optional[str]
    ):
        """Run all preference learning in background without blocking selection response."""
        try:
            # Text-based learning (from description)
            print(f"Background text-based learning started for user {user_id}")
            self.memory.learn_from_design_selection(user_id, description, room_id)

            # Image-based learning (visual analysis)
            if image_url:
                print(f"Background image analysis started for: {image_url}")
                await self.memory.learn_from_selected_image(user_id, image_url, room_id)

            print(f"Background preference learning completed for user {user_id}")
        except Exception as e:
            print(f"ERROR in background preference learning: {e}")


# Global agent instance
design_agent = DesignAgent()
