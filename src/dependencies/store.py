import boto3
import asyncio
import botocore
import aiofiles

from botocore.exceptions import ClientError, EndpointConnectionError, BotoCoreError
from aiofiles import os as aio_os
from functools import partial
from typing import Protocol, List, Tuple

from src.dependencies.config import Config


type ImagePaths = List[str]


class ImageStore(Protocol):
    async def upload_image(self, file_data: bytes, path_to_save: str) -> bool: ...
    async def delete_images(
        self, image_paths: ImagePaths
    ) -> Tuple[ImagePaths, ImagePaths]: ...


class LocalStore:
    async def upload_image(self, file_data: bytes, path_to_save: str) -> bool:
        try:
            async with aiofiles.open(file=path_to_save, mode="wb") as fp:
                await fp.write(file_data)
            return True
        except FileExistsError:
            raise
        except IOError:
            raise

    async def delete_images(
        self, image_paths: ImagePaths
    ) -> Tuple[ImagePaths, ImagePaths]:
        success: ImagePaths = []
        errors: ImagePaths = []
        for image_path in image_paths:
            try:
                await aio_os.unlink(image_path)
                success.append(image_path)
            except FileNotFoundError:
                errors.append(image_path)

        return success, errors


class RemoteStore:
    def __init__(self, config: Config) -> None:
        self.r2_client: botocore.client.BaseClient = boto3.client(
            service_name="s3",
            endpoint_url=f"https://{config.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            region_name="auto",
        )
        self.bucket: str = config.bucket

    async def upload_image(self, file_data: bytes, path_to_save: str) -> bool:
        """send the upload request to the signed URL"""
        put_object_partial = partial(
            self.r2_client.put_object,
            Body=file_data,
            Bucket=self.bucket,
            Key=path_to_save,
        )
        try:
            await asyncio.to_thread(put_object_partial)
            return True
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            raise IOError(f"R2 Upload failed [{error_code}]: {e}")
        except EndpointConnectionError as e:
            raise IOError(f"Cannot connect to endpoint {e}")
        except BotoCoreError as e:
            raise IOError(f"R2 client error: {e}")

    async def delete_images(
        self, image_paths: ImagePaths
    ) -> tuple[ImagePaths, ImagePaths]:
        """deletes a list of images from the image store"""
        objects: list[dict[str, str]] = [
            {"Key": image_path} for image_path in image_paths
        ]
        delete: dict[str, list] = {"Objects": objects}
        delete_object_partial = partial(
            self.r2_client.delete_objects, Bucket=self.bucket, Delete=delete
        )

        try:
            results = await asyncio.to_thread(delete_object_partial)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            raise IOError(f"R2 Delete failed [{error_code}]: {e}")
        except EndpointConnectionError as e:
            raise IOError(f"Cannot connect to endpoint {e}")
        except BotoCoreError as e:
            raise IOError(f"R2 client error: {e}")

        deleted: list[dict] = results.get("Deleted", [])
        failed: list[dict] = results.get("Errors", [])

        success: ImagePaths = [obj["Key"] for obj in deleted]
        errors: ImagePaths = [obj["Key"] for obj in failed]

        return success, errors
