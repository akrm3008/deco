"""Preference learning from user conversations and feedback."""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from backend.config import config
from backend.models.schemas import UserPreference
from backend.models.types import PreferenceType
from backend.memory.storage import storage


class PreferenceLearner:
    """Extracts and updates user preferences from conversations."""

    # Keywords for detecting preferences
    STYLE_KEYWORDS = {
        "modern": ["modern", "contemporary", "minimalist", "clean"],
        "traditional": ["traditional", "classic", "vintage", "antique"],
        "rustic": ["rustic", "farmhouse", "country", "natural"],
        "industrial": ["industrial", "urban", "loft", "metal"],
        "bohemian": ["bohemian", "boho", "eclectic", "colorful"],
        "scandinavian": ["scandinavian", "nordic", "simple", "functional"],
    }

    WARMTH_KEYWORDS = {
        "warm": ["warm", "cozy", "inviting", "comfortable"],
        "cool": ["cool", "crisp", "fresh", "airy"],
        "neutral": ["neutral", "balanced", "moderate"],
    }

    COMPLEXITY_KEYWORDS = {
        "simple": ["simple", "minimal", "clean", "uncluttered"],
        "moderate": ["moderate", "balanced"],
        "complex": ["detailed", "ornate", "elaborate", "rich"],
    }

    COLOR_KEYWORDS = {
        "blue": ["blue", "navy", "azure", "cobalt"],
        "green": ["green", "sage", "olive", "emerald"],
        "gray": ["gray", "grey", "charcoal", "slate"],
        "white": ["white", "ivory", "cream", "off-white"],
        "black": ["black", "ebony", "onyx"],
        "brown": ["brown", "tan", "beige", "taupe", "caramel"],
        "red": ["red", "burgundy", "crimson", "maroon"],
        "yellow": ["yellow", "gold", "mustard"],
        "orange": ["orange", "coral", "terracotta"],
        "pink": ["pink", "rose", "blush"],
        "purple": ["purple", "lavender", "plum", "violet"],
    }

    MATERIAL_KEYWORDS = {
        "wood": ["wood", "wooden", "oak", "walnut", "pine", "teak"],
        "metal": ["metal", "steel", "brass", "copper", "iron"],
        "glass": ["glass"],
        "fabric": ["fabric", "textile", "upholstered"],
        "leather": ["leather"],
        "stone": ["stone", "granite", "marble"],
        "concrete": ["concrete"],
        "ceramic": ["ceramic", "tile", "porcelain"],
        "carpet": ["carpet", "rug"],
        "velvet": ["velvet"],
        "linen": ["linen"],
        "rattan": ["rattan", "wicker"],
    }

    def extract_preferences_from_text(
        self, text: str, user_id: str, source_room_id: Optional[str] = None
    ) -> List[UserPreference]:
        """
        Extract preferences from user text.

        Returns list of detected preferences.
        """
        text_lower = text.lower()
        preferences = []

        # Extract style preferences
        for style_value, keywords in self.STYLE_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                pref = UserPreference(
                    user_id=user_id,
                    preference_type=PreferenceType.STYLE,
                    preference_value=style_value,
                    confidence=0.1,  # Low initial confidence for implicit detection
                    source_room_id=source_room_id,
                )
                preferences.append(pref)

        # Extract warmth preferences
        for warmth_value, keywords in self.WARMTH_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                pref = UserPreference(
                    user_id=user_id,
                    preference_type=PreferenceType.WARMTH,
                    preference_value=warmth_value,
                    confidence=0.15 if "warm" in text_lower or "cozy" in text_lower else 0.1,
                    source_room_id=source_room_id,
                )
                preferences.append(pref)

        # Extract complexity preferences
        for complexity_value, keywords in self.COMPLEXITY_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                pref = UserPreference(
                    user_id=user_id,
                    preference_type=PreferenceType.COMPLEXITY,
                    preference_value=complexity_value,
                    confidence=0.1,
                    source_room_id=source_room_id,
                )
                preferences.append(pref)

        # Extract color preferences
        for color_value, keywords in self.COLOR_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                pref = UserPreference(
                    user_id=user_id,
                    preference_type=PreferenceType.COLOR,
                    preference_value=color_value,
                    confidence=0.1,
                    source_room_id=source_room_id,
                )
                preferences.append(pref)

        # Extract material preferences
        for material_value, keywords in self.MATERIAL_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                pref = UserPreference(
                    user_id=user_id,
                    preference_type=PreferenceType.MATERIAL,
                    preference_value=material_value,
                    confidence=0.1,
                    source_room_id=source_room_id,
                )
                preferences.append(pref)

        return preferences

    def update_preference_confidence(
        self,
        user_id: str,
        preference_type: PreferenceType,
        preference_value: str,
        confidence_delta: float,
        source_room_id: Optional[str] = None,
    ) -> UserPreference:
        """
        Update confidence for a preference.

        Confidence scoring logic:
        - Explicit selection: +0.3
        - Positive feedback: +0.2
        - Implicit mention: +0.1
        - Contradictory feedback: -0.2
        - Time decay: applied separately
        """
        # Find existing preference
        existing = storage.find_preference(user_id, preference_type, preference_value)

        if existing:
            # Update existing preference
            new_confidence = min(1.0, max(0.0, existing.confidence + confidence_delta))
            existing.confidence = new_confidence
            existing.updated_at = datetime.utcnow()
            if source_room_id:
                existing.source_room_id = source_room_id
            return storage.update_preference(existing)
        else:
            # Create new preference
            new_preference = UserPreference(
                user_id=user_id,
                preference_type=preference_type,
                preference_value=preference_value,
                confidence=max(0.0, min(1.0, 0.3 + confidence_delta)),
                source_room_id=source_room_id,
            )
            return storage.create_preference(new_preference)

    def apply_time_decay(self, user_id: str, decay_rate: float = 0.95):
        """
        Apply time decay to all user preferences.

        decay_rate: multiplier per week (default 0.95 = 5% decay per week)
        """
        preferences = storage.get_user_preferences(user_id, confidence_threshold=0.0)
        current_time = datetime.utcnow()

        for pref in preferences:
            # Calculate weeks since last update
            time_diff = current_time - pref.updated_at
            weeks = time_diff.total_seconds() / (7 * 24 * 3600)

            # Apply decay
            if weeks > 0:
                decayed_confidence = pref.confidence * (decay_rate ** weeks)
                if decayed_confidence < 0.05:  # Remove very low confidence preferences
                    decayed_confidence = 0.0

                pref.confidence = decayed_confidence
                storage.update_preference(pref)

    def learn_from_selection(
        self, user_id: str, selected_description: str, room_id: Optional[str] = None
    ):
        """
        Learn preferences from user's design selection.

        Selection indicates strong preference, so increase confidence significantly.
        """
        preferences = self.extract_preferences_from_text(
            selected_description, user_id, room_id
        )

        for pref in preferences:
            # Selection is strong signal, boost confidence
            self.update_preference_confidence(
                user_id,
                pref.preference_type,
                pref.preference_value,
                confidence_delta=0.3,  # Strong positive signal
                source_room_id=room_id,
            )

    def learn_from_feedback(
        self,
        user_id: str,
        feedback_text: str,
        is_positive: bool,
        room_id: Optional[str] = None,
    ):
        """Learn preferences from user feedback."""
        preferences = self.extract_preferences_from_text(
            feedback_text, user_id, room_id
        )

        confidence_delta = 0.2 if is_positive else -0.2

        for pref in preferences:
            self.update_preference_confidence(
                user_id,
                pref.preference_type,
                pref.preference_value,
                confidence_delta=confidence_delta,
                source_room_id=room_id,
            )

    def get_preference_summary(self, user_id: str) -> Dict[str, List[str]]:
        """
        Get a summary of user preferences by type.

        Returns dict of {preference_type: [values]} with high confidence preferences.
        """
        preferences = storage.get_user_preferences(
            user_id, confidence_threshold=config.PREFERENCE_CONFIDENCE_THRESHOLD
        )

        summary = {}
        for pref in preferences:
            pref_type = pref.preference_type.value
            if pref_type not in summary:
                summary[pref_type] = []
            summary[pref_type].append(f"{pref.preference_value} ({pref.confidence:.2f})")

        return summary


# Global preference learner instance
preference_learner = PreferenceLearner()
