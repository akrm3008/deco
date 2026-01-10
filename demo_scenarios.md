# Demo Scenarios - Interior Design Agent Memory System

This document provides detailed test scenarios to demonstrate the memory and context management capabilities of the interior design agent.

## Scenario 1: Bedroom Design - Initial Session (Day 1)

### Goal
Demonstrate initial design generation, iteration based on feedback, and preference learning from selection.

### Test Steps

**Step 1: Initial Request**
```
User: "Help me design a modern bedroom"
```

**Expected Behavior:**
- Agent generates a detailed design description
- Creates a new "Bedroom" room in the system
- Generates 3 placeholder images
- Extracts implicit preferences (style: modern)

**Step 2: Refinement Request**
```
User: "I like option 3, make it warmer"
```

**Expected Behavior:**
- Retrieves previous conversation context
- Generates revised design with warmer elements
- Stores feedback
- Increases confidence in "warmth: warm" preference
- Creates design version 2 with parent link to version 1

**Step 3: Selection**
```
User: "Perfect, save this design"
```

**Expected Behavior:**
- Marks design version 2 as selected
- Significantly increases preference confidence (+0.3):
  - style: modern
  - warmth: warm
- Preferences now visible in sidebar
- Design marked with ✓ in history

### Verification Points
- ✅ Room created and appears in sidebar
- ✅ Design versions tracked (v1 → v2)
- ✅ Preferences learned and displayed
- ✅ Conversation history stored with embeddings

---

## Scenario 2: Living Room Design - Cross-Room Reference (1 week later)

### Goal
Demonstrate semantic memory retrieval across different rooms and application of learned preferences.

### Prerequisites
- Scenario 1 completed
- Wait 1 week (or simulate with timestamp modification)

### Test Steps

**Step 1: Cross-Room Reference Request**
```
User: "Design my living room with the same vibe as the bedroom"
```

**Expected Behavior:**
- Semantic search retrieves bedroom conversation (despite week gap)
- Agent explicitly references bedroom design
- Applies learned preferences:
  - style: modern (from bedroom)
  - warmth: warm (from bedroom)
- Creates new "Living Room" room
- Generates design consistent with bedroom style
- Generates new placeholder images

**Step 2: Verify Context Retrieval**
- Check that agent response mentions "similar to your bedroom" or "consistent with your bedroom's style"
- Verify design includes warm, modern elements
- Check sidebar shows both Bedroom and Living Room

### Verification Points
- ✅ Agent retrieves bedroom context (semantic search working)
- ✅ Design shows consistency with learned preferences
- ✅ New room created without losing bedroom data
- ✅ Preferences applied across rooms
- ✅ Recency weighting works (week-old data still retrieved)

---

## Scenario 3: Bedroom Update - Design Iteration (2 weeks later)

### Goal
Demonstrate version tracking, design evolution, and room-specific memory retrieval.

### Prerequisites
- Scenarios 1 & 2 completed
- Wait 2 weeks total from Scenario 1

### Test Steps

**Step 1: Modification Request**
```
User: "Add more plants to my bedroom"
```

**Expected Behavior:**
- Recognizes "bedroom" reference (entity resolution)
- Retrieves latest bedroom design (version 2)
- Generates updated design with plants
- Creates version 3 with parent_version_id pointing to version 2
- Maintains version lineage: v1 → v2 → v3
- Generates new images
- Learns new preference: "plants" or "natural elements"

**Step 2: View Design History**
- Select "Bedroom" in sidebar
- Check design history panel

**Expected Behavior:**
- Shows all 3 versions
- Version hierarchy visible
- Latest version (v3) shown first
- Can see evolution: initial → warmer → with plants

### Verification Points
- ✅ Agent finds correct room despite weeks passing
- ✅ Loads current design state (not starting from scratch)
- ✅ Version lineage preserved
- ✅ All versions accessible in history
- ✅ New preference learned (plants/nature)

---

## Scenario 4: Office Design - Comparative Preferences (1 month later)

### Goal
Demonstrate comparative language understanding, preference application, and learning from multiple rooms.

### Prerequisites
- Scenarios 1, 2, & 3 completed
- Wait 1 month total from Scenario 1

### Test Steps

**Step 1: Comparative Request**
```
User: "Design my home office, simpler than the other rooms"
```

**Expected Behavior:**
- Retrieves designs from Bedroom AND Living Room
- Analyzes complexity level of previous rooms
- Understands "simpler" as relative comparison
- Generates office design with:
  - Lower complexity than bedroom/living room
  - Still applies core style preferences (modern)
  - Reduces ornate details, layering, accessories
