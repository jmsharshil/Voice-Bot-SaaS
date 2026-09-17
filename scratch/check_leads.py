import os
import django
import sys

# Set encoding for output
sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voice_bot.settings')
django.setup()

from conversations.models import LeadAnalysis, CallDetailRecord

print("--- Checking Unmatched CDRs ---")
unmatched = CallDetailRecord.objects.filter(matched=False).order_by('-received_at')[:20]
for cdr in unmatched:
    print(f"CDR ID: {cdr.id} | Phone: {cdr.phone_number} | Recording: {cdr.recording_file_name}")

print("\n--- Checking Matched CDRs ---")
matched = CallDetailRecord.objects.filter(matched=True).order_by('-received_at')[:10]
for cdr in matched:
    print(f"CDR ID: {cdr.id} | Phone: {cdr.phone_number} | Recording: {cdr.recording_file_name}")
