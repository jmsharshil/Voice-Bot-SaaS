import os
import sys
import django

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.models import CallDetailRecord, Conversation
from icemake_bot.models import IcemakeTicket

def fix_cdr_links():
    print("🔧 Repairing CDR links for Ice Make conversations...")
    
    # 1. Match unlinked CDRs by uniqueid -> Conversation.stream_sid
    unlinked_cdrs = CallDetailRecord.objects.filter(recording_file_name__gt="").order_by("-id")
    fixed_count = 0

    for cdr in unlinked_cdrs:
        if cdr.conversation:
            continue
            
        uid = cdr.uniqueid or ""
        conv = None
        if uid:
            conv = Conversation.objects.filter(stream_sid=uid).first()
            if not conv:
                conv = Conversation.objects.filter(stream_sid=f"stream_{uid}").first()
            if not conv and uid.startswith("stream_"):
                conv = Conversation.objects.filter(stream_sid=uid[7:]).first()

        if not conv and cdr.phone_number:
            clean_p = "".join(filter(str.isdigit, cdr.phone_number))[-10:]
            if clean_p:
                conv = Conversation.objects.filter(
                    user_number__icontains=clean_p,
                    strategy_key="icemake"
                ).order_by("-started_at").first()

        if conv:
            # Delete any empty dummy CDR on that conv if present
            CallDetailRecord.objects.filter(conversation=conv, recording_file_name="").delete()
            cdr.conversation = conv
            cdr.save()
            fixed_count += 1
            print(f"✅ Linked CDR #{cdr.id} ({cdr.recording_file_name}) -> Conversation #{conv.id}")

    print(f"\n🎉 Successfully repaired {fixed_count} CDR recording links!")

if __name__ == "__main__":
    fix_cdr_links()
