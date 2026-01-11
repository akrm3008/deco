# Image-Based Preference Learning

## Overview

Enhanced preference learning system that combines **text analysis** and **visual image analysis** using CLIP (Contrastive Language-Image Pre-training) to learn user design preferences.

## New Preference Types

### Previously Available
- `STYLE` - modern, traditional, rustic, industrial, bohemian, scandinavian
- `WARMTH` - warm, cool, neutral
- `COMPLEXITY` - simple, moderate, complex

### Newly Added
- **`COLOR`** - Dominant color preferences (blue, green, gray, white, black, brown, red, yellow, orange, pink, purple)
- **`MATERIAL`** - Material preferences (wood, metal, glass, fabric, leather, stone, concrete, ceramic, carpet, velvet, linen, rattan)

## How It Works

### 1. Text-Based Learning (Existing)

**Trigger:** User sends messages or selects designs

**Method:** Keyword matching in text descriptions

**Example:**
```
User: "I want a modern living room with wooden furniture"
→ Extracts: style=modern (+0.1), material=wood (+0.1)
```

**Confidence Deltas:**
- Implicit mention in message: +0.1
- Selection of design: +0.3
- Rejection of design: -0.2

---

### 2. Image-Based Learning (NEW)

**Trigger:** User selects a design image

**Method:** Computer vision analysis using CLIP model

**Features Extracted:**

#### A. Color Palette Extraction
- Uses K-means clustering on image pixels
- Extracts 5 dominant colors with percentages
- Maps RGB values to color names (blue, green, gray, etc.)

```python
Example Output:
[
  ("white", "#f5f5f5", 0.35),  # 35% of image
  ("gray", "#8a8a8a", 0.25),   # 25% of image
  ("brown", "#8b7355", 0.20),  # 20% of image
]
→ Learns: color=white (+0.09), color=gray (+0.06), color=brown (+0.05)
```

#### B. Material Detection
- Zero-shot classification using CLIP
- Detects materials with confidence scores
- Categories: wood, metal, glass, fabric, leather, stone, marble, concrete, ceramic, carpet, hardwood, velvet, linen, rattan

```python
Example Output:
[
  ("wood", 0.72),    # 72% confident
  ("fabric", 0.48),  # 48% confident
  ("metal", 0.25),   # 25% confident
]
→ Learns: material=wood (+0.14), material=fabric (+0.10)
```

#### C. Visual Style Detection
- Zero-shot classification using CLIP
- Detects design styles from visual appearance
- Categories: modern minimalist, traditional classic, rustic farmhouse, industrial urban, bohemian eclectic, scandinavian nordic, contemporary, vintage, mid-century modern, coastal

```python
Example Output:
[
  ("modern", 0.82),        # 82% confident
  ("scandinavian", 0.34),  # 34% confident
]
→ Learns: style=modern (+0.21), style=scandinavian (+0.09)
```

#### D. Warmth from Colors
- Analyzes color palette to determine temperature
- Warm colors: red, orange, yellow, pink, brown
- Cool colors: blue, green, cyan, purple
- Neutral: gray, white, black

```python
Example: Image with mostly beige, brown, orange
→ Learns: warmth=warm (+0.2)
```

#### E. Visual Complexity
- Edge detection + color variety
- Estimates simple/moderate/complex
- Based on visual density and color diversity

```python
Example: Minimalist white room with few items
→ Learns: complexity=simple (+0.15)
```

---

## Complete Flow

### When User Selects a Design:

```python
1. Mark design version as selected in database
2. Mark specific image as selected (if provided)

3. TEXT-BASED LEARNING:
   - Extract keywords from design description
   - Update preferences with +0.3 confidence boost

4. IMAGE-BASED LEARNING (if image selected):
   - Download image from Supabase URL
   - Extract color palette (K-means clustering)
   - Detect materials (CLIP zero-shot)
   - Detect visual style (CLIP zero-shot)
   - Determine warmth from colors
   - Estimate visual complexity
   - Update preferences with weighted confidence
```

### Confidence Calculation:

```python
# Text-based
selection_boost = +0.3  # Strong signal

# Image-based (weighted by detection confidence)
color_confidence = 0.25 * color_percentage  # e.g., 0.25 * 0.35 = 0.088
material_confidence = 0.2 * detection_confidence  # e.g., 0.2 * 0.72 = 0.144
style_confidence = 0.25 * detection_confidence  # e.g., 0.25 * 0.82 = 0.205
warmth_confidence = 0.2  # Fixed boost
```

---

## Technical Implementation

### Files Modified/Created:

1. **`backend/memory/image_analyzer.py`** (NEW)
   - ImageAnalyzer class with CLIP model
   - Color extraction using K-means
   - Material and style detection using CLIP
   - Warmth and complexity estimation

2. **`backend/memory/manager.py`**
   - Added `learn_from_selected_image()` method
   - Orchestrates image analysis and preference updates

3. **`backend/memory/learner.py`**
   - Added COLOR_KEYWORDS and MATERIAL_KEYWORDS
   - Enhanced `extract_preferences_from_text()` for new types

4. **`backend/agent/design_agent.py`**
   - Updated `select_design()` to call image analysis

5. **`backend/models/types.py`**
   - PreferenceType enum already had COLOR and MATERIAL

6. **`requirements.txt`**
   - Added: transformers, torch, torchvision, Pillow, scikit-learn

---

## Dependencies

