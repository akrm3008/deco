# Interior Design Agent - Technical Design Document

**Version:** 1.0
**Date:** January 2026
**Focus:** AI-powered conversational interior design with multi-modal preference learning

---

## 1. System Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Chat Input   │  │ Design View  │  │ Preference Dashboard │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────────────┘  │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   FastAPI Server  │
                    │   (Backend API)   │
                    └────────┬──────────┘
                             │
          ┏━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━┓
          ▼                  ▼                  ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │  Claude  │      │  Memory  │      │  Image   │
    │  Agent   │◄────►│  System  │◄────►│Generator │
    └────┬─────┘      └────┬─────┘      └────┬─────┘
         │                 │                  │
         │            ┌────┴─────┐            │
         │            ▼          ▼            │
         │      ┌──────────┐ ┌──────────┐    │
         │      │ChromaDB  │ │Supabase  │    │
         │      │(Vectors) │ │(Postgres)│    │
         │      └──────────┘ └────┬─────┘    │
         │                        │          │
         └────────────────────────┴──────────┘
                                  │
                            ┌─────▼─────┐
                            │ Supabase  │
                            │  Storage  │
                            │ (Images)  │
                            └───────────┘
```

### Data Flow: Message Processing

```
User Message → FastAPI → DesignAgent
                            │
                            ├─→ Memory.search_conversations() → ChromaDB
                            │   (Semantic search for context)
                            │
                            ├─→ Storage.get_user_preferences() → Supabase
                            │   (Load user preferences)
                            │
                            ├─→ Storage.get_selected_designs() → Supabase
                            │   (Load previous selections)
                            │
                            ├─→ Claude API (Sonnet -4.5)
                            │   Context: [History + Preferences + Selections]
                            │   Response: Design description + metadata
                            │
                            ├─→ ImageGenerator.generate() → Gemini API
                            │   Input: Description + Style + Reference
                            │   Output: 3 design variations
                            │
                            └─→ Storage.save_design_version() → Supabase
                                Storage.save_design_images() → Supabase
                                Memory.store() → ChromaDB

Response → User (Design + Images + Select/Reject UI)
```

### Data Flow: Design Selection & Preference Learning

```
User Selects Design → FastAPI → DesignAgent.select_design()
                                      │
                                      ├─→ Storage.mark_selected() → Supabase
                                      │   (Update design_versions & images)
                                      │
                                      └─→ [ASYNC] _learn_preferences_background()
                                            │
                                            ├─→ [TEXT] Memory.learn_from_design_selection()
                                            │   ├─→ Learner.extract_preferences_from_text()
                                            │   │   (Keyword matching: style, color, material)
                                            │   └─→ Storage.update_preference() → Supabase
                                            │       (Confidence delta: +0.3)
                                            │
                                            └─→ [IMAGE] Memory.learn_from_selected_image()
                                                ├─→ Download image from Supabase Storage
                                                ├─→ ImageAnalyzer.analyze_image()
                                                │   ├─→ Color Palette (K-means clustering)
                                                │   ├─→ Material Detection (CLIP zero-shot)
                                                │   ├─→ Style Detection (CLIP zero-shot)
                                                │   ├─→ Warmth Analysis (color temperature)
                                                │   └─→ Complexity Estimation (edge density)
                                                └─→ Storage.update_preference() → Supabase
                                                    (Confidence deltas: 0.05-0.25)

Instant Response → User ("Design selected!")
[Background learning completes in 5-7 seconds]
```

---

## 2. Data Models & Schema Design

### Core Entities

```
User
├── id (UUID, PK)
├── email (TEXT, UNIQUE)
├── username (TEXT)
├── password_hash (TEXT)
└── created_at (TIMESTAMP)

Room
├── id (UUID, PK)
├── user_id (UUID, FK → users.id)
├── name (TEXT)
├── room_type (ENUM: living_room, bedroom, kitchen, etc.)
└── created_at (TIMESTAMP)

