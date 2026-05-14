import logging
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from django.conf import settings

logger = logging.getLogger(__name__)

class AzureBlobService:
    def __init__(self):
        self.account_name = settings.AZURE_ACCOUNT_NAME
        self.account_key = settings.AZURE_ACCOUNT_KEY
        self.container_name = settings.AZURE_MEDIA_CONTAINER
        self.custom_domain = settings.AZURE_CUSTOM_DOMAIN
        
        self.connection_string = (
            f"DefaultEndpointsProtocol=https;"
            f"AccountName={self.account_name};"
            f"AccountKey={self.account_key};"
            f"EndpointSuffix=core.windows.net"
        )
        
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
        except Exception as e:
            logger.error(f"Azure Storage Initialization Error: {e}")

    def upload_recording(self, file_content, phone_number):
        """
        Uploads call recording to Azure Blob Storage.
        file_content: bytes or file-like object
        phone_number: string for filename
        Returns: Public URL of the uploaded blob
        """
        if not settings.USE_AZURE_MEDIA:
            logger.info("Azure Storage is disabled in settings.")
            return None

        # Create unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"recording_{phone_number}_{timestamp}.mp3"
        
        try:
            # Ensure container exists (from your sample logic)
            try:
                self.container_client.get_container_properties()
            except Exception:
                logger.info(f"Creating container '{self.container_name}'...")
                self.container_client.create_container()

            blob_client = self.container_client.get_blob_client(filename)
            blob_client.upload_blob(file_content, overwrite=True)
            
            # Construct Public URL
            media_url = f"https://{self.custom_domain}/{self.container_name}/{filename}"
            logger.info(f"Uploaded to Azure: {media_url}")
            return media_url

        except Exception as e:
            logger.error(f"Failed to upload to Azure: {e}")
            return None

    def download_and_upload(self, provider_url, phone_number):
        """
        Downloads a file from provider_url and uploads it to Azure.
        Returns: New Azure URL or None if failed.
        """
        import requests
        try:
            logger.info(f"Downloading recording from: {provider_url}")
            resp = requests.get(provider_url, timeout=30)
            if resp.status_code == 200:
                # Successfully downloaded, now upload to Azure
                return self.upload_recording(resp.content, phone_number)
            else:
                logger.error(f"Failed to download recording. Status: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error during download/upload process: {e}")
            return None
