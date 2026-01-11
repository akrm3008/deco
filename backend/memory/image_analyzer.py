"""Image analysis for preference learning using CLIP and color extraction."""
import io
from typing import Dict, List, Tuple, Optional
from collections import Counter

import httpx
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


class ImageAnalyzer:
    """Analyze images to extract visual preferences."""

    def __init__(self):
        """Initialize image analyzer with CLIP model."""
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Loading CLIP model on {self.device}...")

            # Use smaller CLIP model for faster inference
            model_name = "openai/clip-vit-base-patch32"
            self.clip_model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.clip_processor = CLIPProcessor.from_pretrained(model_name)

            print("CLIP model loaded successfully")
            self.clip_available = True
        except Exception as e:
            print(f"Warning: Could not load CLIP model: {e}")
            print("Image analysis will work with color extraction only")
            self.clip_available = False

        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def download_image(self, image_url: str) -> Optional[Image.Image]:
        """Download image from URL."""
        try:
            response = await self.http_client.get(image_url)
            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content)).convert('RGB')
                return image
            else:
                print(f"Failed to download image: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error downloading image: {e}")
            return None

    def extract_color_palette(self, image: Image.Image, n_colors: int = 5) -> List[Tuple[str, str, float]]:
        """
        Extract dominant colors from image using k-means clustering.

        Returns list of (color_name, hex_code, percentage) tuples.
        """
        try:
            # Resize for faster processing
            img = image.copy()
            img.thumbnail((200, 200))

            # Convert to numpy array and reshape
            pixels = np.array(img).reshape(-1, 3)

            # Apply k-means clustering
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)

            # Get color centers and their frequencies
            colors = kmeans.cluster_centers_.astype(int)
            labels = kmeans.labels_
            label_counts = Counter(labels)
            total_pixels = len(labels)

            # Convert to color names and hex codes
            palette = []
            for i, color in enumerate(colors):
                r, g, b = color
                hex_code = f"#{r:02x}{g:02x}{b:02x}"
                color_name = self._rgb_to_color_name(r, g, b)
                percentage = label_counts[i] / total_pixels
                palette.append((color_name, hex_code, percentage))

            # Sort by percentage (most dominant first)
            palette.sort(key=lambda x: x[2], reverse=True)

            return palette

        except Exception as e:
            print(f"Error extracting color palette: {e}")
            return []

    def _rgb_to_color_name(self, r: int, g: int, b: int) -> str:
        """Convert RGB to basic color name."""
        # Calculate color properties
        max_val = max(r, g, b)
        min_val = min(r, g, b)

        # Check for grayscale
        if max_val - min_val < 30:
            if max_val < 60:
                return "black"
            elif max_val < 130:
                return "gray"
            elif max_val < 200:
                return "light_gray"
            else:
                return "white"

        # Determine dominant color
        if r > g and r > b:
            if r > 200 and g < 100 and b < 100:
                return "red"
            elif r > 200 and g > 150 and b < 100:
                return "orange"
            elif r > 180 and g > 100 and b > 100:
                return "pink"
            else:
                return "brown"
        elif g > r and g > b:
            if g > 200 and r < 100 and b < 100:
                return "green"
            elif g > 150 and r > 150 and b < 100:
                return "yellow"
            else:
                return "olive"
        else:  # b is dominant
            if b > 200 and r < 100 and g < 100:
                return "blue"
            elif b > 150 and r > 100 and g < 150:
                return "purple"
            elif b > 150 and g > 150:
                return "cyan"
            else:
                return "navy"

    async def detect_materials(self, image: Image.Image) -> List[Tuple[str, float]]:
        """
        Detect materials in the image using CLIP zero-shot classification.

        Returns list of (material_name, confidence) tuples.
        """
        if not self.clip_available:
            return []

        try:
            import torch

            # Material categories to detect
            material_labels = [
                "wood furniture",
                "metal fixtures",
                "glass surfaces",
                "fabric upholstery",
                "leather furniture",
                "stone countertops",
                "marble surfaces",
                "concrete walls",
                "brick walls",
                "ceramic tiles",
                "carpet flooring",
                "hardwood flooring",
                "velvet textiles",
                "linen fabrics",
                "rattan furniture",
                "wicker furniture",
            ]

            # Prepare inputs for CLIP
            inputs = self.clip_processor(
                text=material_labels,
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            # Get predictions
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]

            # Get top materials with confidence > threshold
            materials = []
            for label, prob in zip(material_labels, probs):
                if prob > 0.1:  # Only include if confidence > 10%
                    # Simplify label (remove context words)
                    material = label.split()[0]  # "wood" from "wood furniture"
                    materials.append((material, float(prob)))

            # Sort by confidence
            materials.sort(key=lambda x: x[1], reverse=True)

            return materials[:5]  # Return top 5

        except Exception as e:
            print(f"Error detecting materials: {e}")
            return []

    async def detect_style(self, image: Image.Image) -> List[Tuple[str, float]]:
        """
        Detect interior design style using CLIP zero-shot classification.

        Returns list of (style_name, confidence) tuples.
        """
        if not self.clip_available:
            return []

        try:
            import torch

            # Style categories
            style_labels = [
                "modern minimalist interior",
                "traditional classic interior",
                "rustic farmhouse interior",
                "industrial urban interior",
                "bohemian eclectic interior",
                "scandinavian nordic interior",
                "contemporary sleek interior",
                "vintage retro interior",
                "mid-century modern interior",
                "coastal beach interior",
            ]

            # Prepare inputs
            inputs = self.clip_processor(
                text=style_labels,
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            # Get predictions
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]

            # Get top styles
            styles = []
            for label, prob in zip(style_labels, probs):
                if prob > 0.1:
                    # Extract style name (first word)
                    style = label.split()[0].lower()
                    styles.append((style, float(prob)))

            styles.sort(key=lambda x: x[1], reverse=True)
            return styles[:3]  # Return top 3

        except Exception as e:
            print(f"Error detecting style: {e}")
            return []

    async def analyze_image(self, image_url: str) -> Dict[str, List]:
        """
        Perform complete image analysis.

        Returns dict with:
        - colors: List of (color_name, hex_code, percentage)
        - materials: List of (material_name, confidence)
        - styles: List of (style_name, confidence)
        """
        # Download image
        image = await self.download_image(image_url)
        if not image:
            return {"colors": [], "materials": [], "styles": []}

        # Extract features
        colors = self.extract_color_palette(image, n_colors=5)
        materials = await self.detect_materials(image)
        styles = await self.detect_style(image)

        return {
            "colors": colors,
            "materials": materials,
            "styles": styles,
        }

    async def get_warmth_from_colors(self, colors: List[Tuple[str, str, float]]) -> str:
        """
        Determine overall warmth (warm/cool/neutral) from color palette.
        """
        warm_colors = {"red", "orange", "yellow", "pink", "brown"}
        cool_colors = {"blue", "green", "cyan", "purple"}
        neutral_colors = {"gray", "white", "black", "light_gray"}

        warm_score = 0
        cool_score = 0
        neutral_score = 0

        for color_name, _, percentage in colors:
            if color_name in warm_colors:
                warm_score += percentage
            elif color_name in cool_colors:
                cool_score += percentage
            elif color_name in neutral_colors:
                neutral_score += percentage

        # Determine dominant temperature
        if warm_score > cool_score and warm_score > neutral_score:
            return "warm"
        elif cool_score > warm_score and cool_score > neutral_score:
            return "cool"
        else:
            return "neutral"

    async def get_complexity_from_image(self, image: Image.Image) -> str:
        """
        Estimate visual complexity (simple/moderate/complex) from image.

        Uses edge detection and color variety.
        """
        try:
            from PIL import ImageFilter

            # Convert to grayscale for edge detection
            gray = image.convert('L')
            edges = gray.filter(ImageFilter.FIND_EDGES)

            # Count edge pixels
            edges_array = np.array(edges)
            edge_density = np.mean(edges_array > 50)

            # Get number of unique colors
            image_small = image.resize((50, 50))
            colors = len(set(list(image_small.getdata())))
            color_variety = colors / (50 * 50)

            # Combine metrics
            complexity_score = (edge_density + color_variety) / 2

            if complexity_score < 0.15:
                return "simple"
            elif complexity_score < 0.35:
                return "moderate"
            else:
                return "complex"

        except Exception as e:
            print(f"Error calculating complexity: {e}")
            return "moderate"


# Global image analyzer instance
image_analyzer = ImageAnalyzer()
