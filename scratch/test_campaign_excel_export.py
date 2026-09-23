import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
import django
django.setup()

from conversations.models import SarvamCampaign, SarvamCampaignLead, SarvamCallRecord, SarvamAgent
from conversations.views import _extract_lead_status_and_reasons
import openpyxl

print("=" * 60)
print("🧪 TESTING CAMPAIGN EXCEL EXPORT & STATUS COLUMN")
print("=" * 60)

# Check if any campaign exists or create a mock lead to test _extract_lead_status_and_reasons
agent = SarvamAgent.objects.filter(is_active=True).first()
camp = SarvamCampaign.objects.first()

if not camp:
    camp = SarvamCampaign.objects.create(
        name="Test Export Campaign",
        sarvam_agent=agent,
        total_leads=4
    )

# Create 4 test leads with various statuses & tags to verify STATUS output
leads_test_data = [
    {
        "name": "Rohan Mehta",
        "phone": "+919876543210",
        "final_status": "ANSWERED",
        "summary": {
            "tags": ["Price Inquiry", "Test Drive Request", "Appointment Confirmed"],
            "call_summary": "Customer inquired about petrol automatic Sonet and booked a test drive on Saturday.",
            "final_status": "INTERESTED"
        },
        "transcript": "Hello, I am looking for Sonet automatic test drive.",
        "duration": 45.0
    },
    {
        "name": "Kiran Patel",
        "phone": "+919876543211",
        "final_status": "ANSWERED",
        "summary": {
            "tags": ["Not Interested", "Already Purchased"],
            "call_summary": "Customer already bought another car last month and is not interested.",
            "final_status": "NOT_INTERESTED"
        },
        "transcript": "No thanks, I already bought another car.",
        "duration": 22.0
    },
    {
        "name": "Suresh Gupta",
        "phone": "+919876543212",
        "final_status": "ANSWERED",
        "summary": {
            "tags": ["Driving", "Callback Requested", "WhatsApp Details"],
            "call_summary": "Customer was driving and asked to send details on WhatsApp.",
            "final_status": "CALLBACK"
        },
        "transcript": "I am driving now, please share details on WhatsApp.",
        "duration": 18.0
    },
    {
        "name": "Deepak Joshi",
        "phone": "+919876543213",
        "final_status": "MISSED_ALL_RETRIES",
        "summary": {},
        "transcript": "",
        "duration": 0.0
    }
]

for item in leads_test_data:
    rec = None
    if item["duration"] > 0:
        rec = SarvamCallRecord.objects.create(
            candidate_name=item["name"],
            phone_number=item["phone"],
            duration_seconds=item["duration"],
            status=item["summary"].get("final_status", "COMPLETED"),
            summary=item["summary"],
            transcript=item["transcript"],
            sarvam_agent=agent
        )
    
    lead = SarvamCampaignLead.objects.create(
        campaign=camp,
        candidate_name=item["name"],
        phone_number=item["phone"],
        stage_1_call=rec,
        stage_1_status="ANSWERED" if item["duration"] > 0 else "MISSED",
        final_status=item["final_status"],
        total_attempts=1 if item["duration"] > 0 else 3
    )

    status_text, call_sum, cat = _extract_lead_status_and_reasons(lead)
    print(f"\nLead: {lead.candidate_name}")
    print(f"  Category:     {cat}")
    print(f"  STATUS Col:   {status_text}")
    print(f"  AI Summary:   {call_sum}")

from django.test import RequestFactory
from conversations.views import sarvam_campaign_export_full_api

factory = RequestFactory()
req = factory.get(f"/api/sarvam/campaigns/{camp.id}/export-full/")
resp = sarvam_campaign_export_full_api(req, camp.id)

print(f"\nExport Response Status Code: {resp.status_code}")
print(f"Content-Type: {resp.get('Content-Type')}")
print(f"Content-Disposition: {resp.get('Content-Disposition')}")
print(f"Excel Byte Length: {len(resp.content)} bytes")

# Read back generated Excel with openpyxl to verify sheet headers
import io
wb = openpyxl.load_workbook(io.BytesIO(resp.content))
ws = wb.active
headers = [cell.value for cell in ws[1]]
print(f"Excel Sheet Headers: {headers}")
assert "STATUS" in headers, "STATUS column missing from headers!"
assert "AI Call Summary" in headers, "AI Call Summary column missing!"

print("\n" + "=" * 60)
print("✅ ALL EXCEL EXPORT & STATUS TESTS PASSED 100%!")
print("=" * 60)
