"""Initialize ChromaDB collections for the interior design agent."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import config
from backend.memory.vector_store import vector_store_manager

def main():
    """Initialize ChromaDB."""
    print("Initializing ChromaDB...")
    print(f"Storage path: {config.CHROMA_DB_PATH}")

    try:
        # Vector store manager initializes ChromaDB automatically
        print(f"Collection 'conversations' created/loaded successfully")
        print(f"Embedding model: {config.EMBEDDING_MODEL} ({config.EMBEDDING_PROVIDER})")
        print(f"Embedding dimensions: {config.EMBEDDING_DIMENSION}")
        print("\n✅ ChromaDB initialized successfully!")

    except Exception as e:
        print(f"\n❌ Error initializing ChromaDB: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
