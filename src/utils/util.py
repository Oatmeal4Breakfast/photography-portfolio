from src.dependencies.config import Config, EnvType


def build_photo_url(config: Config, path: str) -> str:
    """
    build the path for the image based on the image store

    e.g. https://cloudflare.r2.com/your/bucket/image_120412.jpeg
    """
    if config.env_type == EnvType.DEVELOPMENT:
        return f"/{path}"
    return f"{config.image_store}/{path}"
