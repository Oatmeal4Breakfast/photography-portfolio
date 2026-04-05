import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from logging.handlers import RotatingFileHandler

from src.dependencies.config import Config, EnvType
from src.dependencies.logging import get_logger


@pytest.fixture
def dev_config() -> Config:
    return Config(
        db_uri="sqlite:///:memory:",
        env_type=EnvType.DEVELOPMENT,
        image_store="localhost",
        secret_key="fake_secret_abc",
        algorithm="HS256",
        auth_token_expire_minute=15,
        max_image_size=10485760,
        r2_account_id="",
        aws_access_key_id="",
        aws_secret_access_key="",
        bucket="",
    )


@pytest.fixture
def prod_config() -> Config:
    return Config(
        db_uri="sqlite:///:memory:",
        env_type=EnvType.PRODUCTION,
        image_store="localhost",
        secret_key="fake_secret_abc",
        algorithm="HS256",
        auth_token_expire_minute=15,
        max_image_size=10485760,
        r2_account_id="",
        aws_access_key_id="",
        aws_secret_access_key="",
        bucket="",
    )


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Remove all handlers from loggers created during each test to prevent cross-test pollution."""
    yield
    for name, logger in list(logging.Logger.manager.loggerDict.items()):
        if name.startswith("test_logger_"):
            if isinstance(logger, logging.Logger):
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)


class TestGetLoggerDevelopment:
    def test_returns_logger_instance(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

            result: logging.Logger = get_logger(
                name="test_logger_dev_returns_instance", config=dev_config
            )

            assert isinstance(result, logging.Logger)

    def test_log_level_is_debug(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

            logger: logging.Logger = get_logger(
                name="test_logger_dev_log_level", config=dev_config
            )

            file_handler = next(
                h for h in logger.handlers if isinstance(h, MagicMock)
            )
            stream_handler = next(
                h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, MagicMock)
            )

            file_handler.setLevel.assert_called_with(level=logging.DEBUG)
            assert stream_handler.level == logging.DEBUG

    def test_file_path_is_app_log(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

            get_logger(name="test_logger_dev_file_path", config=dev_config)

            call_kwargs = mock_rfh.call_args
            assert call_kwargs.kwargs["filename"] == "app.log"

    def test_rotating_file_handler_configured(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

            get_logger(name="test_logger_dev_rfh_config", config=dev_config)

            mock_rfh.assert_called_once_with(
                filename="app.log",
                maxBytes=(5 * 1024 * 1024),
                backupCount=3,
                encoding="utf-8",
            )

    def test_both_handlers_are_added(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

            logger: logging.Logger = get_logger(
                name="test_logger_dev_both_handlers", config=dev_config
            )

            assert len(logger.handlers) == 2

    def test_stream_handler_is_added(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

            logger: logging.Logger = get_logger(
                name="test_logger_dev_stream_handler", config=dev_config
            )

            stream_handlers = [
                h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, MagicMock)
            ]
            assert len(stream_handlers) == 1

    def test_rotating_file_handler_is_added(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_handler = MagicMock(spec=RotatingFileHandler)
            mock_rfh.return_value = mock_handler

            logger: logging.Logger = get_logger(
                name="test_logger_dev_rfh_added", config=dev_config
            )

            assert mock_handler in logger.handlers


class TestGetLoggerProduction:
    def test_returns_logger_instance(self, prod_config: Config) -> None:
        mock_dirs = MagicMock()
        mock_dirs.user_log_path = Path("/mock/log/dir")

        with patch("src.dependencies.logging.PlatformDirs", return_value=mock_dirs):
            with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
                mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

                result: logging.Logger = get_logger(
                    name="test_logger_prod_returns_instance", config=prod_config
                )

                assert isinstance(result, logging.Logger)

    def test_log_level_is_info(self, prod_config: Config) -> None:
        mock_dirs = MagicMock()
        mock_dirs.user_log_path = Path("/mock/log/dir")

        with patch("src.dependencies.logging.PlatformDirs", return_value=mock_dirs):
            with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
                mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

                logger: logging.Logger = get_logger(
                    name="test_logger_prod_log_level", config=prod_config
                )

                file_handler = next(
                    h for h in logger.handlers if isinstance(h, MagicMock)
                )
                stream_handler = next(
                    h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, MagicMock)
                )

                file_handler.setLevel.assert_called_with(level=logging.INFO)
                assert stream_handler.level == logging.INFO

    def test_file_path_uses_platform_dirs(self, prod_config: Config) -> None:
        mock_dirs = MagicMock()
        mock_log_path = Path("/mock/log/dir")
        mock_dirs.user_log_path = mock_log_path

        with patch("src.dependencies.logging.PlatformDirs", return_value=mock_dirs):
            with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
                mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

                get_logger(name="test_logger_prod_file_path", config=prod_config)

                call_kwargs = mock_rfh.call_args
                assert call_kwargs.kwargs["filename"] == mock_log_path / "app.log"

    def test_platform_dirs_initialized_with_correct_args(self, prod_config: Config) -> None:
        mock_dirs = MagicMock()
        mock_dirs.user_log_path = Path("/mock/log/dir")

        with patch("src.dependencies.logging.PlatformDirs", return_value=mock_dirs) as mock_platform_dirs:
            with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
                mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

                get_logger(name="test_logger_prod_platform_dirs_args", config=prod_config)

                mock_platform_dirs.assert_called_once_with(
                    appname="photo-portfolio",
                    appauthor="Oatmeal4Breakfast",
                    ensure_exists=True,
                )

    def test_both_handlers_are_added(self, prod_config: Config) -> None:
        mock_dirs = MagicMock()
        mock_dirs.user_log_path = Path("/mock/log/dir")

        with patch("src.dependencies.logging.PlatformDirs", return_value=mock_dirs):
            with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
                mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

                logger: logging.Logger = get_logger(
                    name="test_logger_prod_both_handlers", config=prod_config
                )

                assert len(logger.handlers) == 2


class TestGetLoggerHandlerCaching:
    def test_calling_twice_returns_same_logger(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

            logger_first: logging.Logger = get_logger(
                name="test_logger_caching_same_instance", config=dev_config
            )
            logger_second: logging.Logger = get_logger(
                name="test_logger_caching_same_instance", config=dev_config
            )

            assert logger_first is logger_second

    def test_calling_twice_does_not_add_duplicate_handlers(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

            get_logger(name="test_logger_caching_no_duplicates", config=dev_config)
            logger: logging.Logger = get_logger(
                name="test_logger_caching_no_duplicates", config=dev_config
            )

            assert len(logger.handlers) == 2

    def test_rotating_file_handler_created_only_once(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

            get_logger(name="test_logger_caching_rfh_once", config=dev_config)
            get_logger(name="test_logger_caching_rfh_once", config=dev_config)

            mock_rfh.assert_called_once()

    def test_different_names_return_different_loggers(self, dev_config: Config) -> None:
        with patch("src.dependencies.logging.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = MagicMock(spec=RotatingFileHandler)

            logger_a: logging.Logger = get_logger(
                name="test_logger_caching_diff_a", config=dev_config
            )
            logger_b: logging.Logger = get_logger(
                name="test_logger_caching_diff_b", config=dev_config
            )

            assert logger_a is not logger_b
