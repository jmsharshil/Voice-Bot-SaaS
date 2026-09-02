import os
import sys
import django

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.models import CallDetailRecord
from bot.services.azure_storage import AzureBlobService

def sync_recordings_to_azure():
    print("☁️ Syncing call recordings to Azure Blob Storage...")
    azure_service = AzureBlobService()
    cdrs = CallDetailRecord.objects.exclude(recording_file_name="")
    synced_count = 0

    for c in cdrs:
        url = c.recording_file_name
        if "blob.core.windows.net" in url:
            print(f"⏩ CDR #{c.id} already on Azure: {url}")
            continue

        print(f"⏳ Uploading CDR #{c.id} recording ({url}) to Azure...")
        azure_url = azure_service.download_and_upload(url, c.phone_number or "unknown")
        if azure_url:
            c.recording_file_name = azure_url
            c.save(update_fields=["recording_file_name"])
            synced_count += 1
            print(f"✅ Uploaded CDR #{c.id} -> {azure_url}")
        else:
            print(f"❌ Failed to upload CDR #{c.id} to Azure")

    print(f"\n🎉 Successfully synced {synced_count} recording files to Azure Blob Storage!")

if __name__ == "__main__":
    sync_recordings_to_azure()
