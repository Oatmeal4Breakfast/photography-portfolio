import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Sequence
from io import BytesIO
from PIL import Image

from src.models.schema import Base, Photo
from src.services.admin_service import AdminService
from src.dependencies.config import Config, EnvType
from src.dependencies.store import ImagePaths


class MockImageStore:
    def __init__(self) -> None:
        self.uploaded_images: dict[str, bytes] = {}
        self.deleted_paths: list[str] = []

    async def upload_image(self, file_data: bytes, path_to_save: str) -> bool:
        self.uploaded_images[path_to_save] = file_data
        return True

    async def delete_images(
        self, image_paths: ImagePaths
    ) -> tuple[ImagePaths, ImagePaths]:
        success: ImagePaths = []
        errors: ImagePaths = []
        for path in image_paths:
            if path in self.uploaded_images:
                del self.uploaded_images[path]
                success.append(path)
                self.deleted_paths.append(path)
            else:
                errors.append(path)
        return success, errors


@pytest.fixture
def test_config() -> Config:
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
def test_db() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def mock_store() -> MockImageStore:
    return MockImageStore()


@pytest.fixture
def test_image_bytes() -> bytes:
    img: Image.Image = Image.new("RGB", (100, 100), color="red")
    buffer: BytesIO = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


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
            original_path = f"uploads/original/{file_name}"
        if thumbnail_path is None:
            thumbnail_path = f"uploads/thumbnail/{file_name}"

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


class TestAdminService:
    def test_photo_hash_exists(
        self, test_db: Session, test_config: Config, mock_store: MockImageStore, create_photo
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )
        photo_hash: str = "abc123"
        create_photo(hash=photo_hash)

        result: bool = service.photo_hash_exists(hash=photo_hash)

        assert result is True

    def test_photo_hash_does_not_exist(
        self, test_db: Session, test_config: Config, mock_store: MockImageStore
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )

        result: bool = service.photo_hash_exists(hash="nonexistent")

        assert result is False

    def test_get_all_photos_empty(
        self, test_db: Session, test_config: Config, mock_store: MockImageStore
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )

        result: Sequence[Photo] = service.get_all_photos()

        assert len(result) == 0

    def test_get_all_photos_multiple(
        self, test_db: Session, test_config: Config, mock_store: MockImageStore, create_photo
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )
        create_photo(hash="hash1", file_name="photo1.jpeg")
        create_photo(hash="hash2", file_name="photo2.jpeg")
        create_photo(hash="hash3", file_name="photo3.jpeg")

        result: Sequence[Photo] = service.get_all_photos()

        assert len(result) == 3

    def test_get_photo_by_id(
        self, test_db: Session, test_config: Config, mock_store: MockImageStore, create_photo
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )
        photo: Photo = create_photo()

        result: Photo | None = service.get_photo_by_id(id=photo.id)

        assert result is not None
        assert result.id == photo.id
        assert result.hash == "hash123"

    def test_get_photo_by_id_returns_none(
        self, test_db: Session, test_config: Config, mock_store: MockImageStore
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )

        result: Photo | None = service.get_photo_by_id(id=999)

        assert result is None

    @pytest.mark.asyncio
    async def test_upload_photo_success(
        self,
        test_db: Session,
        test_config: Config,
        mock_store: MockImageStore,
        test_image_bytes: bytes,
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )

        result: Photo | None = await service.upload_photo(
            title="sunset",
            file_name="sunset.jpg",
            file_data=test_image_bytes,
            collection="nature",
        )

        assert result is not None
        assert result.title == "sunset"
        assert result.collection == "nature"
        assert "sunset" in result.file_name
        assert result.hash is not None
        assert len(mock_store.uploaded_images) == 2

    @pytest.mark.asyncio
    async def test_upload_photo_with_none_filename(
        self,
        test_db: Session,
        test_config: Config,
        mock_store: MockImageStore,
        test_image_bytes: bytes,
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )

        result: Photo | None = await service.upload_photo(
            title="test",
            file_name=None,
            file_data=test_image_bytes,
            collection="test",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_upload_photo_duplicate_hash(
        self,
        test_db: Session,
        test_config: Config,
        mock_store: MockImageStore,
        test_image_bytes: bytes,
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )

        await service.upload_photo(
            title="first",
            file_name="first.jpg",
            file_data=test_image_bytes,
            collection="test",
        )

        with pytest.raises(ValueError, match="Duplicate Photo"):
            await service.upload_photo(
                title="second",
                file_name="second.jpg",
                file_data=test_image_bytes,
                collection="test",
            )

    @pytest.mark.asyncio
    async def test_delete_photos_success(
        self,
        test_db: Session,
        test_config: Config,
        mock_store: MockImageStore,
        test_image_bytes: bytes,
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )

        photo: Photo | None = await service.upload_photo(
            title="to_delete",
            file_name="delete_me.jpg",
            file_data=test_image_bytes,
            collection="test",
        )

        assert photo is not None

        await service.delete_photos(photos=[photo])

        result: Photo | None = service.get_photo_by_id(id=photo.id)
        assert result is None
        assert len(mock_store.deleted_paths) == 2

    @pytest.mark.asyncio
    async def test_delete_photos_multiple(
        self,
        test_db: Session,
        test_config: Config,
        mock_store: MockImageStore,
        test_image_bytes: bytes,
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )

        img1: Image.Image = Image.new("RGB", (50, 50), color="blue")
        buffer1: BytesIO = BytesIO()
        img1.save(buffer1, format="JPEG")
        image_bytes_1: bytes = buffer1.getvalue()

        photo1: Photo | None = await service.upload_photo(
            title="photo1",
            file_name="photo1.jpg",
            file_data=image_bytes_1,
            collection="test",
        )

        photo2: Photo | None = await service.upload_photo(
            title="photo2",
            file_name="photo2.jpg",
            file_data=test_image_bytes,
            collection="test",
        )

        assert photo1 is not None
        assert photo2 is not None

        await service.delete_photos(photos=[photo1, photo2])

        result1: Photo | None = service.get_photo_by_id(id=photo1.id)
        result2: Photo | None = service.get_photo_by_id(id=photo2.id)

        assert result1 is None
        assert result2 is None
        assert len(mock_store.deleted_paths) == 4

    @pytest.mark.asyncio
    async def test_delete_photos_partial_failure(
        self, test_db: Session, test_config: Config, mock_store: MockImageStore, create_photo
    ) -> None:
        service: AdminService = AdminService(
            db=test_db, config=test_config, store=mock_store
        )

        photo: Photo = create_photo()

        await service.delete_photos(photos=[photo])

        result: Photo | None = service.get_photo_by_id(id=photo.id)
        assert result is not None
        assert len(mock_store.deleted_paths) == 0
