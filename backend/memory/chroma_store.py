"""ChromaDB vector store with HuggingFace embeddings (no LlamaIndex)."""
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
from typing import List, Dict, Optional


class ChromaStore:
    """Simple ChromaDB wrapper with HuggingFace embeddings."""

    def __init__(self, persist_directory: Path, model_name: str = "BAAI/bge-small-en-v1.5"):
        """Initialize ChromaDB with HuggingFace embeddings.

        Args:
            persist_directory: Directory to persist ChromaDB data
            model_name: HuggingFace model name for embeddings
        """
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=str(persist_directory))

        # Create embedding function using HuggingFace
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )

        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="conversations",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

    def add(
        self,
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> None:
        """Add documents to the collection.

        Args:
            documents: List of text documents
            metadatas: List of metadata dicts for each document
            ids: List of unique IDs for each document
        """
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        """Query the collection.

        Args:
            query_text: Text to search for
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            Dict with 'ids', 'documents', 'metadatas', 'distances'
        """
        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )

    def delete(self, ids: List[str]) -> None:
        """Delete documents by ID.

        Args:
            ids: List of document IDs to delete
        """
        self.collection.delete(ids=ids)

    def count(self) -> int:
        """Get count of documents in collection."""
        return self.collection.count()

    def clear(self) -> None:
        """Clear all documents from collection."""
        self.client.delete_collection("conversations")
        self.collection = self.client.get_or_create_collection(
            name="conversations",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
