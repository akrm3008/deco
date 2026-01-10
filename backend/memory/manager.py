"""Memory manager orchestrating all memory operations."""
from datetime import datetime
from typing import List, Optional

from llama_index.core import Document
from llama_index.core.schema import NodeWithScore

from backend.config import config
from backend.memory.learner import preference_learner
from backend.memory.retriever import HybridRetriever
from backend.memory.storage import storage
from backend.memory.vector_store import vector_store_manager
from backend.models.schemas import ConversationMessage, UserPreference
from backend.models.types import MessageRole


class MemoryManager:
    """Orchestrates all memory operations for the design agent."""

    def __init__(self):
        self.vector_store = vector_store_manager
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

        # Create LlamaIndex document with metadata
        doc = Document(
            text=message,
            metadata={
                "user_id": user_id,
                "session_id": session_id,
                "role": role.value,
                "room_id": room_id or "",
                "timestamp": conv_message.created_at.isoformat(),
                "message_id": conv_message.id,
            },
        )

        # Add to vector store index (automatically embeds)
        try:
            self.vector_store.index.insert(doc)
        except Exception as e:
            # Log error but don't fail the request if embedding fails
            print(f"WARNING: Failed to embed conversation (rate limit?): {e}")
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
    ) -> List[NodeWithScore]:
        """
        Retrieve relevant conversation context using hybrid search.

        Args:
            query: Query text
            user_id: User ID to filter by
            room_id: Optional room ID to filter by
            top_k: Number of results to return

        Returns:
            List of relevant conversation nodes with scores
        """
        # Get base retriever
        base_retriever = self.vector_store.get_retriever(similarity_top_k=top_k or config.SIMILARITY_TOP_K * 2)

        # Create hybrid retriever with filters
        hybrid_retriever = HybridRetriever(
            base_retriever=base_retriever,
            user_id=user_id,
            room_id=room_id,
            top_k=top_k or config.SIMILARITY_TOP_K,
        )

        # Retrieve relevant nodes
        from llama_index.core.schema import QueryBundle

        query_bundle = QueryBundle(query_str=query)
        nodes = hybrid_retriever.retrieve(query_bundle)

        return nodes

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
        nodes = self.retrieve_relevant_context(query, user_id, room_id)

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
                metadata = node.node.metadata
                role = metadata.get("role", "unknown")
                timestamp = metadata.get("timestamp", "")
                text = node.node.text
                score = node.score

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
