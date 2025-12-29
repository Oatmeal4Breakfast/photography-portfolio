import uuid
import hashlib
from pathlib import Path
from src.config import Config, EnvType


def sanitize_file(file_name: str) -> str:
    """sanitizes the file and returns a unique file name"""
    stem: str = Path(file_name).stem
    sanitized_stem: str = stem.replace(" ", "_")[:50]
    return f"{sanitized_stem}_{uuid.uuid4().hex[:8]}.jpeg"


def build_photo_url(path: str | None) -> str | None:
    if path is None:
        return None

    config: Config = Config.from_env()

    if config.env_type == EnvType.DEVELOPMENT:
        return f"/{path}"
    else:
        return f"{config.image_store_url}/{path}"


def get_hash(file_data: bytes) -> str:
    """Returns the hashed string of the file"""
    return hashlib.sha256(data=file_data).hexdigest()
