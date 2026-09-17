# # from django.apps import AppConfig


# # class KnowledgeConfig(AppConfig):
# #     name = 'knowledge'



# from django.apps import AppConfig

# class KnowledgeConfig(AppConfig):
#     name = "knowledge"

#     def ready(self):
#         import threading

#         def preload():
#             try:
#                 # Preload embedding model
#                 from knowledge.services.indexer import _get_model
#                 print("[STARTUP] Preloading embedding model...")
#                 _get_model()
#                 print("[STARTUP] Embedding model ready ✅")

#                 # ⚡ Pre-warm LLM connection — eliminates cold start on first call
#                 from conversations.services.azure_openai_service import generate_response
#                 print("[STARTUP] Pre-warming LLM...")
#                 generate_response("You are a helpful assistant.", "Hi")
#                 print("[STARTUP] LLM ready ✅")

#             except Exception as e:
#                 print(f"[STARTUP] Preload failed: {e}")

#         # Run in background thread so server starts instantly
#         threading.Thread(target=preload, daemon=True).start()





































































from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    name = "knowledge"

    def ready(self):
        import sys
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, 'reconfigure'):
                try:
                    stream.reconfigure(errors='replace')
                except Exception:
                    pass

        import threading

        def preload():
            # 1. Preload embedding model
            try:
                from knowledge.services.indexer import _get_model
                print("[STARTUP] Preloading embedding model...")
                _get_model()
                print("[STARTUP] Embedding model ready [OK]")
            except Exception as e:
                print(f"[STARTUP] [WARN] Preloading embedding model failed: {e}")

            # 2. Pre-warm LLM connection — eliminates cold start on first call
            try:
                from conversations.services.azure_openai_service import generate_response
                print("[STARTUP] Pre-warming LLM...")
                generate_response("You are a helpful assistant.", "Hi")
                print("[STARTUP] LLM ready [OK]")
            except Exception as e:
                print(f"[STARTUP] [WARN] Pre-warming LLM failed: {e}")

            # 3. Pre-warm greeting audio — cache TTS so EVERY call plays instantly
            try:
                print("[STARTUP] Pre-warming greeting audio...")
                import os
                from conversations.consumers import (
                    _GREETING_AUDIO_CACHE, ELEVENLABS_CLIENT, ELEVENLABS_VOICE_MAP,
                    _amplify_pcm, encode_g711
                )
                from conversations.services.core.behavior_router import get_role_strategy
                from agents.models import VoiceAgent

                for agent in VoiceAgent.objects.select_related("role_template").filter(is_active=True):
                    role_name = agent.role_template.role_name if agent.role_template else ""
                    if get_role_strategy(role_name) != "automobile":
                        continue  # only pre-warm automobile agents

                    company = agent.company_name or "our company"
                    summary_txt = agent.summary.strip().rstrip(".") if agent.summary else ""
                    greeting = (
                        f"Hello! Main {agent.name} bol rahi hoon {company} se. {summary_txt}."
                        if summary_txt else
                        f"Hello, Main {agent.name} bol rahi hoon {company} se. "
                        f"kya aap abhi baat kar sakte hain?"
                    )

                    for lang in ["en", "hi", "gu"]:
                        local_greeting = os.path.join("mp3_responses", f"{lang}_step1_greeting.raw")
                        if os.path.exists(local_greeting):
                            print(f"[STARTUP] Loading ElevenLabs greeting file: {local_greeting}")
                            with open(local_greeting, "rb") as f:
                                ulaw = f.read()
                            _GREETING_AUDIO_CACHE[f"{agent.id}_{lang}"] = ulaw
                            print(
                                f"[STARTUP] [OK] Greeting cached from file: '{agent.name}' ({lang}, {len(ulaw):,} bytes)"
                            )
                        else:
                            # Synthesize via ElevenLabs API
                            print(f"[STARTUP] ElevenLabs greeting file not found. Synthesizing {lang}...")
                            voice_id = ELEVENLABS_VOICE_MAP.get(lang, ELEVENLABS_VOICE_MAP["en"])
                            try:
                                from elevenlabs import VoiceSettings
                                audio_generator = ELEVENLABS_CLIENT.text_to_speech.convert(
                                    voice_id=voice_id,
                                    text=greeting,
                                    model_id="eleven_multilingual_v2",
                                    output_format="pcm_8000",
                                    voice_settings=VoiceSettings(
                                        stability=0.55,          # Natural human-like tone variation
                                        similarity_boost=0.75,   # Balanced — reduces artifacts & over-enunciation
                                        style=0.00,
                                        use_speaker_boost=False, # Softer, warmer — removes loud "studio" effect
                                        speed=1.00               # Medium speed — natural pace on telephony
                                    )
                                )
                                pcm = b""
                                for chunk in audio_generator:
                                    if chunk:
                                        pcm += chunk
                                if pcm:
                                    if len(pcm) % 2 != 0:
                                        pcm = pcm[:-1]
                                    pcm = _amplify_pcm(pcm, gain=0.6)
                                    ulaw = encode_g711(pcm)
                                    _GREETING_AUDIO_CACHE[f"{agent.id}_{lang}"] = ulaw
                                    print(
                                        f"[STARTUP] [OK] Greeting synthesized and cached: '{agent.name}' ({lang}, {len(ulaw):,} bytes)"
                                    )
                            except Exception as se:
                                print(f"[STARTUP] [WARN] ElevenLabs synthesis failed for {lang}: {se}")
                print("[STARTUP] Greeting audio ready [OK]")
            except Exception as ge:
                print(f"[STARTUP] [WARN] Greeting pre-warm failed: {ge}")

            # 4. Preload Automobile Matchers — avoids huge delays during live calls
            try:
                print("[STARTUP] Preloading Automobile Matchers...")
                from conversations.consumers import get_matcher as get_matcher1
                from conversations.consumers_service2 import get_matcher as get_matcher2
                
                matchers_to_preload = [
                    ("AUTOMOBILE_MATCHER", "automobile_intents.json"),
                    ("NAAVYA_MATCHER", "automobile_bot/data/Naavya_intents.json"),
                    ("LOAN_MATCHER", "loan_bot/data/loan_intents.json"),
                    ("REMINDER_MATCHER", "reminder_bot/data/reminder_intents.json"),
                    ("TEMP_REAL_ESTATE_MATCHER", "temp_real_estate_bot/data/real_estate_intents.json"),
                    ("ENOGIC_MATCHER", "enogic_bot/data/enogic_intents.json"),
                    ("SAMSUNG_MATCHER", "samsung_bot/data/samsung_intents.json"),
                ]
                
                for name, intents_file in matchers_to_preload:
                    try:
                        get_matcher1(name, intents_file)
                        get_matcher2(name, intents_file)
                    except Exception as e:
                        print(f"[STARTUP] [WARN] Failed to preload matcher {name}: {e}")
                
                print("[STARTUP] Automobile Matchers preloaded [OK]")
            except Exception as me:
                print(f"[STARTUP] [WARN] Failed to preload matchers: {me}")

        # Run in background thread so server starts instantly
        threading.Thread(target=preload, daemon=True).start()