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
                print("[STARTUP] Embedding model ready ✅")

                # 2. Pre-warm LLM connection — eliminates cold start on first call
                from conversations.services.azure_openai_service import generate_response
                print("[STARTUP] Pre-warming LLM...")
                generate_response("You are a helpful assistant.", "Hi")
                print("[STARTUP] LLM ready ✅")

                # 3. Pre-warm greeting audio — cache TTS so EVERY call plays instantly
                print("[STARTUP] Pre-warming greeting audio...")
                try:
                    import os
                    import azure.cognitiveservices.speech as speechsdk
                    from conversations.consumers import (
                        _GREETING_AUDIO_CACHE, build_ssml, encode_g711,
                        strip_wav_header, TTS_VOICE_MAP,
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
                            f"Aapne KIYA vehicle ke liye enquiry ki thi, "
                            f"kya aap abhi baat kar sakte hain?"
                        )

                        ssml = build_ssml(greeting, "en")
                        speech_cfg = speechsdk.SpeechConfig(
                            subscription=os.getenv("AZURE_SPEECH_KEY"),
                            region=os.getenv("AZURE_SPEECH_REGION", "centralindia"),
                        )
                        speech_cfg.speech_synthesis_voice_name = TTS_VOICE_MAP.get(
                            "en", "en-IN-NeerjaNeural"
                        )
                        speech_cfg.set_speech_synthesis_output_format(
                            speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
                        )
                        synth = speechsdk.SpeechSynthesizer(
                            speech_config=speech_cfg, audio_config=None
                        )
                        result = synth.speak_ssml_async(ssml).get()
                        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                            pcm = strip_wav_header(result.audio_data)
                            if len(pcm) % 2 != 0:
                                pcm = pcm[:-1]
                            ulaw = encode_g711(pcm)
                            _GREETING_AUDIO_CACHE[str(agent.id)] = ulaw
                            print(
                                f"[STARTUP] ✅ Greeting cached: '{agent.name}' ({len(ulaw):,} bytes)"
                            )
                        else:
                            print(f"[STARTUP] ⚠️  Greeting TTS skipped for '{agent.name}'")

                except Exception as ge:
                    print(f"[STARTUP] Greeting pre-warm error: {ge}")

                print("[STARTUP] Greeting audio ready ✅")

            except Exception as e:
                print(f"[STARTUP] Preload failed: {e}")

        # Run in background thread so server starts instantly
        threading.Thread(target=preload, daemon=True).start()