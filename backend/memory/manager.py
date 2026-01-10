"""Memory manager orchestrating all memory operations."""
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import uuid

from backend.config import config
from backend.memory.learner import preference_learner
from backend.memory.storage import storage
from backend.memory.chroma_store import ChromaStore
from backend.models.schemas import ConversationMessage, UserPreference
from backend.models.types import MessageRole


class MemoryManager:
    """Orchestrates all memory operations for the design agent."""

    def __init__(self):
        # Initialize ChromaDB with HuggingFace embeddings
        self.chroma = ChromaStore(
            persist_directory=config.CHROMA_DB_PATH,
            model_name="BAAI/bge-small-en-v1.5"
        )
        self.storage = storage
        self.learner = preference_learner

    def store_conversation(
        self,
        user_id: str,
        session_id: str,
        message: str,
        role: MessageRole,
        room_id: Optional[str] = None,
    ) -> ConversationMessage:
        """
        Store a conversation message with embedding in ChromaDB.

        Args:
            user_id: User ID
            session_id: Session ID
            message: Message text
            role: Message role (user/agent)
            room_id: Optional room ID

        Returns:
            ConversationMessage instance
        """
        # Create conversation message
        conv_message = ConversationMessage(
            user_id=user_id,
            session_id=session_id,
            message=message,
            role=role,
            room_id=room_id,
        )

        # Add to ChromaDB with metadata
        try:
            self.chroma.add(
                documents=[message],
                metadatas=[{
                    "user_id": user_id,
                    "session_id": session_id,
                    "role": role.value,
                    "room_id": room_id or "",
                    "timestamp": conv_message.created_at.isoformat(),
                    "message_id": conv_message.id,
                }],
                ids=[conv_message.id]
            )
        except Exception as e:
            # Log error but don't fail the request if embedding fails
            print(f"WARNING: Failed to embed conversation: {e}")
            # Continue without embedding - conversation history still works via recent context

        # Learn preferences from user messages
        if role == MessageRole.USER:
            try:
                preferences = self.learner.extract_preferences_from_text(
                    message, user_id, room_id
                )
                for pref in preferences:
                    self.learner.update_preference_confidence(
                        user_id,
                        pref.preference_type,
                        pref.preference_value,
                        confidence_delta=0.1,  # Implicit mention
                        source_room_id=room_id,
                    )
            except Exception as e:
                print(f"WARNING: Failed to extract preferences: {e}")

        return conv_message

    def retrieve_relevant_context(
        self,
        query: str,
        user_id: str,
        room_id: Optional[str] = None,
        top_k: int = None,
    ) -> List[Dict]:
        """
        Retrieve relevant conversation context using semantic search.

        Args:
            query: Query text
            user_id: User ID to filter by
            room_id: Optional room ID to filter by
            top_k: Number of results to return

        Returns:
            List of dicts with 'text', 'metadata', 'score'
        """
        try:
            # Build metadata filter
            where_filter = {"user_id": user_id}
            if room_id:
                where_filter["room_id"] = room_id

            # Query ChromaDB
            results = self.chroma.query(
                query_text=query,
                n_results=top_k or config.SIMILARITY_TOP_K,
                where=where_filter
            )

            # Format results
            nodes = []
            if results and results['documents'] and len(results['documents']) > 0:
                docs = results['documents'][0]  # First query result
                metadatas = results['metadatas'][0] if results['metadatas'] else []
                distances = results['distances'][0] if results['distances'] else []

                for i, doc in enumerate(docs):
                    # Convert distance to similarity score (1 - distance for cosine)
                    score = 1.0 - distances[i] if i < len(distances) else 0.0
                    metadata = metadatas[i] if i < len(metadatas) else {}

                    nodes.append({
                        "text": doc,
                        "metadata": metadata,
                        "score": score
                    })

            return nodes
        except Exception as e:
            print(f"WARNING: Failed to retrieve context: {e}")
            return []

    def get_user_preferences(
        self, user_id: str, confidence_threshold: float = None
    ) -> List[UserPreference]:
        """Get user preferences above confidence threshold."""
        threshold = confidence_threshold or config.PREFERENCE_CONFIDENCE_THRESHOLD
        return self.storage.get_user_preferences(user_id, threshold)

    def get_preference_summary(self, user_id: str) -> dict:
        """Get summary of user preferences by type."""
        return self.learner.get_preference_summary(user_id)

    def format_context_for_llm(
        self,
        query: str,
        user_id: str,
        room_id: Optional[str] = None,
    ) -> str:
        """
        Format retrieved context and preferences for LLM.

        Returns formatted string with:
        - Relevant past conversations
        - User preferences
        - Current room information
        """
        # Retrieve relevant conversations
        try:
            nodes = self.retrieve_relevant_context(query, user_id, room_id)
        except Exception as e:
            print(f"WARNING: Failed to retrieve context (rate limit?): {e}")
            nodes = []  # Continue without semantic search context

        # Get user preferences
        preferences = self.get_user_preferences(user_id)
        pref_summary = self.get_preference_summary(user_id)

        # Get current room info if specified
        room_info = ""
        if room_id:
            room = self.storage.get_room(room_id)
            if room:
                room_info = f"\nCurrent Room: {room.name} ({room.room_type.value})"

                # Get design history
                versions = self.storage.get_room_design_versions(room_id)
                if versions:
                    latest = versions[-1]
                    room_info += f"\nLatest Design: Version {latest.version_number} - {latest.description}"

        # Format context
        context_parts = []

        if room_info:
            context_parts.append(f"## Room Context{room_info}\n")

        if pref_summary:
            context_parts.append("## User Preferences")
            for pref_type, values in pref_summary.items():
                context_parts.append(f"- {pref_type.title()}: {', '.join(values)}")
            context_parts.append("")

        if nodes:
            context_parts.append("## Relevant Past Conversations")
            for i, node in enumerate(nodes, 1):
                metadata = node.get("metadata", {})
                role = metadata.get("role", "unknown")
                timestamp = metadata.get("timestamp", "")
                text = node.get("text", "")
                score = node.get("score", 0.0)

                context_parts.append(
                    f"{i}. [{role}] (relevance: {score:.2f}): {text[:200]}..."
                )
            context_parts.append("")

        return "\n".join(context_parts)

    def learn_from_design_selection(
        self, user_id: str, design_description: str, room_id: Optional[str] = None
    ):
        """Learn preferences from user's design selection."""
        self.learner.learn_from_selection(user_id, design_description, room_id)

    def learn_from_feedback(
        self,
        user_id: str,
        feedback: str,
        is_positive: bool,
        room_id: Optional[str] = None,
    ):
        """Learn preferences from user feedback."""
        self.learner.learn_from_feedback(user_id, feedback, is_positive, room_id)


# Global memory manager instance
memory_manager = MemoryManager()
