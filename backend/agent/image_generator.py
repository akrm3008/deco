"""Flexible image generation module supporting multiple backends."""
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import quote
import base64
import uuid
from pathlib import Path

import httpx

from backend.config import config
from backend.agent.image_storage import image_storage


class ImageGenerator(ABC):
    """Abstract base class for image generation."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        style: Optional[str] = None,
        reference_image_url: Optional[str] = None
    ) -> str:
        """
        Generate an image from a text prompt, optionally with a reference image.

        Args:
            prompt: Text description of the image to generate
            style: Optional style modifier
            reference_image_url: Optional reference image URL for editing/style transfer

        Returns:
            URL of the generated image
        """
        pass


class PlaceholderGenerator(ImageGenerator):
    """Placeholder generator for development/testing."""

    async def generate(
        self,
        prompt: str,
        style: Optional[str] = None,
        reference_image_url: Optional[str] = None
    ) -> str:
        """Generate a placeholder image URL."""
        # Combine prompt and style
        full_prompt = f"{prompt} ({style})" if style else prompt
        if reference_image_url:
            full_prompt = f"[EDIT] {full_prompt}"

        # Truncate and URL encode
        encoded_prompt = quote(full_prompt[:100])

        # Use placehold.co for placeholder images
        return f"https://placehold.co/800x600/e0e0e0/333333?text={encoded_prompt}"


class GPTImageGenerator(ImageGenerator):
    """GPT-Image-1.5 integration using OpenAI API."""

    def __init__(self, api_key: str):
        """Initialize with OpenAI API key."""
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        style: Optional[str] = None,
        reference_image_url: Optional[str] = None
    ) -> str:
        """
        Generate image using OpenAI's gpt-5 with image generation tools.

        Args:
            prompt: Text description of the image to generate
            style: Optional style modifier

        Returns:
            URL path to the generated image (e.g., /static/images/uuid.png)
        """
        full_prompt = f"{prompt}, {style} style" if style else prompt

        try:
            # Generate image using OpenAI responses API with image generation tool
            response = self.client.responses.create(
                model="gpt-5",
                input=full_prompt,
                tools=[{"type": "image_generation", "action": "generate"}],
            )

            # Extract image data from response
            image_data = [
                output.result
                for output in response.output
                if output.type == "image_generation_call"
            ]

            if not image_data:
                raise Exception("No image data received from OpenAI")

            # Decode base64 image
            image_base64 = image_data[0]
            image_bytes = base64.b64decode(image_base64)

            # Save image using configured storage backend (local or Supabase)
            url, filename = image_storage.save(image_bytes, full_prompt)

            return url

        except Exception as e:
            print(f"Error generating image with OpenAI: {e}")
            # Fallback to placeholder on error
            encoded_prompt = quote(full_prompt[:100])
            return f"https://placehold.co/800x600/ffcccc/000000?text=Error-{encoded_prompt}"


class BananaProGenerator(ImageGenerator):
    """Nano Banana Pro integration (configurable with API details)."""

    def __init__(self, api_key: str, model_key: str):
        self.api_key = api_key
        self.model_key = model_key
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate(
        self,
        prompt: str,
        style: Optional[str] = None,
        reference_image_url: Optional[str] = None
    ) -> str:
        """
        Generate image using Banana Pro API.

        Note: Implementation pending API documentation.
        Once you provide the API details, this will be configured to:
        1. POST to Banana's endpoint with the model key
        2. Include the prompt and style parameters
        3. Handle authentication with the API key
        4. Parse the response to get the image URL
        """
        full_prompt = f"{prompt}, {style} style" if style else prompt

        # Placeholder implementation
        # TODO: Replace with actual Banana API call
        # Example structure:
        # response = await self.client.post(
        #     "https://api.banana.dev/start/v4",
        #     headers={"X-API-Key": self.api_key},
        #     json={
        #         "model_key": self.model_key,
        #         "inputs": {"prompt": full_prompt}
        #     }
        # )
        # return response.json()["output"]["image_url"]

        # For now, return placeholder
        return f"https://placehold.co/800x600/ffcccc/000000?text=Banana-Pro-{quote(full_prompt[:50])}"


class GeminiImageGenerator(ImageGenerator):
    """Google Gemini image generation integration."""

    def __init__(self, api_key: str):
        """Initialize with Gemini API key."""
        self.api_key = api_key
        self.model = "gemini-2.5-flash-image"  # Image generation model from docs
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        prompt: str,
        style: Optional[str] = None,
        reference_image_url: Optional[str] = None
    ) -> str:
        """
        Generate image using Google Gemini API.

        Supports both text-to-image and image editing.

        Args:
            prompt: Text description of the image to generate
            style: Optional style modifier
            reference_image_url: Optional reference image for editing/style transfer

        Returns:
            URL of the generated image
        """
        full_prompt = f"{prompt}, {style} style" if style else prompt

        try:
            # Build request content parts
            parts = []

            # If reference image is provided, download and encode it
            if reference_image_url:
                try:
                    # Download reference image from Supabase public URL
                    image_response = await self.client.get(reference_image_url)

                    if image_response.status_code == 200:
                        # Encode to base64
                        image_base64 = base64.b64encode(image_response.content).decode('utf-8')

                        # Determine mime type from URL or default to PNG
                        mime_type = "image/png"
                        if reference_image_url.endswith('.jpg') or reference_image_url.endswith('.jpeg'):
                            mime_type = "image/jpeg"
                        elif reference_image_url.endswith('.webp'):
                            mime_type = "image/webp"

                        # Add image part
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_base64
                            }
                        })

                        # Add editing instruction
                        parts.append({
                            "text": f"Using the provided image as reference, {full_prompt}. Maintain the overall style, lighting, and composition while making the requested changes."
                        })
                        print(f"DEBUG: Successfully loaded reference image for editing: {reference_image_url}")
                    else:
                        print(f"Warning: Failed to fetch reference image (status {image_response.status_code}): {reference_image_url}")
                        # Fall back to text-only generation
                        parts.append({"text": full_prompt})

                except Exception as e:
                    print(f"Error loading reference image: {e}")
                    # Fall back to text-only generation
                    parts.append({"text": full_prompt})
            else:
                # Text-to-image generation
                parts.append({"text": full_prompt})

            # Make API request
            url = f"{self.base_url}/{self.model}:generateContent"
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }

            payload = {
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "response_modalities": ["IMAGE"]
                }
            }

            response = await self.client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                error_text = response.text
                print(f"Gemini API error: {response.status_code} - {error_text}")
                raise Exception(f"Gemini API returned {response.status_code}")

            result = response.json()

            # Debug: Print response structure
            print(f"DEBUG: Gemini response keys: {result.keys()}")
            if "candidates" in result:
                print(f"DEBUG: Candidates count: {len(result['candidates'])}")
                if result['candidates']:
                    print(f"DEBUG: First candidate keys: {result['candidates'][0].keys()}")

            # Extract image data from response
            # Response structure: candidates[0].content.parts[0].inline_data.data
            candidates = result.get("candidates", [])
            if not candidates:
                print(f"DEBUG: Full response: {result}")
                raise Exception("No candidates in Gemini response")

            content = candidates[0].get("content", {})
            parts_response = content.get("parts", [])

            print(f"DEBUG: Parts count: {len(parts_response)}")
            if parts_response:
                print(f"DEBUG: First part keys: {parts_response[0].keys()}")

            image_base64 = None
            for part in parts_response:
                if "inline_data" in part:
                    image_base64 = part["inline_data"].get("data")
                    break
                elif "inlineData" in part:  # Try camelCase variant
                    image_base64 = part["inlineData"].get("data")
                    break

            if not image_base64:
                print(f"DEBUG: Full response: {result}")
                raise Exception("No image data in Gemini response")

            # Decode base64 image
            image_bytes = base64.b64decode(image_base64)

            # Save image using configured storage backend
            url_path, filename = image_storage.save(image_bytes, full_prompt)

            return url_path

        except Exception as e:
            print(f"Error generating image with Gemini: {e}")
            # Fallback to placeholder on error
            encoded_prompt = quote(full_prompt[:100])
            mode = "Edit" if reference_image_url else "Gen"
            return f"https://placehold.co/800x600/ffcccc/000000?text={mode}-Error-{encoded_prompt}"


def get_image_generator() -> ImageGenerator:
    """Get the configured image generator based on config."""
    if config.IMAGE_GENERATOR == "gpt-5":
        if not config.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not configured, falling back to placeholder")
            return PlaceholderGenerator()
        return GPTImageGenerator(api_key=config.OPENAI_API_KEY)
    elif config.IMAGE_GENERATOR == "gemini":
        if not config.GEMINI_API_KEY:
            print("Warning: GEMINI_API_KEY not configured, falling back to placeholder")
            return PlaceholderGenerator()
        return GeminiImageGenerator(api_key=config.GEMINI_API_KEY)
    elif config.IMAGE_GENERATOR == "banana-pro":
        if not config.IMAGE_API_KEY or not config.IMAGE_MODEL_KEY:
            print("Warning: Banana Pro not fully configured, falling back to placeholder")
            return PlaceholderGenerator()
        return BananaProGenerator(
            api_key=config.IMAGE_API_KEY, model_key=config.IMAGE_MODEL_KEY
        )
    else:
        # Default to placeholder
        return PlaceholderGenerator()


# Global image generator instance
image_generator = get_image_generator()
