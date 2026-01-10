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
    async def generate(self, prompt: str, style: Optional[str] = None) -> str:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            style: Optional style modifier

        Returns:
            URL of the generated image
        """
        pass


class PlaceholderGenerator(ImageGenerator):
    """Placeholder generator for development/testing."""

    async def generate(self, prompt: str, style: Optional[str] = None) -> str:
        """Generate a placeholder image URL."""
        # Combine prompt and style
        full_prompt = f"{prompt} ({style})" if style else prompt

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

    async def generate(self, prompt: str, style: Optional[str] = None) -> str:
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

    async def generate(self, prompt: str, style: Optional[str] = None) -> str:
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


def get_image_generator() -> ImageGenerator:
    """Get the configured image generator based on config."""
    if config.IMAGE_GENERATOR == "gpt-5":
        if not config.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not configured, falling back to placeholder")
            return PlaceholderGenerator()
        return GPTImageGenerator(api_key=config.OPENAI_API_KEY)
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
