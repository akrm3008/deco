# Interior Design Agent with Visual Preference Learning

An AI-powered interior design assistant with persistent memory, visual preference learning, and image-to-image generation capabilities.

## 🌟 Features

### Core Capabilities
- **Visual Preference Learning**: Learns from both text AND images using CLIP (OpenAI's vision model)
  - Extracts color palettes from selected designs
  - Detects materials (wood, metal, glass, fabric, etc.)
  - Identifies visual styles (modern, traditional, rustic, scandinavian, etc.)
  - Analyzes warmth and complexity from images

- **Image-to-Image Generation**: Create designs inspired by existing rooms
  - Iterate on designs with visual consistency
  - Cross-room inspiration ("design bedroom like my living room")
  - Reference images prioritized over text for visual coherence

- **Persistent Memory**: Remembers preferences, designs, and conversations across sessions
  - Semantic search using ChromaDB with local embeddings
  - Supabase PostgreSQL for structured data storage
  - Preference confidence scores with time decay

- **User Authentication**: Secure login with username/password
  - Each user has their own rooms, designs, and preferences
  - Bcrypt password hashing

- **Real-time Chat Interface**: Interactive web UI with instant feedback
  - Image modal for enlarged design viewing
  - Design selection and rejection with preference learning
  - Room-based conversation history

### AI Image Generation
- **Google Gemini 2.5 Flash Image**: High-quality interior design images
- **Text-to-Image**: Generate designs from descriptions
- **Image-to-Image**: Edit and iterate on existing designs
- **Cross-Room Inspiration**: Use one room's visual style for another

## 🏗️ Architecture Overview

### Technology Stack

**Backend**
- Python 3.11+, FastAPI
- Supabase (PostgreSQL) for structured data
- ChromaDB (local vector database)
- HuggingFace sentence-transformers for embeddings
- Claude 4.5 Sonnet (Anthropic) for conversational AI
- Google Gemini 2.5 Flash Image for image generation
- CLIP (ViT-Base-Patch32) for image analysis

**Frontend**
- HTML, CSS, JavaScript
- Async operations for instant UI feedback

**Storage**
- Supabase PostgreSQL: users, rooms, designs, preferences
- Supabase Storage: generated design images (public URLs)
- ChromaDB: conversation embeddings for semantic search

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  (HTML/CSS/JS - Chat UI, Image Gallery, Preferences)       │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP/REST
┌────────────────▼────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │             Design Agent (Orchestrator)               │  │
│  └──┬────────────────┬────────────────┬─────────────┬───┘  │
│     │                │                │             │       │
│  ┌──▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐  ┌───▼────┐ │
│  │ Memory  │  │   Image   │  │   Image     │  │ Auth   │ │
│  │ Manager │  │ Generator │  │  Analyzer   │  │        │ │
│  │         │  │ (Gemini)  │  │   (CLIP)    │  │        │ │
│  └──┬──────┘  └───────────┘  └──────┬──────┘  └────────┘ │
│     │                                │                      │
└─────┼────────────────────────────────┼──────────────────────┘
      │                                │
┌─────▼────────┐  ┌──────────────┐   │   ┌──────────────────┐
│  ChromaDB    │  │  Supabase    │   └───│   CLIP Model     │
│  (Vectors)   │  │ (PostgreSQL) │       │   (Local/CPU)    │
│              │  │   + Storage  │       │                  │
└──────────────┘  └──────────────┘       └──────────────────┘
```

### Data Flow

**1. User Sends Message**
```
User → Frontend → API → Design Agent
                           ↓
                    Memory Manager
                    ├─ Store in ChromaDB (embeddings)
                    ├─ Retrieve relevant context
                    └─ Get user preferences
                           ↓
                    Claude API (with context + preferences)
                           ↓
                    Design Description
                           ↓
                    Image Generator (Gemini)
                    ├─ Text-to-Image (new designs)
                    └─ Image-to-Image (with reference)
                           ↓
                    Supabase Storage → Public URLs
                           ↓
                    Frontend (display images)
```

**2. User Selects Design (Async Preference Learning)**
```
User clicks "Select" → API marks as selected
                       ↓
                    INSTANT UI feedback
                       ↓
                    Background tasks (non-blocking):
                    ├─ Text-based learning (keywords)
                    ├─ Download image from Supabase
                    ├─ CLIP image analysis
                    │   ├─ Color palette extraction
                    │   ├─ Material detection
                    │   ├─ Style classification
                    │   └─ Warmth/complexity analysis
                    └─ Update preferences in database
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))
- Google Gemini API key ([get one here](https://aistudio.google.com/apikey))
- Supabase account ([create one here](https://supabase.com/))

### Installation

```bash
# Clone the repository
cd deco

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (includes CLIP, transformers, torch)
pip install -r requirements.txt
```

### Configuration

1. **Set up Supabase Database**

Execute this SQL in your Supabase SQL Editor:

```sql
-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    username TEXT,
    password_hash TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create rooms table
CREATE TABLE rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name TEXT NOT NULL,
    room_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create design_versions table
CREATE TABLE design_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID REFERENCES rooms(id),
    version_number INT NOT NULL,
    description TEXT,
    parent_version_id UUID,
    selected BOOLEAN DEFAULT FALSE,
    rejected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create design_images table
CREATE TABLE design_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    design_version_id UUID REFERENCES design_versions(id),
    image_url TEXT NOT NULL,
    prompt TEXT,
    selected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create user_preferences table
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    preference_type TEXT NOT NULL,
    preference_value TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    source_room_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_rooms_user ON rooms(user_id);
CREATE INDEX idx_design_versions_room ON design_versions(room_id);
CREATE INDEX idx_design_images_version ON design_images(design_version_id);
CREATE INDEX idx_preferences_user ON user_preferences(user_id, confidence DESC);
CREATE INDEX idx_users_email ON users(email);
```

2. **Create Supabase Storage Bucket**

In Supabase dashboard:
- Go to **Storage**
- Create new bucket: `design-images`
- Make it **public**
- Add RLS policies:

```sql
-- Allow public inserts
CREATE POLICY "Allow public uploads"
ON storage.objects
FOR INSERT
TO public
WITH CHECK (bucket_id = 'design-images');

-- Allow public reads
CREATE POLICY "Allow public reads"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'design-images');
```

3. **Configure Environment Variables**

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env`:

```env
# Anthropic API (Primary LLM) - REQUIRED
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Google Gemini (Image Generation - Recommended)
GEMINI_API_KEY=your_gemini_api_key_here

# Supabase (Database and Storage) - REQUIRED
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_BUCKET=design-images

# Local HuggingFace Embeddings (no API key required)
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384

# Image Generation
IMAGE_GENERATOR=gemini  # Options: gemini, gpt-5, placeholder

# Image Storage
IMAGE_STORAGE=supabase  # Required for image editing features

# App Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
CHROMA_DB_PATH=./chroma_db
DATA_STORAGE_PATH=./data
```

### Run the Application

```bash
# Start the FastAPI server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Open your browser
# Navigate to: http://localhost:8000
```

## 🎮 How to Run Demo

### First Time Setup

1. **Start the server** (see above)
2. **Open** http://localhost:8000
3. **Register** a new account with email/username/password
4. You'll be redirected to the main chat interface

### Demo Scenario 1: Create Initial Design

```
You: "Design a modern living room"
Agent: [Generates 3 design variations with images]

Click "Select This Design" on your favorite option
→ Instant UI feedback
→ Background: Learns style, colors, materials from image
```

### Demo Scenario 2: Iterate on Design

```
You: "Make it warmer and add more plants"
Agent: [Uses previous design as visual reference]
      [Generates new variations maintaining style]

→ Reference image guides generation
→ Minimal text interference
```

### Demo Scenario 3: Cross-Room Inspiration

```
You: "Design a bedroom with the same vibe as my living room"
Agent: [Pulls living room's selected image as reference]
      [Generates bedroom with matching colors/materials/style]

→ Visual consistency across rooms
→ Image-to-image generation
```

### Demo Scenario 4: Check Learned Preferences

Look at the sidebar under **"Your Preferences"**:
```
style: modern 85%
color: white 70%
color: gray 45%
material: wood 75%
material: fabric 50%
warmth: neutral 60%
```

These are learned from your selections!

## 🧪 How to Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_memory.py -v
```

## 📁 Project Structure

```
deco/
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration management
│   ├── models/
│   │   ├── schemas.py          # Pydantic models
│   │   └── types.py            # Enums (RoomType, PreferenceType, etc.)
│   ├── memory/
│   │   ├── manager.py          # Memory orchestration
│   │   ├── chroma_store.py     # ChromaDB wrapper with local embeddings
│   │   ├── learner.py          # Text-based preference extraction
│   │   ├── image_analyzer.py   # CLIP-based image analysis (NEW)
│   │   └── storage.py          # Supabase database operations
│   ├── agent/
│   │   ├── design_agent.py     # Main agent logic
│   │   ├── image_generator.py  # Gemini image generation (NEW)
│   │   ├── image_storage.py    # Supabase/local image storage
│   │   └── prompts.py          # System prompts
│   ├── api/
│   │   ├── routes.py           # Main API endpoints
│   │   └── auth.py             # Authentication endpoints (NEW)
│   └── utils/
│       └── auth.py             # Password hashing (NEW)
├── frontend/
│   ├── static/
│   │   ├── css/styles.css      # Responsive design styles
│   │   ├── js/
│   │   │   ├── app.js          # Main application logic
│   │   │   └── login.js        # Authentication UI (NEW)
│   │   └── images/             # Local image storage (dev only)
│   └── templates/
│       ├── index.html          # Main chat interface
│       └── login.html          # Login/register page (NEW)
├── requirements.txt            # Python dependencies
├── .env.example                # Environment configuration template
├── IMAGE_PREFERENCE_LEARNING.md  # Technical documentation (NEW)
└── README.md
```

## 🎯 Key Design Decisions

### 1. Hybrid Preference Learning (Text + Visual)

**Decision**: Use both keyword extraction AND CLIP image analysis

**Rationale**:
- Text-only learning misses actual visual preferences
- Users may select designs without mentioning specific colors/materials
- CLIP provides objective visual feature extraction
- Combination captures both stated and revealed preferences

**Implementation**:
- Text learning: Fast, keyword-based (+0.1 to +0.3 confidence)
- Image learning: Slower, CLIP-based, weighted by detection confidence
- Both run asynchronously to avoid blocking user interactions

### 2. Image-Dominant Editing (vs Text-Dominant)

**Decision**: When reference image exists, minimize text prompt

**Rationale**:
- Text descriptions compete with visual references in image-to-image models
- Users want visual consistency, not new interpretations
- "Design bedroom like living room" should strongly match visually

**Implementation**:
```python
# With reference: "Interior design for bedroom inspired by reference image"
# Without reference: "Modern minimalist bedroom with white walls..." (full description)
```

### 3. Supabase for Images (vs Local Filesystem)

**Decision**: Store all images in Supabase Storage, not local files

**Rationale**:
- Public URLs required for image-to-image generation
- CLIP can't download from relative paths (`/static/images/...`)
- Scalable, CDN-backed, production-ready
- No manual file management

### 4. Async Preference Learning

**Decision**: Run ALL preference learning in background after selection

**Rationale**:
- CLIP analysis takes 5-7 seconds
- Users expect instant feedback when clicking "Select"
- Database writes are I/O bound
- No reason to block the UI

**Result**: Selection response time: 0.1s (was 5-8s)

### 5. Supabase PostgreSQL (vs JSON Files)

**Decision**: Replace JSON storage with Supabase database

**Rationale**:
- Relational data (users → rooms → designs → images)
- ACID transactions for data consistency
- Easier querying and filtering
- Multi-user support with authentication
- Production-ready scalability

### 6. Local CLIP Model (vs API)

**Decision**: Run CLIP model locally on CPU, not via API

**Rationale**:
- No per-request costs
- Runs on any machine (no GPU required)
- Fast enough for background processing (~2-4s)
- One-time ~350MB download
- Privacy: images never sent to external services

### 7. Confidence-Based Preference Scoring

**Decision**: Weighted confidence scores with time decay

**Rationale**:
- Not all signals are equal (selection > mention)
- Preferences evolve over time
- Allows graceful forgetting of old preferences
- Probabilistic rather than binary

**Scoring**:
- Explicit selection: +0.3
- Positive feedback: +0.2
- Implicit mention: +0.1
- Rejection: -0.2
- Time decay: 5% per week

### 8. Minimal Text Prompts for Iteration

**Decision**: Use minimal prompts when iterating/cross-referencing

**Rationale**:
- Detailed text descriptions override visual references
- "Same vibe as living room" should prioritize the image
- Gemini's image-to-image works best with simple guidance
- Let the model focus on visual consistency

## 📊 API Endpoints

### Authentication

```http
POST /api/auth/register
Body: { "email": str, "username": str, "password": str }
Response: { "id": str, "email": str, "username": str }

POST /api/auth/login
Body: { "email": str, "password": str }
Response: { "id": str, "email": str, "username": str }

GET /api/auth/user/{user_id}/data
Response: { "user": User, "rooms": [Room], "preferences": [Preference], "designs": {...} }
```

### Chat

```http
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
  "version_id": str,
  "images": [{"id": str, "url": str}]
}
```

### Design Operations

```http
GET /api/rooms/{user_id}
Response: { "rooms": [Room] }

GET /api/rooms/{room_id}/designs
Response: { "versions": [DesignVersion], "images": {...} }

POST /api/rooms/{room_id}/designs/{version_id}/select?user_id={user_id}&image_id={image_id}
Response: { "status": "success" }

POST /api/rooms/{room_id}/designs/{version_id}/reject?user_id={user_id}&feedback={text}
Response: { "status": "success" }
```

### Preferences

```http
GET /api/preferences/{user_id}
Response: { "preferences": [UserPreference] }
```

## ⚙️ Configuration Options

### Image Generation

**Google Gemini** (Recommended - supports text-to-image AND image editing):
```env
IMAGE_GENERATOR=gemini
GEMINI_API_KEY=your_gemini_api_key
```

**OpenAI GPT-5** (Text-to-image only, no editing):
```env
IMAGE_GENERATOR=gpt-5
OPENAI_API_KEY=your_openai_api_key
```

**Placeholder** (Development/testing):
```env
IMAGE_GENERATOR=placeholder
```

### Image Storage

**Supabase** (Recommended - required for image editing):
```env
IMAGE_STORAGE=supabase
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

**Local** (Development only - image editing won't work):
```env
IMAGE_STORAGE=local
```

### Embeddings (Local, No API Key Required)

**Default** (Recommended):
```env
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384
```

**Other options**:
- `all-MiniLM-L6-v2` (384 dimensions) - Faster
- `all-mpnet-base-v2` (768 dimensions) - More accurate

## 🔧 Development

### Clearing Data

```bash
# Clear ChromaDB embeddings
rm -rf chroma_db/

# Clear local data (if using local storage)
rm -rf data/

# Clear Supabase data (run in SQL editor)
DELETE FROM design_images;
DELETE FROM design_versions;
DELETE FROM user_preferences;
DELETE FROM rooms;
DELETE FROM users;
```

### Viewing Logs

```bash
# Check server logs
tail -f server.log

# Check for CLIP model loading
tail -f server.log | grep "CLIP"

# Check for image analysis
tail -f server.log | grep "Analyzing selected image"
```

### Debug Mode

```env
LOG_LEVEL=DEBUG
```

## 🐛 Troubleshooting

### Issue: "ANTHROPIC_API_KEY is required"
**Solution**: Add API key to `.env` file

### Issue: "GEMINI_API_KEY is required when IMAGE_GENERATOR=gemini"
**Solution**: Get Gemini API key from https://aistudio.google.com/apikey

### Issue: "Bucket not found" or 403 errors for images
**Solution**:
1. Create `design-images` bucket in Supabase Storage
2. Make it public
3. Add RLS policies (see Configuration section)

### Issue: Images not displaying from Supabase
**Solution**: Add SELECT policy for public reads (see Configuration)

### Issue: "Could not load CLIP model"
**Solution**:
- Model will auto-download on first use (~350MB)
- Ensure internet connection
- Check disk space
- If fails, image analysis will be skipped (color extraction still works)

### Issue: Selection is slow
**Solution**: Already optimized! Should be instant (~0.1s). Check:
- Frontend shows "Learning preferences..." immediately
- Background learning happens asynchronously
- Check browser console for errors

### Issue: "Embedding dimension 384 does not match collection dimensionality 1024"
**Solution**: Clear ChromaDB with different embedding dimensions:
```bash
rm -rf chroma_db/
```

### Issue: Cross-room inspiration not working
**Solution**:
1. Select a design in the source room first
2. Use phrases like "same vibe as", "like my", "inspired by"
3. Check logs for: `DEBUG: Detected cross-room reference`
4. Ensure Supabase storage is configured (not local)

## 📈 Performance

- **Selection Response**: ~0.1s (instant UI feedback)
- **Local Embeddings**: ~50-100ms per message
- **Vector Search**: ~10-50ms
- **Claude API**: ~1-3s per response
- **Gemini Image Generation**: ~5-10s per image (3 images)
- **CLIP Analysis**: ~5-7s (runs in background)
- **Total Design Generation**: ~20-30s for 3 images

## 🔐 Security

- Passwords hashed with bcrypt (salt + rounds)
- Supabase RLS policies for data access control
- No plaintext password storage
- HTTPS required in production
- Session management via localStorage (upgrade to JWT for production)

## 🚀 Deployment

1. Set `ENVIRONMENT=production` in `.env`
2. Use HTTPS (required for secure authentication)
3. Configure Supabase production instance
4. Consider adding:
   - Rate limiting
   - Request logging
   - Error monitoring (Sentry)
   - CDN for static assets

## 📚 Documentation

- **IMAGE_PREFERENCE_LEARNING.md**: Detailed technical documentation on CLIP-based preference learning
- **API Documentation**: Available at http://localhost:8000/docs (FastAPI auto-generated)

## 🎉 Recent Updates

### Latest (2026-01-11)
- Prioritize reference images over text in iteration and cross-room modes
- Minimal text prompts when using visual references
- Enhanced visual consistency for image-to-image generation

### v2.0 (2026-01-11)
- Added CLIP-based image analysis for preference learning
- Color palette extraction from selected designs
- Material detection (wood, metal, glass, fabric, etc.)
- Visual style classification
- Async preference learning (non-blocking)
- Instant selection feedback

### v1.5 (2026-01-10)
- Switched to Google Gemini for image generation
- Added image-to-image editing support
- Cross-room visual inspiration
- Supabase storage for images

### v1.0 (2026-01-08)
- Custom username/password authentication
- Supabase PostgreSQL database
- Image modal for enlarged viewing
- Multi-user support

## 📞 Support

For questions, issues, or feature requests, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ using Claude 4.5 Sonnet, Google Gemini, CLIP, ChromaDB, Supabase, and HuggingFace**