DesignVersion
├── id (UUID, PK)
├── room_id (UUID, FK → rooms.id)
├── version_number (INTEGER)
├── description (TEXT)
├── selected (BOOLEAN)
├── rejected (BOOLEAN)
├── feedback (TEXT, nullable)
└── created_at (TIMESTAMP)

DesignImage
├── id (UUID, PK)
├── version_id (UUID, FK → design_versions.id)
├── image_url (TEXT)
├── style_modifier (TEXT, nullable)
├── selected (BOOLEAN)
└── created_at (TIMESTAMP)

UserPreference
├── id (UUID, PK)
├── user_id (UUID, FK → users.id)
├── preference_type (ENUM: style, color, material, warmth, complexity)
├── preference_value (TEXT)
├── confidence (FLOAT, 0.0-1.0)
├── source_room_id (UUID, nullable)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)
```

### Schema Design Rationale

**Normalized Relational Design:**
- Each design version can have multiple images (1:N)
- Users can have multiple rooms (1:N)
- Preferences are versioned with timestamps for evolution tracking
- Separate `selected` flags at both version and image level for granularity

**Indexing Strategy:**
```sql
CREATE INDEX idx_user_prefs ON user_preferences(user_id, confidence DESC);
CREATE INDEX idx_room_versions ON design_versions(room_id, version_number DESC);
CREATE INDEX idx_version_images ON design_images(version_id);
CREATE INDEX idx_users_email ON users(email);
```

**Confidence as First-Class Property:**
- Preference confidence stored as float (0.0-1.0)
- Enables weighted context building
- Supports time-based decay (not yet implemented)
- Allows ranking by certainty

---

## 3. Retrieval Strategy

### Multi-Tier Context Retrieval

#### Tier 1: Semantic Search (ChromaDB)
**Purpose:** Find relevant conversation history and design context

```python
# Query ChromaDB with user message
results = chromadb.query(
    query_texts=[user_message],
    n_results=5,
    where={"user_id": user_id, "session_id": session_id}
)
```

**Why ChromaDB?**
- Local embedding model (all-MiniLM-L6-v2)
- No external API calls
- Fast cosine similarity search
- Automatic persistence

**Trade-off:** Limited to text embeddings. Cannot search image content directly.

#### Tier 2: Structured Preference Retrieval (Supabase)
**Purpose:** Load explicit user preferences by confidence

```sql
SELECT * FROM user_preferences
WHERE user_id = $1
ORDER BY confidence DESC
LIMIT 10;
```

**Why SQL?**
- Precise filtering by confidence threshold
- Easy aggregation (e.g., average confidence by type)
- Supports complex queries (e.g., preferences from specific rooms)

**Trade-off:** Preferences are explicit tags, not nuanced embeddings.

#### Tier 3: Selected Design Retrieval (Supabase)
**Purpose:** Show user what they previously liked

```sql
SELECT dv.*, di.image_url
FROM design_versions dv
JOIN design_images di ON dv.id = di.version_id
WHERE dv.room_id IN (
    SELECT id FROM rooms WHERE user_id = $1
)
AND (dv.selected = true OR di.selected = true)
ORDER BY dv.created_at DESC
LIMIT 5;
```

**Why Join?**
- Images provide visual reference for Claude's context
- User sees consistency across sessions
- Enables image-to-image generation

#### Tier 4: Reference Image Retrieval
**Purpose:** Enable iteration and cross-room inspiration

**Case 1: Room Iteration**
```python
# Get most recent selected image from same room
selected_images = storage.get_selected_images(room_id)
if selected_images:
    reference_url = selected_images[0].image_url
```

**Case 2: Cross-Room Inspiration**
```python
# Parse user message for room references
# "design bedroom like living room"
if "like living room" in user_message:
    living_room = storage.get_room_by_name(user_id, "living room")
    reference_url = get_selected_image(living_room.id)
```

**Why Supabase Storage URLs?**
- Public URLs enable Gemini API to download images
- No need to proxy image data through backend
- Direct integration with image-to-image generation

---

## 4. Preference Learning Approach

### Hybrid Multi-Modal Learning

```
┌─────────────────────────────────────────────────────┐
│          PREFERENCE LEARNING PIPELINE               │
└─────────────────────────────────────────────────────┘

