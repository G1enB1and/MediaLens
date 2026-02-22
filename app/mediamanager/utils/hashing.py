from __future__ import annotations

import hashlib
from pathlib import Path


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
