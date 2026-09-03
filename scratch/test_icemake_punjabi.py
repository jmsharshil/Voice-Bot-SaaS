import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent
from conversations.models import ConversationSession
from icemake_bot.strategy import icemake_prepare

def test_icemake_punjabi():
    agent = VoiceAgent.objects.filter(name__icontains="Ice Make").first()
    if not agent:
        print("Ice Make agent not found, skipping DB agent test.")
        return

    session, _ = ConversationSession.objects.get_or_create(
        agent=agent,
        session_id="test_icemake_pa_session"
    )
    
    # Step 0: Greeting
    res0 = icemake_prepare(agent, "", session)
    print("Step 0 static reply:", res0["static_reply"])

    # Step 0 -> Step 1: User says "Punjabi"
    res1 = icemake_prepare(agent, "ਮੈਂ ਪੰਜਾਬੀ ਵਿੱਚ ਗੱਲ ਕਰਨਾ ਚਾਹੁੰਦਾ ਹਾਂ", session)
    print("Step 1 reply (Punjabi selected):", res1["static_reply"])
    assert res1["tts_language"] == "pa", f"Expected 'pa', got {res1['tts_language']}"
    assert "ਨਾਮ" in res1["static_reply"], "Expected Punjabi prompt asking for name"

    # Step 1 -> Step 2: Name
    res2 = icemake_prepare(agent, "ਮੇਰਾ ਨਾਮ ਗੁਰਪ੍ਰੀਤ ਹੈ", session)
    print("Step 2 reply (State ask):", res2["static_reply"])
    assert res2["tts_language"] == "pa"

    print("✅ All Punjabi Ice Make tests passed successfully!")

if __name__ == "__main__":
    test_icemake_punjabi()