INPUT: User selects Design Version 3, Image 2

┌──────────────────┐          ┌──────────────────┐
│  TEXT LEARNING   │          │  IMAGE LEARNING  │
│   (Immediate)    │          │  (5-7 seconds)   │
└────────┬─────────┘          └────────┬─────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌──────────────────────┐
│ Keyword Extract │          │  Download Image      │
│ from Description│          │  from Supabase       │
└────────┬────────┘          └──────────┬───────────┘
         │                              │
         │                              ▼
         │                    ┌──────────────────────┐
         │                    │  K-means Clustering  │
         │                    │  (Color Palette)     │
         │                    └──────────┬───────────┘
         │                              │
         │                              ▼
         │                    ┌──────────────────────┐
         │                    │  CLIP Zero-Shot      │
         │                    │  Classification:     │
         │                    │  • Materials         │
         │                    │  • Visual Styles     │
         │                    └──────────┬───────────┘
         │                              │
         └──────────────┬───────────────┘
                        ▼
            ┌───────────────────────┐
            │  Update Preferences   │
            │  in Supabase:         │
            │  • style=modern +0.3  │
            │  • color=white +0.10  │
            │  • material=wood +0.15│
            └───────────────────────┘
```

### Text-Based Learning (Existing)

**Keywords Extraction:**
```python
STYLE_KEYWORDS = {
    "modern": ["modern", "contemporary", "minimalist"],
    "traditional": ["traditional", "classic", "elegant"],
    ...
}

MATERIAL_KEYWORDS = {
    "wood": ["wood", "wooden", "oak", "walnut"],
    "metal": ["metal", "steel", "brass"],
    ...
}
```

**Confidence Deltas:**
- Selection: `+0.3` (strong signal)
- Rejection: `-0.2` (negative signal)
- Mention in message: `+0.1` (weak signal)

**Strength:** Fast, no external dependencies, explicit
**Weakness:** Limited to keywords, misses visual nuance

### Image-Based Learning (New)

#### A. Color Palette Extraction
**Method:** K-means clustering on RGB pixel values
**Output:** Top 5 colors with percentages

```python
colors = [
    ("white", "#f5f5f5", 0.38),  # 38% of image
    ("gray", "#8a8a8a", 0.22),
    ("brown", "#8b7355", 0.18),
]
# Confidence: 0.25 * percentage
# white → +0.095, gray → +0.055, brown → +0.045
```

**Strength:** Objective, captures dominant visual tones
**Weakness:** Doesn't understand semantic color (e.g., "accent wall")

#### B. Material Detection
**Method:** CLIP zero-shot classification with material labels
**Model:** `openai/clip-vit-base-patch32`

```python
material_labels = [
    "wood furniture", "metal fixtures", "glass surfaces",
    "fabric upholstery", "leather furniture", ...
]
# CLIP outputs probability distribution
materials = [
    ("wood", 0.72),    # 72% confident
    ("fabric", 0.48),  # 48% confident
]
# Confidence: 0.2 * detection_confidence
# wood → +0.144, fabric → +0.096
```

**Strength:** Visual pattern recognition, handles complex textures
**Weakness:** Limited by CLIP's training data, may confuse similar materials

#### C. Style Detection
**Method:** CLIP zero-shot classification with style labels

```python
style_labels = [
    "modern minimalist interior", "traditional classic interior",
    "rustic farmhouse interior", "industrial urban interior", ...
]
# Visual style classification
styles = [
    ("modern", 0.84),        # 84% confident
    ("scandinavian", 0.35),  # 35% confident
]
# Confidence: 0.25 * detection_confidence
# modern → +0.21, scandinavian → +0.0875
```

**Strength:** Captures visual style beyond keywords
**Weakness:** Style categories overlap (e.g., modern + scandinavian)

#### D. Warmth & Complexity
**Warmth:** Derived from color palette temperature
**Complexity:** Derived from edge detection + color diversity

```python
# Warmth scoring
warm_colors = ["red", "orange", "yellow", "brown"]
cool_colors = ["blue", "green", "cyan", "purple"]
warmth = (warm_score - cool_score) / total_colors