### CLIP Model
- Model: `openai/clip-vit-base-patch32`
- Size: ~350MB (downloads on first use)
- Device: CPU (works on all machines, no GPU required)
- Loading time: ~5-10 seconds on first startup

### Python Packages
```
transformers>=4.30.0  # CLIP model
torch>=2.0.0          # Deep learning framework
torchvision>=0.15.0   # Vision utilities
Pillow>=10.0.0        # Image processing
scikit-learn>=1.3.0   # K-means clustering
```

---

## Database Schema

### `user_preferences` Table (Existing)

```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    preference_type TEXT NOT NULL,  -- 'style', 'color', 'material', 'warmth', 'complexity'
    preference_value TEXT NOT NULL, -- 'modern', 'blue', 'wood', 'warm', 'simple'
    confidence FLOAT NOT NULL,      -- 0.0 to 1.0
    source_room_id UUID,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_user_prefs ON user_preferences(user_id, confidence DESC);
```

No schema changes required - COLOR and MATERIAL types already supported!

---

## Example User Journey

### 1. User Creates Design
```
User: "Design a modern living room"
Agent: [Generates 3 design options with images]
```

### 2. User Selects Design
```
User: [Clicks "Select This Design" on Option 2]

TEXT LEARNING:
  Description: "Modern minimalist living room with natural wood furniture"
  → style=modern (+0.3)
  → complexity=simple (+0.3)
  → material=wood (+0.3)

IMAGE LEARNING:
  Analyzing image: https://supabase.../designs/abc123.png

  Colors detected:
    - white (38%) → color=white (+0.10)
    - gray (22%) → color=gray (+0.06)
    - brown/wood (18%) → color=brown (+0.05)

  Materials detected:
    - wood furniture (75% confidence) → material=wood (+0.15)
    - fabric upholstery (52% confidence) → material=fabric (+0.10)
    - glass surfaces (28% confidence) → material=glass (+0.06)

  Visual style detected:
    - modern minimalist (84% confidence) → style=modern (+0.21)
    - scandinavian (35% confidence) → style=scandinavian (+0.09)

  Warmth: neutral → warmth=neutral (+0.2)
  Complexity: simple → complexity=simple (+0.15)
```

### 3. Preferences Updated
```
Your Preferences:
  style: modern 88%        (0.3 text + 0.21 image + existing)
  material: wood 75%       (0.3 text + 0.15 image)
  color: white 65%         (0.10 image)
  material: fabric 52%     (0.10 image)
  warmth: neutral 60%      (0.2 image)
  complexity: simple 70%   (0.3 text + 0.15 image)
```

### 4. Next Design Uses Preferences
```
User: "Design a bedroom"
Agent context includes:
  "User Preferences:
   - Style: modern (0.88), scandinavian (0.09)
   - Materials: wood (0.75), fabric (0.52)
   - Colors: white (0.65), gray (0.45)
   - Warmth: neutral (0.60)"

Agent generates bedroom designs incorporating these visual preferences!
```

---

## Advantages Over Text-Only Learning

### Before (Text-Only):
❌ Could only learn from keywords in descriptions
❌ Missed visual patterns users actually preferred
❌ Couldn't detect specific colors or materials from images
❌ Required users to explicitly mention preferences

### After (Text + Image):
✅ Learns from what users **visually select**, not just what they say
✅ Detects dominant colors automatically (no need to mention "I like blue")
✅ Identifies materials from actual furniture in images
✅ Captures nuanced visual styles (modern minimalist vs traditional modern)
✅ More accurate warmth detection from color palettes
✅ Objective complexity assessment from image analysis

---

## Performance Notes

### First Startup:
- Downloads CLIP model (~350MB) - one-time only
- Takes 5-10 seconds to load model into memory
- Subsequent startups are faster

### Per-Selection Analysis:
- Image download: ~1-2 seconds
- Color extraction: ~0.5 seconds
- CLIP material detection: ~1-2 seconds
- CLIP style detection: ~1-2 seconds
- **Total: ~5-7 seconds per selection**

Runs asynchronously, doesn't block the response to user!

---

## Future Enhancements

### Possible Improvements:
1. **Embedding similarity**: Store image embeddings to find similar designs
2. **Rejection analysis**: Learn what user dislikes from rejected images
3. **Behavioral patterns**: Track which option (1, 2, or 3) user typically picks
4. **Fine-tuning**: Train custom model on interior design images
5. **GPU acceleration**: Faster inference with CUDA
6. **Batch processing**: Analyze multiple images together
7. **Furniture detection**: Identify specific furniture types (sofa, table, chair)
8. **Layout analysis**: Learn spatial arrangement preferences

---

## Debugging

### Check if CLIP loaded:
```bash
tail -f server.log | grep "CLIP"
# Should see: "Loading CLIP model on cpu..." and "CLIP model loaded successfully"
```

### Check image analysis:
```bash
tail -f server.log | grep "Analyzing selected image"
# Should see: "Analyzing selected image: https://..."
# Followed by: "Image analysis complete: 5 colors, 3 materials, 3 styles"
```

### If CLIP fails to load:
- System falls back to text-only learning
- Warning logged: "Could not load CLIP model: ..."
- Color extraction still works (doesn't require CLIP)

---

## Summary

We've built a **hybrid preference learning system** that combines:
- Traditional NLP keyword extraction
- Modern computer vision with CLIP
- Unsupervised color clustering
- Zero-shot classification for materials and styles

This creates a **rich, multi-modal understanding** of user preferences that goes beyond what they explicitly say to capture what they **visually prefer**.
