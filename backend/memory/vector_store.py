"""ChromaDB vector store setup for LlamaIndex."""
import chromadb
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.voyageai import VoyageEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from backend.config import config


def get_embedding_model():
    """Get the configured embedding model."""
    if config.EMBEDDING_PROVIDER == "voyage":
        if not config.VOYAGE_API_KEY:
            raise ValueError("VOYAGE_API_KEY not configured")
        return VoyageEmbedding(
            model_name=config.EMBEDDING_MODEL,
            voyage_api_key=config.VOYAGE_API_KEY,
        )
    elif config.EMBEDDING_PROVIDER == "openai":
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        return OpenAIEmbedding(
            model=config.EMBEDDING_MODEL,
            api_key=config.OPENAI_API_KEY,
        )
    elif config.EMBEDDING_PROVIDER == "huggingface":
        # Local HuggingFace embeddings - no API key needed
        return HuggingFaceEmbedding(
            model_name=config.EMBEDDING_MODEL,
        )
    else:
        raise ValueError(f"Unknown embedding provider: {config.EMBEDDING_PROVIDER}")


class VectorStoreManager:
    """Manages ChromaDB vector store and LlamaIndex integration."""

    def __init__(self):
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=str(config.CHROMA_DB_PATH))

        # Create or get collection for conversations
        self.collection = self.chroma_client.get_or_create_collection(
            name="conversations",
            metadata={"hnsw:space": "cosine"},  # Use cosine similarity
        )

        # Create LlamaIndex vector store
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)

        # Create storage context
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )

        # Get embedding model
        self.embed_model = get_embedding_model()

        # Initialize vector store index (will be empty initially)
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            storage_context=self.storage_context,
            embed_model=self.embed_model,
        )

    def get_index(self) -> VectorStoreIndex:
        """Get the vector store index."""
        return self.index

    def get_retriever(self, similarity_top_k: int = None):
        """Get a retriever for semantic search."""
        if similarity_top_k is None:
            similarity_top_k = config.SIMILARITY_TOP_K

        return self.index.as_retriever(similarity_top_k=similarity_top_k)

    def clear_collection(self):
        """Clear all data from the collection (for testing)."""
        self.chroma_client.delete_collection("conversations")
        self.collection = self.chroma_client.create_collection(
            name="conversations",
            metadata={"hnsw:space": "cosine"},
        )
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            storage_context=self.storage_context,
            embed_model=self.embed_model,
        )


# Global vector store instance
vector_store_manager = VectorStoreManager()
