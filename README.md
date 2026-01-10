# Interior Design Agent Memory System

An AI-powered interior design assistant with persistent memory across sessions. Built for the Affinity Labs Senior Software Engineer challenge.

## Features

- **Persistent Memory**: Remembers user preferences, past designs, and conversations across sessions spanning days or weeks
- **Semantic Search**: Uses local vector embeddings (ChromaDB + HuggingFace) to retrieve relevant context from past conversations
- **Preference Learning**: Automatically learns and strengthens user preferences (style, warmth, complexity) based on selections and feedback
- **Design Version Tracking**: Maintains hierarchical design history with parent-child relationships
- **Cross-Room Consistency**: Applies learned preferences across different rooms ("design my living room like my bedroom")
- **AI Image Generation**: Real interior design images using OpenAI's gpt-image-1 model
- **Real-time Chat**: Interactive web interface with instant design feedback

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Vector Database**: ChromaDB (local, zero-setup)
- **Embeddings**: Local HuggingFace models (sentence-transformers) - no API key required
- **LLM**: Claude 4.5 Sonnet (Anthropic API)
- **Image Generation**: OpenAI gpt-image-1 (optional, falls back to placeholder)
- **Frontend**: HTML, CSS, JavaScript with HTMX

## Quick Start

### 1. Prerequisites

