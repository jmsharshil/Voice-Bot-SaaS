import os
import sys
import django

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.models import CallDetailRecord

def restore_cdn_urls():
    print("🔄 Restoring high-speed CDN URLs for all CallDetailRecord entries...")
    cdrs = CallDetailRecord.objects.filter(recording_file_name__icontains="media/recordings")
    count = 0
    for c in cdrs:
        filename = os.path.basename(c.recording_file_name)
        cdn_url = f"https://voiceflowai.elisiontec.com/voiceapp-recordings/client_1616/2026-08-31/{filename}"
        c.recording_file_name = cdn_url
        c.save(update_fields=["recording_file_name"])
        count += 1
        print(f"✅ Restored CDR #{c.id} -> {cdn_url}")

    print(f"\n🎉 Successfully restored {count} recording URLs to high-speed CDN URLs!")

if __name__ == "__main__":
    restore_cdn_urls()