# Complexity scoring
edge_density = cv2.Canny(image).mean()
color_diversity = len(unique_colors) / total_pixels
complexity = (edge_density + color_diversity) / 2
```

**Strength:** Quantitative metrics, reproducible
**Weakness:** Heuristic-based, not learned from design theory

### Preference Update Strategy

**Additive Confidence Model:**
```python
new_confidence = min(1.0, current_confidence + delta)
```

**Why not multiplicative?**
- Additive allows preferences to grow from zero
- Easier to reason about confidence contributions
- Transparent credit assignment

**Why cap at 1.0?**
- Prevents runaway confidence
- Forces competition between similar preferences
- Bounded value for context weighting

**Time Decay (Future):**
```python
# Not yet implemented
decayed_confidence = current_confidence * (0.95 ** days_since_update)
```

---

## 5. Key Technology Choices & Trade-offs

### 1. **Claude API (Sonnet 4.5) as Orchestrator**

**Choice:** Use Claude for conversation understanding, design reasoning, and generation

**Why?**
- Excellent at nuanced conversation (understanding "same vibe as living room")
- Strong reasoning for design decisions
- Can incorporate complex context (history + preferences + images)
- Long context window (200K tokens)

**Trade-offs:**
- Cost: ~$3 per 1M input tokens, $15 per 1M output tokens
- Latency: ~2-5 seconds per response
- External dependency (API downtime risk)

**Alternatives Considered:**
- GPT-4: Similar capability, higher cost
- Open-source LLMs (Llama, Mistral): Lower quality reasoning, requires hosting

**Decision:** Claude's reasoning quality justifies cost for design domain

---

### 2. **Google Gemini 2.5 Flash for Image Generation**

**Choice:** Use Gemini for both text-to-image and image-to-image generation

**Why?**
- Native image-to-image editing (not just text-to-image)
- Fast (5-10 seconds per image)
- Accepts base64 image input for reference
- Response modalities: `["IMAGE"]` for direct generation

**Trade-offs:**
- Rate limits on free tier (15 RPM)
- Quality variable compared to specialized models (DALL-E, Midjourney)
- API still in beta (v1beta)

**Alternatives Considered:**
- DALL-E 3: No native image-to-image editing
- Stable Diffusion: Requires hosting GPU, complex setup
- Midjourney: No API access

**Decision:** Gemini's image-to-image is critical for iteration + cross-room inspiration

---

### 3. **Supabase (PostgreSQL) for Primary Storage**

**Choice:** Use Supabase for users, rooms, designs, preferences

**Why?**
- Strong consistency (ACID transactions)
- Complex queries (joins, aggregations, filtering)
- Row-level security (RLS) for multi-tenancy
- Built-in auth (though we use custom)
- Generous free tier (500MB, unlimited API requests)

**Trade-offs:**
- Requires internet connection (not fully local)
- Schema migrations need SQL knowledge
- Query latency (~50-100ms) vs in-memory

**Alternatives Considered:**
- SQLite: Local, but poor concurrency
- MongoDB: Document model doesn't fit relational data
- JSON files: Used initially, but unmaintainable for multi-user

**Decision:** Relational data + scale + free tier = Supabase wins

---

### 4. **ChromaDB for Semantic Search**

**Choice:** Use ChromaDB for conversation history embeddings

**Why?**
- Local (no external API)
- Automatic embedding with sentence-transformers
- Persistent storage (survives restarts)
- Simple API (`collection.add()`, `collection.query()`)
- Lightweight (~100MB)

**Trade-offs:**
- Limited to text embeddings (no image search)
- Embedding model fixed (all-MiniLM-L6-v2, 384 dimensions)
- No distributed setup (single-machine only)

**Alternatives Considered:**
- Pinecone: Cloud-based, costs money, external dependency
- Weaviate: More complex setup, overkill for our scale
- Postgres pgvector: Requires managing embeddings manually

**Decision:** ChromaDB's simplicity + local-first aligns with project philosophy

---

### 5. **CLIP for Image Analysis (Local Model)**

**Choice:** Use `openai/clip-vit-base-patch32` for zero-shot classification

**Why?**
- Pre-trained on 400M image-text pairs
- Zero-shot (no training needed for new categories)
- 350MB model, runs on CPU
- Handles both material and style detection

**Trade-offs:**
- CPU inference slow (~2-3 seconds per image)
- Model not fine-tuned for interior design
- Cannot detect specific furniture types (e.g., "mid-century sofa")

**Alternatives Considered:**
- Cloud Vision APIs (Google, AWS): Cost + external dependency
- Custom CNN: Requires labeled training data
- GPT-4 Vision: Expensive ($0.01 per image), latency

**Decision:** CLIP's zero-shot + local deployment outweighs speed concerns

---

### 6. **Async Background Learning**

**Choice:** Run preference learning asynchronously after responding to user

**Why?**
- User experience: Selection feels instant (~0.1s)
- Non-critical path: Learning doesn't block next action
- Parallel processing: Text + image learning happen concurrently

**Trade-offs:**
- No error feedback to user if learning fails
- Preferences may not be available for 5-7 seconds
- Harder to debug (async errors in logs)

**Alternatives Considered:**
- Synchronous learning: 5-8 second delay, poor UX
- Queue-based (Celery): Over-engineered for single-user demo

**Decision:** UX responsiveness > guaranteed immediate consistency

---

### 7. **Supabase Storage for Images**

**Choice:** Store generated images in Supabase Storage bucket

**Why?**
- Public URLs enable Gemini to download for image-to-image
- No need to proxy images through backend
- CDN-backed (fast access)
- Integrated with Supabase database

**Trade-offs:**
- 1GB free tier limit (25-50 images with 20-30MB each)
- Vendor lock-in (URLs tied to Supabase domain)
- Requires internet for image access

**Alternatives Considered:**
- Local filesystem: Can't be accessed by Gemini API
- S3: Requires separate AWS account setup
- Base64 in database: Bloats database, poor performance

**Decision:** Gemini integration requirement forces cloud storage

---

### 8. **Image-Dominant Editing (Minimal Text)**

**Choice:** When reference image exists, use minimal text prompt

**Why?**
- Image-to-image works best when visual reference dominates
- Text preferences can conflict with reference image style
- Users expect "same vibe" = visual consistency, not text interpretation

**Implementation:**
```python
if reference_image_url:
    prompt = f"Interior design for {room_type} inspired by reference image"
