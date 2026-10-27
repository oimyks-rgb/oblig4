"""AI-generated pictures (A2): create a picture from an instruction, or modify one.

GeminiImageGenerator calls Google's Gemini image model (paid, needs GEMINI_API_KEY).
FakeImageGenerator draws a simple card locally and is used in tests and demos.
Every Gemini picture carries Google's invisible SynthID watermark.
"""

import base64
import io
import textwrap
from abc import ABC, abstractmethod

from PIL import Image, ImageDraw

from .domain import FoodItem

DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite-image"
INSTRUCTION_MAX = 1000


class ImageGenerationError(RuntimeError):
    """The image service failed. The message is shown to the user."""


def default_illustration_prompt(item: FoodItem) -> str:
    """One consistent illustration style for every food item."""
    about = f"{item.name} ({item.description.rstrip('.')})" if item.description else item.name
    return (
        f"A simple flat vector illustration of {about}, a Norwegian catering dish. "
        "Centred on a plain warm off-white background, soft natural colours, "
        "seen from slightly above. No text, no people, no logos."
    )


class ImageGenerator(ABC):
    @abstractmethod
    def create(self, instruction: str) -> bytes:
        """A new picture from a text instruction."""

    @abstractmethod
    def modify(self, image: bytes, instruction: str) -> bytes:
        """A changed version of a JPEG picture, following the instruction."""


class GeminiImageGenerator(ImageGenerator):
    def __init__(self, api_key: str, model: str = DEFAULT_GEMINI_MODEL, client=None):
        if client is None:
            if not api_key:
                raise RuntimeError("Set GEMINI_API_KEY in .env to use IMAGE_GENERATOR=gemini.")
            from google import genai

            client = genai.Client(api_key=api_key)
        self._client = client
        self.model = model

    def create(self, instruction):
        return self._generate(instruction)

    def modify(self, image, instruction):
        return self._generate(
            [
                {"type": "text", "text": instruction},
                {"type": "image", "data": base64.b64encode(image).decode("ascii"), "mime_type": "image/jpeg"},
            ]
        )

    def _generate(self, request_input) -> bytes:
        try:
            interaction = self._client.interactions.create(
                model=self.model,
                input=request_input,
                response_format={"type": "image", "aspect_ratio": "4:3", "image_size": "1K"},
                store=False,  # don't keep our prompts on Google's side
            )
        except Exception as error:  # the SDK raises several error types
            raise ImageGenerationError(f"The image service failed: {error}") from error
        output = getattr(interaction, "output_image", None)
        if output is None or not getattr(output, "data", None):
            raise ImageGenerationError(
                "The image service returned no picture. Try rephrasing the instruction."
            )
        return base64.b64decode(output.data)


class FakeImageGenerator(ImageGenerator):
    """Draws the instruction on a card. No network, no cost."""

    def create(self, instruction):
        image = Image.new("RGB", (800, 600), (232, 239, 233))
        return self._draw_text(image, instruction)

    def modify(self, image, instruction):
        picture = Image.open(io.BytesIO(image)).convert("RGB")
        return self._draw_text(picture, "Modified: " + instruction)

    @staticmethod
    def _draw_text(image, text):
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, image.width - 20, 140), fill=(47, 93, 80))
        draw.multiline_text((36, 32), "\n".join(textwrap.wrap(text, 70)[:5]), fill="white")
        out = io.BytesIO()
        image.save(out, "PNG")
        return out.getvalue()


def create_image_generator(config) -> "ImageGenerator | None":
    kind = (config.get("IMAGE_GENERATOR") or "").strip().lower()
    if not kind:
        return None
    if kind == "fake":
        return FakeImageGenerator()
    if kind == "gemini":
        return GeminiImageGenerator(
            config.get("GEMINI_API_KEY", ""), config.get("GEMINI_IMAGE_MODEL") or DEFAULT_GEMINI_MODEL
        )
    raise ValueError(f"Unknown IMAGE_GENERATOR: {kind!r} (use gemini, fake or leave empty)")
