"""Authentication API routes with custom username/password authentication."""
from fastapi import APIRouter, HTTPException
from backend.memory.storage import storage
from backend.models.schemas import (
    User,
    UserResponse,
    LoginRequest,
    RegisterRequest,
)
from backend.utils.auth import hash_password, verify_password

router = APIRouter()


@router.post("/signup", response_model=UserResponse)
async def signup(request: RegisterRequest):
    """Register a new user with username and password."""
    try:
        # Check if username already exists
        existing_user = storage.get_user_by_username(request.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")

        # Create user with hashed password
        user = User(
            username=request.username,
            password_hash=hash_password(request.password)
        )

        created_user = storage.create_user(user)

        # Return user without password
        return UserResponse(
            id=created_user.id,
            username=created_user.username,
            created_at=created_user.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=UserResponse)
async def login(request: LoginRequest):
    """Login with username and password."""
    try:
        # Get user by username
        user = storage.get_user_by_username(request.username)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Verify password
        if not user.password_hash or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Return user without password
        return UserResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/data")
async def get_user_data(user_id: str):
    """Get all data for authenticated user (rooms, preferences, designs)."""
    try:
        # Get user
        user = storage.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get all user data
        rooms = storage.get_user_rooms(user_id)
        preferences = storage.get_user_preferences(user_id)

        # Get designs for each room
        designs_by_room = {}
        for room in rooms:
            versions = storage.get_room_design_versions(room.id)
            images_by_version = {}
            for version in versions:
                images = storage.get_design_images(version.id)
                images_by_version[version.id] = images
            designs_by_room[room.id] = {
                "versions": versions,
                "images": images_by_version
            }

        return {
            "user": UserResponse(
                id=user.id,
                username=user.username,
                created_at=user.created_at
            ),
            "rooms": rooms,
            "preferences": preferences,
            "designs": designs_by_room
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get user data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def logout():
    """Logout user (handled on frontend by clearing session)."""
    return {"message": "Logout successful"}
