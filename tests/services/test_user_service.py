from uvicorn.protocols.http.auto import AutoHTTPProtocol
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.models.schema import Base
from src.services.user_service import AuthService
from src.dependencies.config import Config, EnvType


@pytest.fixture
def test_config() -> Config:
    return Config(
        db_uri="sqlite:///:memory:",
        env_type=EnvType.DEVELOPMENT,
        image_store="localhost",
        secret_key="fake_secret_abc",
        algorithm="HS256",
        auth_token_expire_minute=15,
        max_image_size=1098,
        r2_account_id="",
        aws_access_key_id="",
        aws_secret_access_key="",
        bucket="",
    )


@pytest.fixture
def test_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestAuthService:
    def test_admin_does_not_exist(self, test_db, test_config):
        service = AuthService(db=test_db, config=test_config)

        assert not service.admin_exists()

    def test_create_user(self, test_db, test_config):
        service = AuthService(db=test_db, config=test_config)
        results = service.create_user(
            firstname="Elvin",
            lastname="Salcedo",
            email="flastname@example.com",
            password="password123",
        )

        user = service.get_user_by_email(email="flastname@example.com")

        assert results
        assert user is not None
        assert user.firstname == "Elvin"
        assert user.lastname == "Salcedo"
        assert user.email == "flastname@example.com"
        assert user.hashed_password != "password123"
