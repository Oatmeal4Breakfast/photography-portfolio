import pytest
import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from typing import Any, Generator
from datetime import datetime, timedelta, timezone

from src.models.schema import Base, User
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
def test_db() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestAuthService:
    def test_admin_does_not_exist(self, test_db: Session, test_config: Config) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        assert not service.admin_exists()

    def test_admin_exists(self, test_db: Session, test_config: Config) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        service.create_user(
            firstname="Thoughts",
            lastname="Stopped",
            email="flastname@example.com",
            password="password123",
        )
        assert service.admin_exists()

    def test_create_user(self, test_db: Session, test_config: Config) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        results: bool = service.create_user(
            firstname="Thoughts",
            lastname="Stopped",
            email="flastname@example.com",
            password="password123",
        )

        user: User | None = service.get_user_by_email(email="flastname@example.com")

        assert results
        assert user is not None
        assert user.firstname == "Thoughts"
        assert user.lastname == "Stopped"
        assert user.email == "flastname@example.com"
        assert user.hashed_password != "password123"

    def test_create_user_fails(self, test_db: Session, test_config: Config) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        service.create_user(
            firstname="No",
            lastname="Thoughts",
            email="flastname@example.com",
            password="password123",
        )
        with pytest.raises(IntegrityError):
            service.create_user(
                firstname="Thoughts",
                lastname="Stopped",
                email="flastname@example.com",
                password="password456",
            )

    def test_verify_password(self, test_db: Session, test_config: Config) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        password: str = "password123"
        service.create_user(
            firstname="Thoughts",
            lastname="Stopped",
            email="flastname@example.com",
            password=password,
        )
        user: User | None = service.get_user_by_email(email="flastname@example.com")

        assert user is not None
        assert service.verify_password(
            plain_password=password, hashed_password=user.hashed_password
        )

    def test_verify_password_fails(self, test_db: Session, test_config: Config) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        password: str = "password123"
        service.create_user(
            firstname="Thoughts",
            lastname="Stopped",
            email="flastname@example.com",
            password="password456",
        )
        user: User | None = service.get_user_by_email(email="flastname@example.com")

        assert user is not None
        assert not service.verify_password(
            plain_password=password, hashed_password=user.hashed_password
        )

    def test_get_password_hash(self, test_db: Session, test_config: Config) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        password: str = "password"
        hashed_password: str = service.get_password_hash(password=password)
        hashed_password_2: str = service.get_password_hash(password=password)

        assert isinstance(hashed_password, str)
        assert password != hashed_password
        assert hashed_password != hashed_password_2

    def test_get_user_by_email(self, test_db: Session, test_config: Config) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        service.create_user(
            firstname="Thoughts",
            lastname="Stopped",
            email="flastname@example.com",
            password="password123",
        )
        user: User | None = service.get_user_by_email(email="flastname@example.com")

        assert isinstance(user, User)

    def test_get_user_by_email_returns_none(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        service.create_user(
            firstname="Thoughts",
            lastname="Stopped",
            email="flastname@example.com",
            password="password123",
        )
        user: User | None = service.get_user_by_email(email="flastname1@example.com")

        assert user is None

    def test_authenticate_user_success(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        email: str = "flastname@example.com"
        password: str = "password123"
        service.create_user(
            firstname="Thoughts", lastname="Stopped", email=email, password=password
        )
        user: User | None = service.authenticate_user(email=email, password=password)

        assert user is not None
        assert user.email == email

    def test_authenticate_user_not_exist(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        password: str = "password123"
        service.create_user(
            firstname="Thoughts",
            lastname="Stopped",
            email="flastname@example.com",
            password=password,
        )

        failing_email: str = "flastname1@example.com"

        user: User | None = service.authenticate_user(
            email=failing_email, password=password
        )

        assert user is None

    def test_authenticate_user_password_fail(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        failing_password: str = "password321"
        email: str = "flastname@example.com"
        service.create_user(
            firstname="Thoughts",
            lastname="Stopped",
            email=email,
            password="password123",
        )
        user: User | None = service.authenticate_user(
            email=email, password=failing_password
        )

        assert user is None

    def test_create_access_token_success(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        data: dict[str, Any] = {"sub": "flastname@example.com"}
        test_token: str = service.create_access_token(data=data)

        assert isinstance(test_token, str)
        assert len(test_token) > 0

        payload: dict[str, Any] = jwt.decode(
            jwt=test_token,
            key=test_config.secret_key,
            algorithms=[test_config.algorithm],
        )

        assert data.get("sub") == payload.get("sub")
        assert "exp" in payload
        exp_time: datetime = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp: datetime = datetime.now(timezone.utc) + timedelta(minutes=15)
        time_diff: timedelta = abs(exp_time - expected_exp)
        assert time_diff < timedelta(seconds=5)

    def test_create_access_token_with_custom_expiration(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        data: dict[str, Any] = {"sub": "flastname@example.com"}
        custom_delta: timedelta = timedelta(hours=1)
        test_token: str = service.create_access_token(
            data=data, expires_delta=custom_delta
        )

        payload: dict[str, Any] = jwt.decode(
            jwt=test_token,
            key=test_config.secret_key,
            algorithms=[test_config.algorithm],
        )

        assert data.get("sub") == payload.get("sub")
        exp_time: datetime = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp: datetime = datetime.now(timezone.utc) + timedelta(hours=1)
        time_diff: timedelta = abs(exp_time - expected_exp)
        assert time_diff < timedelta(seconds=5)

    def test_verify_access_token_success(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        email: str = "flastname@example.com"

        service.create_user(
            firstname="Thoughts",
            lastname="Stopped",
            email=email,
            password="password123",
        )

        token: str = service.create_access_token(data={"sub": email})

        user: User | None = service.verify_access_token(token)

        assert user is not None
        assert user.email == email

    def test_verify_access_token_invalid_token(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)

        user: User | None = service.verify_access_token("invalid_token_string")

        assert user is None

    def test_verify_access_token_expired_token(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)
        email: str = "flastname@example.com"

        service.create_user(
            firstname="Thoughts",
            lastname="Stopped",
            email=email,
            password="password123",
        )

        expired_token: str = service.create_access_token(
            data={"sub": email}, expires_delta=timedelta(seconds=-1)
        )

        user: User | None = service.verify_access_token(expired_token)

        assert user is None

    def test_verify_access_token_user_not_found(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: AuthService = AuthService(db=test_db, config=test_config)

        token: str = service.create_access_token(
            data={"sub": "nonexistent@example.com"}
        )

        user: User | None = service.verify_access_token(token)

        assert user is None
