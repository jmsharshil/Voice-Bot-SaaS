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
        import threading

        def preload():
            try:
                # 1. Preload embedding model
                from knowledge.services.indexer import _get_model
                print("[STARTUP] Preloading embedding model...")
                _get_model()
                print("[STARTUP] Embedding model ready [OK]")

                # 2. Pre-warm LLM connection — eliminates cold start on first call
                from conversations.services.azure_openai_service import generate_response
                print("[STARTUP] Pre-warming LLM...")
                generate_response("You are a helpful assistant.", "Hi")
                print("[STARTUP] LLM ready [OK]")

                # 3. Pre-warm greeting audio — cache TTS so EVERY call plays instantly
                print("[STARTUP] Pre-warming greeting audio...")
                try:
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
                                            stability=0.65,          # Stable pronunciation, no muttering/rushing
                                            similarity_boost=0.85,   # High voice profile consistency
                                            style=0.00,              # Lower style prevents synthesis artifacts
                                            use_speaker_boost=True
                                        )
                                    )
                                    pcm = b""
                                    for chunk in audio_generator:
                                        if chunk:
                                            pcm += chunk
                                    if pcm:
                                        if len(pcm) % 2 != 0:
                                            pcm = pcm[:-1]
                                        pcm = _amplify_pcm(pcm, gain=1.1)
                                        ulaw = encode_g711(pcm)
                                        _GREETING_AUDIO_CACHE[f"{agent.id}_{lang}"] = ulaw
                                        print(
                                            f"[STARTUP] [OK] Greeting synthesized and cached: '{agent.name}' ({lang}, {len(ulaw):,} bytes)"
                                        )
                                except Exception as se:
                                    print(f"[STARTUP] [WARN] ElevenLabs synthesis failed for {lang}: {se}")

                except Exception as ge:
                    print(f"[STARTUP] Greeting pre-warm error: {ge}")

                print("[STARTUP] Greeting audio ready [OK]")

            except Exception as e:
                print(f"[STARTUP] Preload failed: {e}")

        # Run in background thread so server starts instantly
        threading.Thread(target=preload, daemon=True).start()