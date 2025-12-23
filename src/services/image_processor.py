from io import BytesIO
from pathlib import Path
from PIL import Image

from src.config import Config, EnvType


def _get_output_path(file_name: str, subdir: str) -> str:
    config: Config = Config.from_env()
    path: Path = Path("uploads") / subdir / file_name
    if config.env_type == EnvType.DEVELOPMENT:
        path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def create_thumbnail(
    file: bytes,
    file_name: str,
) -> str:
    """
    Creates Thumbnail from images bytes
    """
    if not file:
        raise ValueError("No file provided")

    size = (300, 300)

    path_to_save = Path(_get_output_path(file_name=file_name, subdir="thumbnail"))

    try:
        with Image.open(fp=BytesIO(initial_bytes=file)) as img:
            img.thumbnail(size=size, resample=Image.Resampling.LANCZOS)
            img.save(path_to_save, format="JPEG")
            return str(path_to_save)
    except Exception as e:
        raise IOError(f"Failed to save thumbnail {e}")


def create_original(file: bytes, file_name: str) -> str:
    """returns path to save file of the original size"""

    if not file:
        raise ValueError("No file provided")

    path_to_save: Path = Path(_get_output_path(file_name=file_name, subdir="original"))

    try:
        with Image.open(fp=BytesIO(initial_bytes=file)) as img:
            img.save(path_to_save, format="JPEG")
            return str(path_to_save)
    except Exception as e:
        raise IOError(f"Failed to save file {e}")


def delete_from_image_store(photo_paths: list[str | Path]):
    """deletes images from the file store"""
    for path in photo_paths:
        item: Path = Path(path)
        if item.is_file():
            item.unlink(missing_ok=True)
