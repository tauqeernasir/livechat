"""Storage utility for handling file uploads to S3-compatible storage."""

import aiobotocore.session
from typing import Optional
from app.core.config import settings
from app.core.logging import logger


class StorageService:
    """Utility service for interacting with S3-compatible storage (e.g., MinIO)."""

    def __init__(self):
        self.session = aiobotocore.session.get_session()
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION

    async def upload_file(self, file_content: bytes, file_path: str, content_type: str = "image/png") -> Optional[str]:
        """Upload a file to S3.

        Args:
            file_content: Raw bytes of the file.
            file_path: Destination path in the bucket.
            content_type: MIME type of the file.

        Returns:
            Optional[str]: The URL/Path of the uploaded file if successful.
        """
        try:
            async with self.session.create_client(
                's3',
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            ) as s3:
                # Ensure bucket exists (optional, could be done at startup)
                try:
                    await s3.head_bucket(Bucket=self.bucket_name)
                except:
                    logger.info("creating_s3_bucket", bucket=self.bucket_name)
                    await s3.create_bucket(Bucket=self.bucket_name)

                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=file_path,
                    Body=file_content,
                    ContentType=content_type
                )
                
                logger.info("file_uploaded_to_s3", path=file_path, bucket=self.bucket_name)
                return f"{self.bucket_name}/{file_path}"
        except Exception as e:
            logger.exception("s3_upload_failed", error=str(e), path=file_path)
            return None

    async def get_file(self, file_key: str) -> Optional[bytes]:
        """Download a file from S3."""
        try:
            async with self.session.create_client(
                's3',
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            ) as s3:
                response = await s3.get_object(Bucket=self.bucket_name, Key=file_key)
                async with response['Body'] as stream:
                    return await stream.read()
        except Exception as e:
            logger.exception("s3_download_failed", error=str(e), key=file_key)
            return None


storage_utils = StorageService()
