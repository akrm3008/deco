"""Custom retriever with hybrid search (vector + metadata + recency)."""
from datetime import datetime, timedelta
from typing import List, Optional

from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle

from backend.config import config


class HybridRetriever(BaseRetriever):
    """Custom retriever combining vector similarity, metadata filtering, and recency boosting."""

    def __init__(
        self,
        base_retriever: BaseRetriever,
        user_id: Optional[str] = None,
        room_id: Optional[str] = None,
        recency_weight: float = 0.3,
        similarity_weight: float = 0.7,
        top_k: int = None,
    ):
        """
        Initialize hybrid retriever.

        Args:
            base_retriever: Base LlamaIndex retriever
            user_id: Filter by user_id if provided
            room_id: Filter by room_id if provided
            recency_weight: Weight for recency score (0-1)
            similarity_weight: Weight for similarity score (0-1)
            top_k: Number of results to return
        """
        self.base_retriever = base_retriever
        self.user_id = user_id
        self.room_id = room_id
        self.recency_weight = recency_weight
        self.similarity_weight = similarity_weight
        self.top_k = top_k or config.SIMILARITY_TOP_K
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Retrieve nodes with hybrid scoring."""
        # Get base retrieval results (vector similarity)
        # Request more than needed since we'll filter
        nodes = self.base_retriever.retrieve(query_bundle)

        # Filter by metadata
        filtered_nodes = []
        for node_with_score in nodes:
            metadata = node_with_score.node.metadata

            # Filter by user_id if specified
            if self.user_id and metadata.get("user_id") != self.user_id:
                continue

            # Filter by room_id if specified
            if self.room_id and metadata.get("room_id") != self.room_id:
                continue

            filtered_nodes.append(node_with_score)

        # Re-score with recency boost
        rescored_nodes = []
        current_time = datetime.utcnow()

        for node_with_score in filtered_nodes:
            metadata = node_with_score.node.metadata
            similarity_score = node_with_score.score

            # Calculate recency score (exponential decay)
            timestamp_str = metadata.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    age_days = (current_time - timestamp).total_seconds() / 86400
                    # Exponential decay: 1.0 for today, 0.5 after ~7 days
                    recency_score = 2 ** (-age_days / 7)
                except (ValueError, AttributeError):
                    recency_score = 0.5  # Default if timestamp invalid
            else:
                recency_score = 0.5  # Default if no timestamp

            # Combined score
            final_score = (
                self.similarity_weight * similarity_score
                + self.recency_weight * recency_score
            )

            rescored_node = NodeWithScore(
                node=node_with_score.node, score=final_score
            )
            rescored_nodes.append(rescored_node)

        # Sort by combined score and return top_k
        rescored_nodes.sort(key=lambda x: x.score, reverse=True)
        return rescored_nodes[: self.top_k]
