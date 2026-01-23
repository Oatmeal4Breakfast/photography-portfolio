import boto3
import botocore
import httpx

from pydantic import BaseModel

from src.dependencies.config import Config


class SignedURLParams(BaseModel):
    Bucket: str
    Key: str
    ContentType: str


class ImageStore:
    def __init__(self, config: Config) -> None:
        print(f"R2 Account Id: {config.r2_account_id}")
        self.r2_client: botocore.client.BaseClient = boto3.client(
            service_name="s3",
            endpoint_url=f"https://{config.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            region_name="auto",
        )
        self.bucket: str = config.bucket

    def _get_put_signed_url(self, params: SignedURLParams, ttl: int) -> str:
        "Genereate presigned url for put/patch/post requests returns a string"
        return self.r2_client.generate_presigned_url(
            "put_object", Params=params.model_dump(), ExpiresIn=ttl
        )

    async def upload_image(
        self, params: SignedURLParams, ttl: int, file_data: bytes
    ) -> int:
        """send the upload request to the signed URL"""
        url: str = self._get_put_signed_url(params, ttl)
        async with httpx.AsyncClient() as client:
            response = await client.put(
                url, content=file_data, headers={"Content-Type": params.ContentType}
            )
            response.raise_for_status()
            return response.status_code

        """deletes objects from the image store"""

    def delete_images(self, images: list[str]) -> tuple[list[str], list[str]]:
        """deletes a list of images from the image store"""
        objects: list[dict[str, str]] = [{"Key": image} for image in images]
        delete: dict[str, list] = {"Objects": objects}
        results: dict = self.r2_client.delete_objects(Bucket=self.bucket, Delete=delete)

        errors: list[str] = results.get("Errors")
        success: list[str] = results.get("Deleted")

        return success, errors
