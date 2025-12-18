from io import BytesIO
from src.config import Config, EnvType
from pathlib import Path
from PIL import Image
import uuid


def _get_output_path(file_name: str, subdir: str) -> str:
    config: Config = Config.from_env()

    if config.env_type == EnvType.DEVELOPMENT:
        path: Path = Path(config.uploads_base_path) / subdir / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)
    else:
        return f"{config.uploads_base_path}/{subdir}/{file_name}"


def _sanitize_file(file_name: str) -> str:
    """sanitizes the file and returns a unique file name"""
    stem = Path(file_name).stem
    sanitized_stem = stem.replace(" ", "_")[:50]
    return f"{sanitized_stem}_{uuid.uuid4().hex[:8]}.jpeg"


def create_thumbnail(
    file: bytes,
    original_filename: str,
) -> str:
    """
    Creates Thumbnail from images bytes
    """
    if not file:
        raise ValueError("No file provided")

    size = (300, 300)

    unique_file_name: str = _sanitize_file(file_name=original_filename)
    path_to_save = Path(
        _get_output_path(file_name=unique_file_name, subdir="thumbnail")
    )

    try:
        with Image.open(fp=BytesIO(initial_bytes=file)) as img:
            img.thumbnail(size=size, resample=Image.Resampling.LANCZOS)
            img.save(path_to_save, format="JPEG")
            return str(path_to_save)
    except Exception as e:
        raise IOError(f"Failed to save thumbnail {e}")


def create_original(file: bytes, original_filename: str) -> str:
    """returns path to save file of the original size"""

    if not file:
        raise ValueError("No file provided")

    unique_file_name: str = _sanitize_file(file_name=original_filename)
    path_to_save: Path = Path(
        _get_output_path(file_name=unique_file_name, subdir="original")
    )

    try:
        with Image.open(fp=BytesIO(initial_bytes=file)) as img:
            img.save(path_to_save, format="JPEG")
            return str(path_to_save)
    except Exception as e:
        raise IOError(f"Failed to save file {e}")
