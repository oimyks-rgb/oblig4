"""Pictures for food items (A2): checking/resizing uploads and storing the files.

Names are content hashes ("<32 hex>.jpg"), so the same picture gets the same name
on every machine. Drafts waiting for the admin's preview are "draft-<uuid>.jpg".
"""

import hashlib
import io
import re
import time
import uuid
from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_SIDE = 1200
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

_NAME = re.compile(r"^(draft-)?[0-9a-f]{32}\.jpg$")


class ImageError(ValueError):
    """The file is not a picture we accept. The message is shown to the user."""


def process_image(data: bytes) -> bytes:
    """Check a picture and return it as a JPEG of at most 1200x1200 px, without metadata."""
    if not data:
        raise ImageError("Choose a picture to upload.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageError("The picture is too large (max 5 MB).")
    try:
        image = Image.open(io.BytesIO(data))
        image_format = image.format
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ImageError("The file is not a picture. Use JPEG, PNG or WebP.") from None
    if image_format not in ALLOWED_FORMATS:
        raise ImageError("Use a JPEG, PNG or WebP picture.")

    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))

    out = io.BytesIO()
    image.save(out, "JPEG", quality=85, optimize=True)  # no exif= argument: metadata is dropped
    return out.getvalue()


def image_name(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:32] + ".jpg"


def is_valid_name(name: str) -> bool:
    return bool(name) and bool(_NAME.match(name))


def is_draft(name: str) -> bool:
    return name.startswith("draft-")


def _check(name: str) -> None:
    if not is_valid_name(name):
        raise ValueError(f"Invalid image name: {name!r}")


class ImageStore(ABC):
    """Where picture files live. Controllers use it through repos().images."""

    def save(self, data: bytes, draft: bool = False) -> str:
        name = f"draft-{uuid.uuid4().hex}.jpg" if draft else image_name(data)
        if draft or not self.exists(name):
            self._write(name, data)
        return name

    def promote(self, draft_name: str) -> str:
        """Turn a draft into a final picture and return its final name."""
        _check(draft_name)
        data = self.read(draft_name)
        if data is None or not is_draft(draft_name):
            raise KeyError(draft_name)
        name = self.save(data)
        self.delete(draft_name)
        return name

    def read(self, name: str) -> Optional[bytes]:
        return self._read(name) if is_valid_name(name) else None

    def exists(self, name: str) -> bool:
        return is_valid_name(name) and self._exists(name)

    def delete(self, name: str) -> None:
        if is_valid_name(name):
            self._delete(name)

    @abstractmethod
    def cleanup_drafts(self, max_age: timedelta) -> int:
        """Delete drafts older than max_age. Returns how many were deleted."""

    @abstractmethod
    def _write(self, name: str, data: bytes) -> None: ...

    @abstractmethod
    def _read(self, name: str) -> Optional[bytes]: ...

    @abstractmethod
    def _exists(self, name: str) -> bool: ...

    @abstractmethod
    def _delete(self, name: str) -> None: ...


class LocalImageStore(ImageStore):
    """Files in a folder on this computer (instance/images/ by default, git-ignored)."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def _path(self, name):
        return self.folder / name

    def _write(self, name, data):
        self._path(name).write_bytes(data)

    def _read(self, name):
        path = self._path(name)
        return path.read_bytes() if path.is_file() else None

    def _exists(self, name):
        return self._path(name).is_file()

    def _delete(self, name):
        self._path(name).unlink(missing_ok=True)

    def cleanup_drafts(self, max_age):
        cutoff = time.time() - max_age.total_seconds()
        deleted = 0
        for path in self.folder.glob("draft-*.jpg"):
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1
        return deleted
