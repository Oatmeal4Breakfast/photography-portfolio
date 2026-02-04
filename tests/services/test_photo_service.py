import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Sequence

from src.models.schema import Base, Photo
from src.services.photo_service import PhotoService
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


@pytest.fixture
def create_photo(test_db: Session):
    def _create_photo(
        title: str = "test_photo",
        hash: str = "hash123",
        file_name: str = "test_file.jpeg",
        original_path: str | None = None,
        thumbnail_path: str | None = None,
        collection: str = "test",
    ) -> Photo:
        if original_path is None:
            original_path = f"some/path/original/{file_name}"
        if thumbnail_path is None:
            thumbnail_path = f"some/path/thumbnail/{file_name}"

        photo: Photo = Photo(
            title=title,
            hash=hash,
            file_name=file_name,
            original_path=original_path,
            thumbnail_path=thumbnail_path,
            collection=collection,
        )
        test_db.add(photo)
        test_db.commit()
        test_db.refresh(photo)
        return photo

    return _create_photo


class TestPhotoService:
    def test_get_photo_by_hash(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        photo_hash: str = "hash123"
        create_photo(hash=photo_hash)

        result: Photo | None = service.get_photo_by_hash(hash=photo_hash)

        assert result is not None
        assert result.hash == photo_hash
        assert result.title == "test_photo"
        assert result.collection == "test"

    def test_get_photo_by_hash_returns_none(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        create_photo(hash="hash123")

        result: Photo | None = service.get_photo_by_hash(hash="non_existing_hash")

        assert result is None

    def test_get_photo_by_id(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        photo: Photo = create_photo()

        result: Photo | None = service.get_photo_by_id(id=photo.id)

        assert result is not None
        assert result.id == photo.id
        assert result.title == "test_photo"
        assert result.hash == "hash123"

    def test_get_photo_by_id_returns_none(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        create_photo()

        result: Photo | None = service.get_photo_by_id(id=999)

        assert result is None

    def test_get_photos_by_collection_empty(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)

        result: Sequence[Photo] = service.get_photos_by_collection(
            collection_name="nonexistent"
        )

        assert len(result) == 0

    def test_get_photos_by_collection_single(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        create_photo(collection="nature")

        result: Sequence[Photo] = service.get_photos_by_collection(
            collection_name="nature"
        )

        assert len(result) == 1
        assert result[0].collection == "nature"

    def test_get_photos_by_collection_multiple(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        create_photo(
            title="photo1", hash="hash1", file_name="photo1.jpeg", collection="nature"
        )
        create_photo(
            title="photo2", hash="hash2", file_name="photo2.jpeg", collection="nature"
        )
        create_photo(
            title="photo3", hash="hash3", file_name="photo3.jpeg", collection="urban"
        )

        result: Sequence[Photo] = service.get_photos_by_collection(
            collection_name="nature"
        )

        assert len(result) == 2
        assert all(photo.collection == "nature" for photo in result)

    def test_get_hero_photo(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        hero_path: str = "uploads/original/hero_image.jpeg"
        create_photo(file_name="hero_image.jpeg", original_path=hero_path)

        result: str | None = service.get_hero_photo()

        assert result is not None
        assert result == hero_path

    def test_get_hero_photo_returns_none(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        create_photo(file_name="landscape.jpeg")

        result: str | None = service.get_hero_photo()

        assert result is None

    def test_get_about_image(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        photo: Photo = create_photo(collection="about_me")

        result: Photo | None = service.get_about_image()

        assert result is not None
        assert result.collection == "about_me"
        assert result.id == photo.id

    def test_get_about_image_returns_none(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        create_photo(collection="nature")

        result: Photo | None = service.get_about_image()

        assert result is None

    def test_get_unique_collections_empty(
        self, test_db: Session, test_config: Config
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)

        result: list[str] = service.get_unique_collections()

        assert len(result) == 0
        assert isinstance(result, list)

    def test_get_unique_collections_single(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        create_photo(collection="nature")

        result: list[str] = service.get_unique_collections()

        assert len(result) == 1
        assert "nature" in result

    def test_get_unique_collections_multiple(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        create_photo(hash="hash1", file_name="photo1.jpeg", collection="nature")
        create_photo(hash="hash2", file_name="photo2.jpeg", collection="urban")
        create_photo(hash="hash3", file_name="photo3.jpeg", collection="portrait")

        result: list[str] = service.get_unique_collections()

        assert len(result) == 3
        assert "nature" in result
        assert "urban" in result
        assert "portrait" in result

    def test_get_unique_collections_with_duplicates(
        self, test_db: Session, test_config: Config, create_photo
    ) -> None:
        service: PhotoService = PhotoService(db=test_db, config=test_config)
        create_photo(hash="hash1", file_name="photo1.jpeg", collection="nature")
        create_photo(hash="hash2", file_name="photo2.jpeg", collection="nature")
        create_photo(hash="hash3", file_name="photo3.jpeg", collection="urban")

        result: list[str] = service.get_unique_collections()

        assert len(result) == 2
        assert "nature" in result
        assert "urban" in result
