import io
import os
from typing import Dict, Union, Any

from chainlit.data.storage_clients.base import BaseStorageClient
from chainlit.logger import logger
from minio import Minio

import rag_system.utils.settings as settings
class MinioStorageClient(BaseStorageClient):

    def __init__(self):
        try:
            self.client = Minio(endpoint=settings.configuration.minio_endpoint,
                                access_key=settings.configuration.minio_access_key,
                                secret_key=settings.configuration.minio_secret_key,
                                secure=False)   # 如果使用https，则secure=True，否则为False
            logger.info("MinioStorageClient initialized")
        except Exception as e:
            logger.warn(f"MinioStorageClient initialization error: {e}")

    async def upload_file(self, object_key: str, data: Union[bytes, str], mime: str = 'application/octet-stream',
                          overwrite: bool = True) -> Dict[str, Any]:
        try:
            if isinstance(data, str):
                data = io.BytesIO(data.encode('utf-8'))
            else:
                data = io.BytesIO(data)
            bucket_name = settings.configuration.minio_bucket_name
            self.client.put_object(bucket_name=bucket_name, object_name=object_key, data=data, length=len(data.getvalue()), content_type=mime)
            # get file url from minio
            url = self.client.get_presigned_url("GET", bucket_name, object_key)
            return {"object_key": object_key, "url": url}
        except Exception as e:
            logger.warn(f"MinioStorageClient, upload_file error: {e}")
            return {}

    async def delete_file(self, object_key: str) -> bool:
        pass

    async def get_read_url(self, object_key: str) -> str:
        pass

