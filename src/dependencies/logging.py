import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from platformdirs import PlatformDirs
from src.dependencies.config import Config, EnvType


def get_logger(name: str, config: Config) -> logging.Logger:
    logger = logging.getLogger(name=name)

    if logger.handlers:
        return logger

    if config.env_type == EnvType.DEVELOPMENT:
        log_file: Path | str = "app.log"
        log_level = logging.DEBUG
    elif config.env_type == EnvType.PRODUCTION:
        dirs = PlatformDirs(
            appname="photo-portfolio", appauthor="Oatmeal4Breakfast", ensure_exists=True
        )
        log_file: Path = dirs.user_log_path / "app.log"
        log_level = logging.INFO

    format = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler: RotatingFileHandler = RotatingFileHandler(
        filename=log_file, maxBytes=(5 * 1024 * 1024), backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(level=log_level)
    file_handler.setFormatter(fmt=format)

    logger.addHandler(hdlr=file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level=log_level)
    stream_handler.setFormatter(fmt=format)

    logger.addHandler(hdlr=stream_handler)

    return logger
