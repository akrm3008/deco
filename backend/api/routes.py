"""API routes for the interior design agent."""
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from backend.agent.design_agent import design_agent
from backend.memory.storage import storage
from backend.memory.manager import memory_manager
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    DesignVersionListResponse,
    PreferenceListResponse,
    RoomListResponse,
    User,
)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the design agent.

    Stores conversation history and generates design responses.
    """
    try:
        # Ensure user exists
        user = storage.get_user(request.user_id)
        if not user:
            user = User(id=request.user_id)
            storage.create_user(user)

        # Process message with agent
        response_text, room_id, version_id, images = await design_agent.chat(
            user_message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            room_id=request.room_id,
        )

        return ChatResponse(
            message=response_text,
            room_id=room_id,
            design_version_id=version_id,
            images=images
        )

    except Exception as e:
        import traceback
        print(f"ERROR in /chat endpoint: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms/{user_id}", response_model=RoomListResponse)
async def get_user_rooms(user_id: str):
    """Get all rooms for a user."""
    try:
        rooms = storage.get_user_rooms(user_id)
        return RoomListResponse(rooms=rooms)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms/{room_id}/designs", response_model=DesignVersionListResponse)
async def get_room_designs(room_id: str):
    """Get all design versions for a room with their images."""
    try:
        versions = storage.get_room_design_versions(room_id)

        # Get images for each version
        images_by_version = {}
        for version in versions:
            images = storage.get_design_images(version.id)
            images_by_version[version.id] = images

        return DesignVersionListResponse(
            versions=versions, images=images_by_version
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rooms/{room_id}/designs/{version_id}/select")
async def select_design(
    room_id: str, version_id: str, user_id: str, image_id: Optional[str] = None
):
    """Mark a design version as selected."""
    try:
        await design_agent.select_design(user_id, version_id, image_id)
        return {"status": "success", "message": "Design selected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rooms/{room_id}/designs/{version_id}/reject")
async def reject_design(
    room_id: str,
    version_id: str,
    user_id: str,
    feedback: str = "I don't like this design"
):
    """
    Mark a design version as rejected and learn from it.

    This decreases confidence in preferences found in the design.
    """
    try:
        # Get the rejected design
        version = storage.get_design_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Design not found")

        # Mark as rejected
        version.rejected = True
        storage.update_design_version(version)

        # Learn from rejection (negative feedback)
        memory_manager.learn_from_feedback(
            user_id=user_id,
            feedback=version.description + " " + feedback,
            is_positive=False,  # This is a rejection
            room_id=room_id
        )

        return {
            "status": "success",
            "message": "Rejection recorded, preferences updated"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(
    user_id: str,
    feedback_text: str,
    is_positive: bool,
    room_id: Optional[str] = None
):
    """
    Submit explicit feedback to improve preference learning.

    Examples:
    - "I love warm colors" (is_positive=True)
    - "Too modern for me" (is_positive=False)
    """
    try:
        memory_manager.learn_from_feedback(
            user_id=user_id,
            feedback=feedback_text,
            is_positive=is_positive,
            room_id=room_id
        )

        return {
            "status": "success",
            "message": "Feedback recorded"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences/{user_id}", response_model=PreferenceListResponse)
async def get_user_preferences(user_id: str):
    """Get learned preferences for a user."""
    try:
        preferences = storage.get_user_preferences(user_id)
        return PreferenceListResponse(preferences=preferences)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "interior-design-agent"}