- Python 3.11 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))
- OpenAI API key (optional, for AI image generation - [get one here](https://platform.openai.com/))

### 2. Installation

```bash
# Clone the repository
cd deco

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
# Required:
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional (for AI image generation):
OPENAI_API_KEY=your_openai_key_here
IMAGE_GENERATOR=gpt-image-1  # Use 'placeholder' for testing without API calls

# Embeddings run locally - no API key needed!
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

### 4. Run the Application

```bash
# Start the FastAPI server
python -m backend.main

# Open your browser
# Navigate to: http://localhost:8000
```

## Usage Guide

### Starting a Conversation

1. Open http://localhost:8000 in your browser
2. Start chatting! Example: "Help me design a modern bedroom"
3. The agent will generate design descriptions and remember them

### Demo Scenarios

Try these scenarios to see the memory system in action:

#### Scenario 1: Initial Bedroom Design (Day 1)
```
You: "Help me design a modern bedroom"
Agent: [Generates 5 design options]

You: "I like option 3, but make it warmer"
Agent: [Generates revised version with warmer tones]

You: "Perfect, save this"
Agent: [Saves design, learns preference for warmth]
```

#### Scenario 2: Living Room with Cross-Room Reference (1 week later)
```
You: "Design my living room with the same vibe as the bedroom"
Agent: [Retrieves bedroom context, applies learned preferences]
```

#### Scenario 3: Bedroom Update (2 weeks later)
```
You: "Add more plants to my bedroom"
Agent: [Finds saved bedroom design, creates version 2]
```

#### Scenario 4: Office with Learned Preferences (1 month later)
```
You: "Design my home office, simpler than the other rooms"
Agent: [Applies learned style, understands comparative complexity]
```

## Project Structure

```
deco/
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration
│   ├── models/
│   │   ├── schemas.py          # Pydantic models
│   │   └── types.py            # Enums and types
│   ├── memory/
│   │   ├── manager.py          # Memory orchestration
│   │   ├── chroma_store.py     # ChromaDB wrapper with HuggingFace embeddings
│   │   ├── learner.py          # Preference learning
│   │   └── storage.py          # JSON storage for rooms/designs/preferences
│   ├── agent/
│   │   ├── design_agent.py     # Main agent logic
│   │   ├── image_generator.py  # OpenAI gpt-image-1 integration
│   │   └── prompts.py          # System prompts
│   └── api/
│       └── routes.py           # API endpoints
├── frontend/
│   ├── static/
│   │   ├── css/styles.css
│   │   └── js/app.js
│   └── templates/
│       └── index.html
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

### Chat
```
POST /api/chat
Body: {
  "message": str,
  "user_id": str,
  "session_id": str,
  "room_id": str (optional)
}
Response: {
  "message": str,
  "room_id": str,
  "images": [str]
}
```

### Get User Rooms
```
GET /api/rooms/{user_id}
Response: {
  "rooms": [Room]
}
```

### Get Room Designs
```
GET /api/rooms/{room_id}/designs
Response: {
  "versions": [DesignVersion],
  "images": {version_id: [DesignImage]}
}
```

### Get User Preferences
```
GET /api/preferences/{user_id}
Response: {
  "preferences": [UserPreference]
}
```

## Memory System Architecture

### 1. Vector Storage (ChromaDB + HuggingFace)
- Stores all conversation messages with local embeddings (BAAI/bge-small-en-v1.5)
- Enables semantic search for relevant context using cosine similarity
- Metadata filtering by user, room, timestamp
- **No API calls** - embeddings generated locally

### 2. Structured Storage (JSON)
- Rooms, design versions, images
- User preferences with confidence scores
- Design hierarchy tracking
- Stored in `./data/` directory

### 3. Context Retrieval
- **Semantic search**: Vector similarity using local embeddings
- **Metadata filtering**: By user_id and room_id
- **Top-K retrieval**: Configurable (default: 5 most relevant messages)
- **Graceful degradation**: Falls back if embeddings fail

### 4. Preference Learning
- **Implicit**: Detects keywords in conversation (+0.1 confidence)
- **Explicit selection**: User picks a design (+0.3 confidence)
- **Feedback**: Positive/negative feedback (±0.2 confidence)
- **Time decay**: 5% confidence reduction per week

## Configuration Options

### Embeddings (Local)

Embeddings run locally using HuggingFace sentence-transformers. No API key required!

**Default** (Recommended):
```env
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384
```

**Other options**:
- `all-MiniLM-L6-v2` (384 dimensions) - Faster, slightly less accurate
- `all-mpnet-base-v2` (768 dimensions) - Slower, more accurate

### Image Generation

**Placeholder** (Default - for development):
```env
IMAGE_GENERATOR=placeholder
```

**OpenAI gpt-image-1** (Real AI images):
```env
IMAGE_GENERATOR=gpt-image-1
OPENAI_API_KEY=your_openai_api_key
```

## Development

### Running Tests
```bash
pytest tests/
```

### Clearing Data
```bash
# Remove ChromaDB data
rm -rf chroma_db/

# Remove structured data
rm -rf data/
```

### Viewing Logs
Logs are output to console with configurable level:
```env
LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR
```

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY is required"
**Solution**: Add your Anthropic API key to `.env` file

### Issue: "Failed to import chromadb" or "sentence-transformers not found"
**Solution**: Reinstall dependencies: `pip install -r requirements.txt`

### Issue: OpenAI image generation errors
**Solution**:
- Check that `OPENAI_API_KEY` is set correctly in `.env`
- Verify `IMAGE_GENERATOR=gpt-image-1` (not gpt-image-1.5)
- For testing without API costs, use `IMAGE_GENERATOR=placeholder`

### Issue: Memory not persisting across restarts
**Solution**: Check that `./chroma_db` and `./data` directories exist and have write permissions

### Issue: "Embedding dimension 384 does not match collection dimensionality 1024"
**Solution**: Clear old ChromaDB data that used different embedding dimensions:
```bash
rm -rf chroma_db/
```
Then restart the server. This happens when switching embedding models.

## Performance Considerations

- **Local embeddings**: ~50-100ms per message on first use (then cached)
- **Vector search**: ~10-50ms for similarity search
- **Claude API**: ~1-3s for response generation
- **OpenAI gpt-image-1**: ~3-5s per image (generates 3 images per design)
- **Total response time**:
  - Text only: ~2-4s
  - With images: ~12-18s (for 3 images)

## Future Enhancements

- Multi-user authentication and authorization
- Additional image models (DALL-E 3, Flux, Stable Diffusion)
- Export designs to PDF/mood boards
- Collaborative design sessions
- Budget tracking and shopping list integration
- 3D room visualization
- Mobile app (React Native)
- Voice interface

## License

This project is created for the Affinity Labs coding challenge.

## Contact

For questions or support regarding this implementation, please reach out through the appropriate channels.

---

**Built with ❤️ using Claude 4.5 Sonnet, ChromaDB, HuggingFace, and OpenAI**
