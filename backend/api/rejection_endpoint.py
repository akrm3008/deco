"""
RECOMMENDATION: Add this to backend/api/routes.py to complete rejection learning
"""

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


# Also add explicit feedback endpoint:
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
