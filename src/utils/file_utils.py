from pathlib import Path
from src.config import Config, EnvType


def build_photo_url(path: str | None) -> str | None:
    """builds the url for the photo e.g. 'https://localhost:800/uploads/thumbnail/img.jpeg'"""
    if path is None:
        return None

    config: Config = Config()

    if config.env_type == EnvType.DEVELOPMENT:
        return f"/{path}"
    else:
        return f"{config.image_store_url}/{path}"
