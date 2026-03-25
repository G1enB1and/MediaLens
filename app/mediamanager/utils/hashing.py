from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

try:
    _RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # pragma: no cover - Pillow < 9 compatibility
    _RESAMPLE = Image.LANCZOS

try:
    import imagehash
except Exception:  # pragma: no cover - runtime dependency may be absent until install
    imagehash = None


def calculate_file_hash(path: str | Path, block_size: int = 65536) -> str:
    """Calculate the SHA-256 hash of a file.

    Args:
        path: Path to the file.
        block_size: Buffer size for reading the file.

    Returns:
        Hexadecimal string of the hash.
    """
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            hasher.update(block)
    return hasher.hexdigest()


def calculate_image_phash(path: str | Path) -> str:
    """Calculate a perceptual hash for visually similar image detection."""
    try:
        with Image.open(path) as img:
            if imagehash is not None:
                return str(imagehash.phash(img))
            # Fallback to a built-in 64-bit average hash so similar grouping still
            # works when ImageHash is not available in the active interpreter.
            gray = img.convert("L").resize((8, 8), _RESAMPLE)
            pixels = list(gray.getdata())
            if not pixels:
                return ""
            avg = sum(pixels) / len(pixels)
            bits = "".join("1" if px >= avg else "0" for px in pixels)
            return f"{int(bits, 2):016x}"
    except Exception:
        return ""


def phash_distance(left: str, right: str) -> int:
    """Return the Hamming distance between two hexadecimal perceptual hashes."""
    left_value = str(left or "").strip()
    right_value = str(right or "").strip()
    if not left_value or not right_value:
        return 64
    try:
        return (int(left_value, 16) ^ int(right_value, 16)).bit_count()
    except Exception:
        return 64
