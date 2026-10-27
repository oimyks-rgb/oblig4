import io
import os
import time
from datetime import timedelta

import pytest
from PIL import Image

from app.models.images import ImageError, LocalImageStore, image_name, process_image
from app.models.memory import MemoryImageStore
from tests.conftest import picture_bytes


def open_image(data):
    return Image.open(io.BytesIO(data))


def test_large_picture_is_shrunk_to_jpeg():
    result = open_image(process_image(picture_bytes((3000, 1500))))
    assert result.format == "JPEG"
    assert result.size == (1200, 600)


def test_png_with_transparency_becomes_jpeg():
    result = open_image(process_image(picture_bytes(fmt="PNG", color=(0, 0, 0, 0))))
    assert result.format == "JPEG"
    assert result.getpixel((0, 0)) == pytest.approx((255, 255, 255), abs=3)


def test_exif_metadata_is_removed():
    exif = Image.Exif()
    exif[0x010F] = "Secret camera maker"
    data = picture_bytes(exif=exif.tobytes())
    assert b"Secret camera" in data
    assert b"Secret camera" not in process_image(data)


@pytest.mark.parametrize("data", [b"", b"hello, not a picture", picture_bytes(fmt="GIF")])
def test_non_pictures_are_rejected(data):
    with pytest.raises(ImageError):
        process_image(data)


def test_oversized_files_are_rejected():
    with pytest.raises(ImageError, match="too large"):
        process_image(b"x" * (5 * 1024 * 1024 + 1))


def check_image_store(store):
    data = process_image(picture_bytes())
    name = store.save(data)
    assert name == image_name(data)
    assert store.save(data) == name  # same content, same name
    assert store.read(name) == data
    assert store.exists(name)

    draft = store.save(data, draft=True)
    assert draft.startswith("draft-") and draft != name
    other = process_image(picture_bytes(color=(10, 10, 10)))
    draft2 = store.save(other, draft=True)
    final = store.promote(draft2)
    assert final == image_name(other)
    assert store.read(final) == other
    assert not store.exists(draft2)
    with pytest.raises(KeyError):
        store.promote(final)  # not a draft

    store.delete(name)
    assert store.read(name) is None

    for bad in ("../secret.jpg", "x.jpg", "/etc/passwd", "draft-../x.jpg", ""):
        assert store.read(bad) is None
        assert not store.exists(bad)
        store.delete(bad)  # no error, no effect

    assert store.cleanup_drafts(timedelta(days=1)) == 0
    assert store.exists(draft)
    return draft


def test_memory_image_store():
    store = MemoryImageStore()
    draft = check_image_store(store)
    store._files[draft] = (store._files[draft][0], time.time() - 2 * 86400)
    assert store.cleanup_drafts(timedelta(days=1)) == 1


def test_local_image_store(tmp_path):
    store = LocalImageStore(tmp_path / "images")
    draft = check_image_store(store)
    old = time.time() - 2 * 86400
    os.utime(tmp_path / "images" / draft, (old, old))
    assert store.cleanup_drafts(timedelta(days=1)) == 1
    assert sorted(p.name for p in (tmp_path / "images").iterdir()) == [image_name(process_image(picture_bytes(color=(10, 10, 10))))]
