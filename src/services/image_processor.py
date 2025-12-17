from io import BytesIO
from pathlib import Path
from PIL import Image
import uuid


def _sanitize_file(file_name: str) -> str:
    """sanitizes the file and returns a unique file name"""
    stem = Path(file_name).stem
    sanitized_stem = stem.replace(" ", "_")[:50]
    return f"{sanitized_stem}_{uuid.uuid4().hex[:8]}.jpeg"


def create_thumbnail(
    file: bytes,
    output_path: str | Path,
    original_filename: str,
) -> str:
    """
    Creates Thumbnail from images bytes
    """
    if not file:
        raise ValueError("No file provided")

    size = (300, 300)

    unique_file_name = _sanitize_file(original_filename)
    path_to_save = Path(output_path) / unique_file_name

    try:
        with Image.open(BytesIO(file)) as img:
            img.thumbnail(size=size, resample=Image.Resampling.LANCZOS)
            img.save(path_to_save, format="JPEG")
            return str(path_to_save)
    except Exception as e:
        raise IOError(f"Failed to save thumbnail {e}")


def create_original(
    file: bytes, output_path: str | Path, original_filename: str
) -> None:
    if not file:
        raise ValueError("No file provided")
    stem = Path(original_filename).stem
    path_to_save = Path(output_path) / f"{stem}.jpeg"

    try:
        with Image.open(BytesIO(file)) as img:
            img.save(path_to_save, format="JPEG")
    except Exception as e:
        raise IOError(f"Failed to save file {e}")
