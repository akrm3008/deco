# Interior Design Agent Memory System

An AI-powered interior design assistant with persistent memory across sessions. Built for the Affinity Labs Senior Software Engineer challenge.

## Features

- **Persistent Memory**: Remembers user preferences, past designs, and conversations across sessions spanning days or weeks
- **Semantic Search**: Uses vector embeddings (ChromaDB + LlamaIndex) to retrieve relevant context from past conversations
- **Preference Learning**: Automatically learns and strengthens user preferences (style, warmth, complexity) based on selections and feedback
- **Design Version Tracking**: Maintains hierarchical design history with parent-child relationships
- **Cross-Room Consistency**: Applies learned preferences across different rooms ("design my living room like my bedroom")
- **Real-time Chat**: Interactive web interface with instant design feedback

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Vector Database**: ChromaDB (local, zero-setup)
- **Memory/RAG**: LlamaIndex
- **LLM**: Claude 4.5 Sonnet (Anthropic API)
- **Embeddings**: Voyage AI or OpenAI
- **Frontend**: HTML, CSS, JavaScript with HTMX
- **Image Generation**: Flexible module (placeholder, GPT-Image-1.5, or custom)

## Quick Start

### 1. Prerequisites

- Python 3.11 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))
- Voyage AI API key (recommended) or OpenAI API key for embeddings

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
VOYAGE_API_KEY=your_voyage_key_here  # or OPENAI_API_KEY

# Optional (for image generation)
IMAGE_GENERATOR=placeholder  # Start with placeholder
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
│   │   ├── vector_store.py     # ChromaDB setup
│   │   ├── retriever.py        # Hybrid search retriever
│   │   ├── learner.py          # Preference learning
│   │   └── storage.py          # JSON/SQLite storage
│   ├── agent/
│   │   ├── design_agent.py     # Main agent logic
│   │   ├── image_generator.py  # Image generation module
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

### 1. Vector Storage (ChromaDB)
- Stores all conversation messages with embeddings
- Enables semantic search for relevant context
- Metadata filtering by user, room, timestamp

### 2. Structured Storage (JSON)
- Rooms, design versions, images
- User preferences with confidence scores
- Design hierarchy tracking

### 3. Hybrid Retrieval
- **Vector similarity** (70%): Semantic matching via embeddings
- **Recency boosting** (30%): Exponential decay over time
- **Metadata filtering**: By user_id, room_id

### 4. Preference Learning
- **Implicit**: Detects keywords in conversation (+0.1 confidence)
- **Explicit selection**: User picks a design (+0.3 confidence)
- **Feedback**: Positive/negative feedback (±0.2 confidence)
- **Time decay**: 5% confidence reduction per week

## Configuration Options

### Embedding Providers

**Voyage AI** (Recommended):
```env
EMBEDDING_PROVIDER=voyage
VOYAGE_API_KEY=your_key
EMBEDDING_MODEL=voyage-3
EMBEDDING_DIMENSION=1024
```

**OpenAI**:
```env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_key
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

### Image Generation

**Placeholder** (Default):
```env
IMAGE_GENERATOR=placeholder
```

**Custom API** (GPT-Image-1.5):
```env
IMAGE_GENERATOR=gpt-image-1.5
IMAGE_API_KEY=your_key
IMAGE_ENDPOINT=https://api.example.com/generate
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

### Issue: "Failed to import chromadb"
**Solution**: Reinstall dependencies: `pip install -r requirements.txt`

### Issue: No embeddings being generated
**Solution**: Check that VOYAGE_API_KEY or OPENAI_API_KEY is set correctly

### Issue: Memory not persisting across restarts
**Solution**: Check that `./chroma_db` and `./data` directories exist and have write permissions

## Performance Considerations

- **Embedding generation**: ~100-200ms per message (cached by ChromaDB)
- **Vector search**: ~10-50ms for similarity search
- **Claude API**: ~1-3s for response generation
- **Total response time**: ~2-4s end-to-end

## Future Enhancements

- Multi-user authentication and authorization
- Real AI image generation (DALL-E, Flux, Stable Diffusion)
- Export designs to PDF/mood boards
- Collaborative design sessions
- Budget tracking and shopping list integration
- Mobile app (React Native)
- Voice interface

## License

This project is created for the Affinity Labs coding challenge.

## Contact

For questions or support regarding this implementation, please reach out through the appropriate channels.

---

**Built with ❤️ using Claude 4.5 Sonnet, LlamaIndex, and ChromaDB**
