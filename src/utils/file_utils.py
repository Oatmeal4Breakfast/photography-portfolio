import uuid
from pathlib import Path


def sanitize_file(file_name: str) -> str:
    """sanitizes the file and returns a unique file name"""
    stem: str = Path(file_name).stem
    sanitized_stem: str = stem.replace(" ", "_")[:50]
    return f"{sanitized_stem}_{uuid.uuid4().hex[:8]}.jpeg"
