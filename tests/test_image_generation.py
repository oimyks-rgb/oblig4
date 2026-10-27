import base64
from types import SimpleNamespace

import pytest

from app.models.image_generation import (
    FakeImageGenerator,
    GeminiImageGenerator,
    ImageGenerationError,
    create_image_generator,
    default_illustration_prompt,
)
from app.models.images import process_image
from tests.conftest import make_item, picture_bytes


class FakeInteractions:
    def __init__(self, result=None, error=None):
        self.calls, self.result, self.error = [], result, error

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


def gemini(result=None, error=None):
    interactions = FakeInteractions(result, error)
    client = SimpleNamespace(interactions=interactions)
    return GeminiImageGenerator(api_key="", model="test-model", client=client), interactions


def image_result(data):
    return SimpleNamespace(output_image=SimpleNamespace(data=base64.b64encode(data).decode()))


def test_gemini_create_sends_prompt_and_decodes_picture():
    png = picture_bytes(fmt="PNG")
    generator, interactions = gemini(image_result(png))

    assert generator.create("A bowl of soup") == png
    [call] = interactions.calls
    assert call["model"] == "test-model"
    assert call["input"] == "A bowl of soup"
    assert call["response_format"] == {"type": "image", "aspect_ratio": "4:3", "image_size": "1K"}
    assert call["store"] is False


def test_gemini_modify_sends_current_picture():
    jpeg = picture_bytes()
    generator, interactions = gemini(image_result(jpeg))

    generator.modify(jpeg, "Add dill")
    text, image = interactions.calls[0]["input"]
    assert text == {"type": "text", "text": "Add dill"}
    assert image["type"] == "image" and image["mime_type"] == "image/jpeg"
    assert base64.b64decode(image["data"]) == jpeg


def test_gemini_errors_become_readable():
    generator, _ = gemini(error=RuntimeError("quota exceeded"))
    with pytest.raises(ImageGenerationError, match="quota exceeded"):
        generator.create("x")

    generator, _ = gemini(SimpleNamespace(output_image=None))
    with pytest.raises(ImageGenerationError, match="no picture"):
        generator.create("x")


def test_gemini_requires_key_without_client():
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        GeminiImageGenerator(api_key="")


def test_fake_generator_gives_usable_pictures():
    fake = FakeImageGenerator()
    created = process_image(fake.create("Soup"))
    assert process_image(fake.modify(created, "Add dill"))


def test_default_prompt_mentions_item_and_style():
    prompt = default_illustration_prompt(make_item(name="Fish soup", description="Creamy soup."))
    assert "Fish soup (Creamy soup)" in prompt
    assert "flat vector illustration" in prompt
    assert "No text" in prompt


def test_create_image_generator_from_config():
    assert create_image_generator({"IMAGE_GENERATOR": ""}) is None
    assert isinstance(create_image_generator({"IMAGE_GENERATOR": "fake"}), FakeImageGenerator)
    with pytest.raises(ValueError):
        create_image_generator({"IMAGE_GENERATOR": "dalle"})