else:
    prompt = f"{full_description_with_preferences} - variation {i}"
```

**Trade-offs:**
- Less control over specific changes (e.g., "make it brighter")
- Gemini may ignore small text hints
- Harder to add explicit constraints

**Alternatives Considered:**
- Full text prompt + image: Gemini confused by conflicting signals
- No text, just image: Gemini needs some direction

**Decision:** Visual consistency > text control for "same vibe" use case

---

## Summary: Core Design Philosophy

1. **Hybrid Intelligence:** Combine LLM reasoning (Claude) with specialized models (Gemini, CLIP)
2. **Multi-Modal Learning:** Text keywords + visual analysis > text alone
3. **Async UX:** Non-blocking background tasks for instant responsiveness
4. **Confidence-Based Context:** Weighted preferences guide generation, not hard rules
5. **Image-First Iteration:** Visual references dominate over text for consistency
6. **Local-First Where Possible:** ChromaDB + CLIP run locally, reduce API dependencies
7. **Relational + Vector Hybrid:** Postgres for structured data, ChromaDB for semantic search

**Trade-off Summary:**
- **Cost vs Quality:** Chose Claude/Gemini APIs over open-source for better results
- **Speed vs Accuracy:** Async learning for UX, CLIP on CPU for simplicity
- **Flexibility vs Simplicity:** Relational schema over document store for query power
- **Local vs Cloud:** Hybrid approach (ChromaDB local, Supabase cloud) for best of both

---

**End of Technical Design Document**
