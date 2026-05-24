"""File utility functions."""
import os
import uuid


def ensure_dir(path: str) -> str:
    """Ensure a directory exists, creating it if necessary."""
    os.makedirs(path, exist_ok=True)
    return path


def generate_filename(extension: str, prefix: str = "") -> str:
    """Generate a unique filename with the given extension."""
    unique_id = uuid.uuid4().hex
    return f"{prefix}{unique_id}.{extension}"