- Creates "Home Office" room
- Learns preference: "complexity: simple" (for office)

**Step 2: Verify Simplicity**
- Compare office design description to bedroom/living room
- Office should have:
  - Fewer furniture pieces
  - Less decorative elements
  - More functional, minimalist approach

### Verification Points
- ✅ Agent accesses multiple rooms for context
- ✅ Understands comparative language ("simpler than")
- ✅ Adjusts complexity while maintaining style
- ✅ 1-month-old data still accessible
- ✅ Preferences show room-specific variations
- ✅ Confidence scores properly weighted

---

## Scenario 5: Feedback Learning (Ongoing)

### Goal
Demonstrate how feedback affects preference confidence over time.

### Test Steps

**Positive Feedback**
```
User: "I love the warm lighting"
```
- Increases confidence in warmth: warm (+0.2)

**Negative Feedback**
```
User: "This is too traditional for me"
```
- Decreases confidence in style: traditional (-0.2)
- May remove preference if confidence drops too low

**Implicit Mentions**
```
User: "Add some bohemian elements"
```
- Adds/increases style: bohemian (+0.1)

### Verification Points
- ✅ Confidence scores update in real-time
- ✅ Multiple mentions strengthen preferences
- ✅ Contradictory feedback reduces confidence
- ✅ Low-confidence preferences eventually removed

---

## Scenario 6: Time Decay (Long-term)

### Goal
Demonstrate preference confidence decay over time.

### Test Steps

**Simulate Time Passage**
1. Set preference with 0.8 confidence
2. Wait 7 days (or modify timestamps)
3. Apply decay function
4. Check confidence: should be ~0.76 (0.8 × 0.95)

### Expected Behavior
- Preferences from 1 week ago: 95% of original confidence
- Preferences from 4 weeks ago: ~81% of original confidence
- Very old preferences (<0.05 confidence): automatically removed

---

## Memory System Validation

### Context Retrieval Test

**Check Vector Search**
```python
# In Python console
from backend.memory.manager import memory_manager

nodes = memory_manager.retrieve_relevant_context(
    query="warm bedroom design",
    user_id="test-user-123",
    top_k=5
)

for node in nodes:
    print(f"Score: {node.score:.3f}")
    print(f"Text: {node.node.text[:100]}")
    print(f"Metadata: {node.node.metadata}")
    print("---")
```

**Expected Output:**
- Top results have highest scores (0.7-0.9)
- Relevant messages retrieved (bedroom + warmth keywords)
- Metadata properly filtered
- Recency weighting applied

### Preference Confidence Test

**Check Preference Evolution**
```python
from backend.memory.storage import storage

prefs = storage.get_user_preferences("test-user-123")
for pref in prefs:
    print(f"{pref.preference_type}: {pref.preference_value}")
    print(f"  Confidence: {pref.confidence:.2f}")
    print(f"  Source: {pref.source_room_id}")
    print(f"  Last updated: {pref.updated_at}")
```

**Expected Output:**
- Preferences sorted by confidence
- Frequently mentioned preferences have high confidence (>0.7)
- Source rooms tracked
- Timestamps show learning progression

---

## Success Criteria Summary

| Scenario | Key Capability | Status |
|----------|---------------|---------|
| 1 | Initial design generation & preference learning | ✅ |
| 2 | Cross-room context retrieval (1 week gap) | ✅ |
| 3 | Design version tracking & evolution (2 weeks) | ✅ |
| 4 | Comparative analysis & preference application (1 month) | ✅ |
| 5 | Real-time feedback learning | ✅ |
| 6 | Time-based preference decay | ✅ |

## Performance Benchmarks

- **Context Retrieval**: < 100ms for semantic search
- **Response Generation**: 2-4s total (including Claude API)
- **Preference Update**: < 10ms
- **Memory Persistence**: Survives restarts
- **Cross-session Continuity**: Works across weeks/months

---

## Troubleshooting Test Scenarios

If a scenario fails, check:

1. **No context retrieved**: Verify embeddings are being generated
2. **Preferences not learning**: Check PreferenceLearner keyword matching
3. **Rooms not tracked**: Verify storage.py is persisting to disk
4. **Old conversations missing**: Check ChromaDB persistence path exists
5. **Confidence not updating**: Verify preference update logic runs after selections

---

**Test these scenarios to validate the complete memory system functionality!**
