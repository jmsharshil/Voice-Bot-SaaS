# scratch/append_tests.py

import os

test_file_path = r"c:\Users\AYUSHI PATEL\Eleven_labs\Voice-Bot-SaaS\conversations\tests.py"

test_code = """

    def test_samsung_llm_flow(self):
        from conversations.services.core.dialogue_engine import prepare_streaming, get_agent_tts_language, finalize_streaming
        from conversations.models import ConversationSession

        # Test TTS Language
        lang = get_agent_tts_language(self.llm_agent.id)
        self.assertEqual(lang, "gu")

        session_id = "session_samsung_llm_test"

        # 1. Step 1: Greeting
        result = prepare_streaming(self.llm_agent, "hello", session_id=session_id)
        self.assertIn("નમસ્તે", result["static_reply"])
        self.assertIn("નીલ છું", result["static_reply"])

        session = ConversationSession.objects.get(session_id=session_id)
        self.assertEqual(session.state["call_phase"], "ASK_CONSENT")

        # 2. Step 2: GREETING_REPLY / ASK_CONSENT -> LLM fallback
        result = prepare_streaming(self.llm_agent, "હા ચોક્કસ વાત કરો", session_id=session_id)
        self.assertNotIn("static_reply", result)
        self.assertIn("system_prompt", result)
        self.assertEqual(result["user_message"], "હા ચોક્કસ વાત કરો")

        # Finalize the response with mock LLM reply
        mock_reply = "સરસ. તો તમે અત્યારે કયો મોબાઈલ વાપરી રહ્યા છો?"
        finalize_streaming(mock_reply, result)

        session.refresh_from_db()
        self.assertEqual(session.state["call_phase"], "LLM_CONVERSATION")
        self.assertIn("Agent: સરસ. તો તમે અત્યારે કયો મોબાઈલ વાપરી રહ્યા છો?", session.state["conversation_history"])
"""

with open(test_file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Append only if not already present
if "test_samsung_llm_flow" not in content:
    content = content.rstrip() + test_code
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Test method appended successfully!")
else:
    print("Test method already exists.")
