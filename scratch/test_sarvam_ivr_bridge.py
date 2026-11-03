import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.utils import timezone
from conversations.models import SarvamAgent, SarvamCallRecord
from sarvam_ivr_bridge.models import AgentIVRForwardingConfig, IVRForwardedCallLog
from sarvam_ivr_bridge.engine import correlate_ivr_log, try_resolve_ivr_forwarded_caller


def run_test():
    print("🚀 Starting Sarvam IVR Bridge Verification Test...")

    # 1. Fetch or create a test SarvamAgent
    agent, _ = SarvamAgent.objects.get_or_create(
        slug="test-ivr-forwarding-agent",
        defaults={
            "name": "Test IVR Forwarding Agent",
            "org_id": "test_org",
            "workspace_id": "test_ws",
            "app_id": "test_app_123",
            "api_key": "test_key",
            "connection_id": "test_conn",
            "agent_phone": "+917971019486",
            "allocated_minutes": 100.0,
            "is_active": True,
        }
    )

    # 2. Configure IVR Forwarding for this agent
    config, _ = AgentIVRForwardingConfig.objects.get_or_create(
        sarvam_agent=agent,
        defaults={
            "is_active": True,
            "ivr_provider_name": "Voicelink PBX",
            "forwarding_dids": "7971019486, +917971019486",
            "time_window_minutes": 15,
            "match_by_duration": True,
            "auto_update_sarvam_record": True,
        }
    )
    print(f"✅ Config created/verified: {config}")

    # 3. Scenario A: Sarvam CDR arrives first with masked trunk number or 'unknown'
    sarvam_call = SarvamCallRecord.objects.create(
        sarvam_agent=agent,
        interaction_id="20261102/test_ivr_interaction_001",
        phone_number="7971019486",  # Trunk forwarded number
        candidate_name="Valued Customer",
        status="COMPLETED",
        call_type="Inbound Call",
        duration_seconds=75.0,
        start_time=timezone.now(),
    )
    print(f"📞 Created SarvamCallRecord #{sarvam_call.id} with masked number: {sarvam_call.phone_number}")

    # 4. Scenario B: IVR CDR arrives with the customer's real SIM number
    real_sim_number = "9876543210"
    ivr_log = IVRForwardedCallLog.objects.create(
        agent_config=config,
        real_caller_number=real_sim_number,
        forwarded_did="7971019486",
        ivr_call_id="call_ivr_998877",
        call_start_time=timezone.now(),
        duration_seconds=74.0,  # Within 20s tolerance
        disposition="ANSWERED",
    )
    print(f"📥 Created IVRForwardedCallLog #{ivr_log.id} with real caller: {ivr_log.real_caller_number}")

    # 5. Run correlation engine
    matched = correlate_ivr_log(ivr_log)
    print(f"🔄 Correlation result: {matched}")

    sarvam_call.refresh_from_db()
    ivr_log.refresh_from_db()

    print(f"🎯 Post-Correlation Sarvam Call Phone: {sarvam_call.phone_number}")
    print(f"🎯 IVR Log Status: {ivr_log.match_status} (Linked Record: {ivr_log.sarvam_call_record_id})")

    assert matched is True, "Expected correlation to succeed!"
    assert sarvam_call.phone_number == real_sim_number, f"Expected {real_sim_number}, got {sarvam_call.phone_number}"
    assert ivr_log.match_status == "MATCHED", f"Expected MATCHED, got {ivr_log.match_status}"

    print("🎉 ALL TESTS PASSED! Clean, isolated, and working perfectly.")

    # Clean up test records
    ivr_log.delete()
    sarvam_call.delete()
    config.delete()
    agent.delete()
    print("🧹 Test cleanup completed.")


if __name__ == "__main__":
    run_test()
