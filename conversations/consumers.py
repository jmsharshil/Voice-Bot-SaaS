# # from urllib.parse import parse_qs
# # import audioop
# # from asgiref.sync import sync_to_async
# # import json
# # from channels.generic.websocket import AsyncWebsocketConsumer
# # from conversations.services.core.dialogue_engine import process_message, prepare_streaming, finalize_streaming
# # from conversations.services.azure_openai_service import generate_response_streaming
# # from conversations.services.speech_service import create_speech_recognizer
# # from conversations.services.translator_service import translate_text
# # import asyncio
# # import os
# # import azure.cognitiveservices.speech as speechsdk
# # import time
# # import base64
# # import uuid
# # import numpy as np
# # import re
# # from django.utils import timezone

# # from agents.models import VoiceAgent
# # from conversations.models import Conversation, Message
from automobile_matcher import AutomobileMatcher

# --- GLOBAL MATCHER (Loaded once at startup) ---
try:
    AUTOMOBILE_MATCHER = AutomobileMatcher("automobile_intents.json")
except Exception as e:
    print(f"⚠️ Failed to load AutomobileMatcher: {e}")
    AUTOMOBILE_MATCHER = None


# # # ================= DATABASE =================

# # @sync_to_async
# # def create_conversation(agent_id, session_id, user_number):
# #     return Conversation.objects.create(
# #         agent_id=agent_id,
# #         session_id=session_id,
# #         user_number=user_number
# #     )


# # @sync_to_async
# # def save_message(conversation, role, text):
# #     last = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
# #     if last and last.text.strip() == text.strip() and last.role == role:
# #         return
# #     Message.objects.create(conversation=conversation, role=role, text=text)


# # @sync_to_async
# # def update_user_number(conversation, number):
# #     conversation.user_number = number
# #     conversation.save()


# # @sync_to_async
# # def close_conversation(conversation):
# #     conversation.ended_at = timezone.now()
# #     conversation.save()


# # @sync_to_async
# # def get_agent_summary(agent_id):
# #     try:
# #         agent = VoiceAgent.objects.get(id=agent_id)
# #         company = agent.company_name or "our company"
# #         if agent.summary:
# #             summary = agent.summary.strip().rstrip(".")
# #             return f"Hello, I am {agent.name} from {company}. {summary}."
# #         return f"Hello, I am {agent.name} from {company}."
# #     except VoiceAgent.DoesNotExist:
# #         return "Hello, how can I assist you today?"


# # @sync_to_async
# # def mark_intro_shown(agent_id, session_id):
# #     from conversations.models import ConversationSession
# #     from agents.models import VoiceAgent
# #     try:
# #         agent = VoiceAgent.objects.get(id=agent_id)
# #         session, _ = ConversationSession.objects.get_or_create(
# #             agent=agent,
# #             session_id=session_id
# #         )
# #         state = session.state or {}
# #         state["intro_shown"] = True
# #         session.state = state
# #         session.save()
# #     except Exception as e:
# #         print("❌ mark_intro_shown error:", e)


# # # ================= AUDIO =================

# # def decode_g711(ulaw):
# #     return audioop.ulaw2lin(ulaw, 2)


# # def encode_g711(pcm):
# #     return audioop.lin2ulaw(pcm, 2)


# # # FIX: Proper RIFF/WAV header parser — reads actual data chunk offset
# # # Old code assumed fixed 44 bytes; Azure sometimes returns 58+ bytes
# # def strip_wav_header(data: bytes) -> bytes:
# #     if data[:4] != b'RIFF':
# #         return data
# #     offset = 12
# #     while offset < len(data) - 8:
# #         chunk_id = data[offset:offset + 4]
# #         chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
# #         if chunk_id == b'data':
# #             return data[offset + 8:]
# #         offset += 8 + chunk_size
# #     return data[44:]  # safe fallback


# # # G.711 u-law silence value is 0x7F — used for padding frames
# # SILENCE_FRAME = b'\x7f' * 160


# # def split_into_sentences(text: str) -> list:
# #     """Split reply into sentences for faster first-audio delivery."""
# #     sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
# #     return sentences if sentences else [text]


# # def is_end_intent(text: str) -> bool:
# #     text = text.lower().strip()
# #     end_keywords = [
# #         # English
# #         "bye", "goodbye", "ok bye", "okay bye",
# #         "thank you", "thanks a lot",
# #         "that's all", "no thanks", "call end",
# #         # Hindi
# #         "अलविदा",
# #         # Gujarati
# #         "બાય", "આભાર"
# #     ]
# #     return any(keyword in text for keyword in end_keywords)

# # # ================= CONSUMER =================

# # class VoiceBotConsumer(AsyncWebsocketConsumer):

# #     async def connect(self):
# #         self.loop = asyncio.get_running_loop()

# #         params = parse_qs(self.scope["query_string"].decode())
# #         self.agent_id = params.get("agent_id", [None])[0]
# #         self.user_number = params.get("from", ["unknown"])[0]
# #         self.language = params.get("language", ["en"])[0]

# #         if not self.agent_id:
# #             await self.close()
# #             return

# #         self.session_id = str(uuid.uuid4())
# #         self.conversation = await create_conversation(
# #             self.agent_id, self.session_id, self.user_number
# #         )

# #         # FIX: Capture streamSid from Twilio "start" event — required on every outgoing media frame
# #         self.stream_sid = None

# #         # ── STATE ──────────────────────────────────────────────
# #         self.is_bot_speaking = False
# #         self.is_connected = True
# #         self.is_processing = False

# #         self.partial_text = ""
# #         self.final_text_queue = asyncio.Queue()

# #         self.last_dispatched_text = ""
# #         self.last_dispatch_time = 0.0

# #         # ── LOCKS & TASKS ──────────────────────────────────────
# #         self.processing_lock = asyncio.Lock()
# #         self.tts_task = None

# #         # ── AUDIO / VAD ────────────────────────────────────────
# #         self.jitter_buffer = []
# #         self.jitter_delay = 2  # ⚡ was 3

# #         self.speech_active = False
# #         self.silence_start_time = None

# #         self.SPEECH_DETECT_RMS = 200
# #         self.SILENCE_TRIGGER_SEC = 1.2  # ⚡ Allow natural pauses — streaming LLM handles speed
# #         self.MIN_WORD_COUNT = 1

# #         # Interrupt detection — tuned for fast, responsive barge-in
# #         self.interrupt_start_time = None
# #         self.INTERRUPT_RMS = 300       # sensitivity threshold (was 400)
# #         self.INTERRUPT_HOLD_SEC = 0.3  # seconds of sustained speech to trigger (was 1.0)

# #         # ── STT SETUP ──────────────────────────────────────────
# #         self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
# #         self._setup_stt_callbacks()
# #         self.recognizer.start_continuous_recognition_async()

# #         # ── TTS SYNTHESIZER (reused — avoids per-call connection overhead) ──
# #         self._tts_synthesizer = self._build_tts_synthesizer()

# #         await self.accept()

# #         summary = await get_agent_summary(self.agent_id)
# #         if self.language != "en":
# #             summary = await sync_to_async(translate_text)(
# #                 summary, from_lang="en", to_lang=self.language
# #             )
# #         asyncio.create_task(self.send_tts(summary))
# #         await mark_intro_shown(self.agent_id, self.session_id)

# #         self.final_consumer_task = asyncio.create_task(self._final_text_consumer())

# #     def _setup_stt_callbacks(self):
# #         def handle_recognizing(evt):
# #             text = evt.result.text.strip() if evt.result.text else ""
# #             self.loop.call_soon_threadsafe(self._set_partial, text)

# #         def handle_recognized(evt):
# #             text = evt.result.text.strip() if evt.result.text else ""
# #             if text:
# #                 detected_lang = evt.result.properties.get(
# #                     speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
# #                 )
# #                 lang_code = detected_lang.split("-")[0] if detected_lang else "en"
# #                 if lang_code in ["en", "hi"]:
# #                     self.loop.call_soon_threadsafe(self._set_language, lang_code)

# #                 print(f"✅ Azure FINAL [{detected_lang}]: {text}")
# #                 self.loop.call_soon_threadsafe(
# #                     lambda: self.final_text_queue.put_nowait(text)
# #                 )

# #         def handle_canceled(evt):
# #             print("⚠️ STT Canceled:", evt.result.cancellation_details)

# #         self.recognizer.recognizing.connect(handle_recognizing)
# #         self.recognizer.recognized.connect(handle_recognized)
# #         self.recognizer.canceled.connect(handle_canceled)

# #     def _set_partial(self, text):
# #         self.partial_text = text

# #     def _set_language(self, lang_code):
# #         if self.language != lang_code:
# #             print(f"🌐 Language switched to: {lang_code}")
# #             self.language = lang_code
# #             # Rebuild synthesizer so next TTS call uses the correct voice
# #             self._tts_synthesizer = self._build_tts_synthesizer()

# #     async def _final_text_consumer(self):
# #         while self.is_connected:
# #             try:
# #                 text = await asyncio.wait_for(self.final_text_queue.get(), timeout=1.0)
# #             except asyncio.TimeoutError:
# #                 continue
# #             except Exception:
# #                 break

# #             if not text:
# #                 continue

# #             if self.is_bot_speaking or self.is_processing:
# #                 print("⏭️ Skipped (bot busy):", text)
# #                 continue

# #             normalized = text.lower().strip()
# #             if normalized == self.last_dispatched_text:
# #                 print("⏭️ Duplicate skipped:", text)
# #                 continue

# #             if time.time() - self.last_dispatch_time < 0.8:  # ⚡ was 1.5
# #                 print("⏭️ Cooldown skip:", text)
# #                 continue

# #             if len(text.split()) < self.MIN_WORD_COUNT:
# #                 print("⏭️ Too short:", text)
# #                 continue

# #             print("⚡ DISPATCHING TO AI:", text)
# #             self.last_dispatched_text = normalized
# #             self.last_dispatch_time = time.time()
# #             self.partial_text = ""

# #             self.is_processing = True
# #             try:
# #                 async with self.processing_lock:
# #                     await self.handle_ai_reply(text)
# #             finally:
# #                 self.is_processing = False

# #     # ================= RECEIVE =================

# #     async def receive(self, text_data=None, bytes_data=None):
# #         if not text_data:
# #             return

# #         try:
# #             data = json.loads(text_data)

# #             if data.get("event") == "start":
# #                 # FIX: Capture streamSid — must be attached to every outgoing media frame
# #                 self.stream_sid = data["start"].get("streamSid")
# #                 print(f"📡 streamSid captured: {self.stream_sid}")
# #                 try:
# #                     number = data["start"]["customParameters"]["callerNumber"]
# #                     self.user_number = number
# #                     await update_user_number(self.conversation, number)
# #                 except Exception:
# #                     pass

# #             if data.get("event") == "media":
# #                 await self._handle_audio_chunk(data)

# #         except Exception as e:
# #             print("❌ RECEIVE ERROR:", e)

# #     async def _handle_audio_chunk(self, data):
# #         payload = base64.b64decode(data["media"]["payload"])
# #         pcm = decode_g711(payload)

# #         # Dynamic gain — boosts quiet/soft/slow voices automatically
# #         pcm_np = np.frombuffer(pcm, dtype=np.int16).copy()
# #         current_rms = audioop.rms(pcm, 2)
# #         if current_rms > 50:
# #             gain = min(1200 / current_rms, 6.0)
# #             pcm_np = np.clip(pcm_np * gain, -32768, 32767).astype(np.int16)
# #         pcm = pcm_np.tobytes()

# #         if len(pcm) % 2 != 0:
# #             pcm = pcm[:-1]

# #         # Jitter buffer
# #         self.jitter_buffer.append(pcm)
# #         if len(self.jitter_buffer) < self.jitter_delay:
# #             return

# #         pcm = self.jitter_buffer.pop(0)
# #         rms = audioop.rms(pcm, 2)

# #         # Drop truly corrupt packets only
# #         pcm_check = np.frombuffer(pcm, dtype=np.int16)
# #         if int(np.abs(pcm_check).max()) == 32767 and rms > 28000:
# #             return

# #         # Always feed to Azure — no RMS gate
# #         # ── INTERRUPT DETECTION ────────────────────────────────
# #         if self.is_bot_speaking:
# #             return  # Do NOT feed audio to Azure STT while bot is speaking

# #         # Feed to Azure STT only when bot is silent
# #         self.push_stream.write(pcm)

# #         # ── AGGRESSIVE PARTIAL-TEXT DISPATCH ───────────────────
# #         # ⚡ This is now the PRIMARY dispatch path — fires BEFORE
# #         # Azure's recognized event, bypassing Azure's silence timeout.
# #         if rms > self.SPEECH_DETECT_RMS:
# #             self.speech_active = True
# #             self.silence_start_time = None
# #         else:
# #             if self.speech_active:
# #                 if self.silence_start_time is None:
# #                     self.silence_start_time = time.time()
# #                 elif time.time() - self.silence_start_time > self.SILENCE_TRIGGER_SEC:
# #                     self.speech_active = False
# #                     self.silence_start_time = None

# #                     if (
# #                         not self.is_bot_speaking
# #                         and not self.is_processing
# #                         and self.partial_text
# #                         # ⚡ REMOVED: self.final_text_queue.empty() guard
# #                         # We no longer wait for Azure's recognized event —
# #                         # local VAD + partial text IS the primary path
# #                     ):
# #                         fallback_text = self.partial_text.strip()
# #                         self.partial_text = ""

# #                         if len(fallback_text.split()) >= self.MIN_WORD_COUNT:
# #                             normalized = fallback_text.lower()
# #                             if normalized != self.last_dispatched_text:
# #                                 if time.time() - self.last_dispatch_time >= 0.8:
# #                                     print("⚡ FAST DISPATCH (partial VAD):", fallback_text)
# #                                     self.last_dispatched_text = normalized
# #                                     self.last_dispatch_time = time.time()
# #                                     self.is_processing = True
# #                                     try:
# #                                         async with self.processing_lock:
# #                                             await self.handle_ai_reply(fallback_text)
# #                                     finally:
# #                                         self.is_processing = False

# #     async def _check_interrupt(self, rms):
# #         """Detect user barge-in while bot is speaking.
# #         When sustained speech above INTERRUPT_RMS is detected for
# #         INTERRUPT_HOLD_SEC seconds, stop TTS immediately, flush
# #         Twilio's audio buffer, and schedule dispatch of the
# #         user's interrupted speech to the AI pipeline."""
# #         if rms < self.INTERRUPT_RMS:
# #             self.interrupt_start_time = None
# #             return

# #         if self.interrupt_start_time is None:
# #             self.interrupt_start_time = time.time()
# #             return

# #         if time.time() - self.interrupt_start_time < self.INTERRUPT_HOLD_SEC:
# #             return

# #         print("🛑 INTERRUPT DETECTED — stopping bot, capturing user speech")

# #         # Snapshot whatever Azure STT has recognised so far
# #         interrupted_partial = self.partial_text.strip()
# #         interrupt_time = time.time()

# #         # ── Stop bot immediately ──────────────────────────────
# #         self.is_bot_speaking = False
# #         self.interrupt_start_time = None

# #         # Cancel TTS playback task
# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         # Flush Twilio's server-side audio buffer so the caller
# #         # hears silence immediately instead of stale bot audio
# #         await self._send_clear_event()

# #         self.jitter_buffer.clear()

# #         # Schedule a fallback: if Azure doesn't produce a final
# #         # recognition in time, use the partial text we captured
# #         asyncio.create_task(
# #             self._interruption_fallback(interrupted_partial, interrupt_time)
# #         )

# #     # ================= INTERRUPT HELPERS =================

# #     async def _send_clear_event(self):
# #         """Send Twilio 'clear' event to flush queued audio on the caller's phone."""
# #         if self.stream_sid:
# #             try:
# #                 await self.send(text_data=json.dumps({
# #                     "event": "clear",
# #                     "streamSid": self.stream_sid
# #                 }))
# #                 print("📢 Twilio audio buffer cleared")
# #             except Exception as e:
# #                 print(f"❌ Clear event failed: {e}")

# #     async def _interruption_fallback(self, partial_text, interrupt_time):
# #         """Safety net for interrupt handling.

# #         After an interrupt the normal path is:
# #           Azure 'recognized' event → _final_text_consumer → handle_ai_reply

# #         But if the old pipeline is still finishing (is_processing=True),
# #         _final_text_consumer skips the text.  This fallback waits 1.5s
# #         and, if nothing was dispatched, uses the captured partial text.
# #         """
# #         await asyncio.sleep(1.5)

# #         # Normal path already handled it — nothing to do
# #         if self.last_dispatch_time > interrupt_time:
# #             print("✅ Interrupt speech already dispatched via normal path")
# #             return

# #         # Bot started a new response or new processing is underway
# #         if self.is_bot_speaking or self.is_processing:
# #             print("⏭️ Interrupt fallback skipped (pipeline busy)")
# #             return

# #         # Try to grab a final recognition that may have queued
# #         final_text = None
# #         try:
# #             final_text = self.final_text_queue.get_nowait()
# #         except asyncio.QueueEmpty:
# #             pass

# #         text = final_text or self.partial_text.strip() or partial_text
# #         self.partial_text = ""

# #         if not text or len(text.split()) < self.MIN_WORD_COUNT:
# #             print("⏭️ Interrupt text too short:", text)
# #             return

# #         normalized = text.lower().strip()
# #         if normalized == self.last_dispatched_text:
# #             print("⏭️ Interrupt duplicate skipped:", text)
# #             return

# #         print("⚡ INTERRUPT FALLBACK DISPATCH:", text)
# #         self.last_dispatched_text = normalized
# #         self.last_dispatch_time = time.time()

# #         self.is_processing = True
# #         try:
# #             async with self.processing_lock:
# #                 await self.handle_ai_reply(text)
# #         finally:
# #             self.is_processing = False

# #     # ================= STREAMING LLM BRIDGE =================

# #     async def _stream_llm(self, system_prompt, user_message):
# #         """
# #         ⚡ Async generator that bridges the synchronous streaming LLM
# #         into the async event loop via a queue. The LLM runs in a thread
# #         and pushes chunks; this generator yields them as they arrive.
# #         Chunks buffer automatically when the consumer is busy with TTS.
# #         """
# #         queue = asyncio.Queue()
# #         loop = asyncio.get_event_loop()

# #         def _run_streaming():
# #             try:
# #                 for chunk in generate_response_streaming(system_prompt, user_message):
# #                     loop.call_soon_threadsafe(queue.put_nowait, chunk)
# #             except Exception as e:
# #                 print(f"❌ LLM Streaming error: {e}")
# #             loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

# #         loop.run_in_executor(None, _run_streaming)

# #         while True:
# #             chunk = await queue.get()
# #             if chunk is None:
# #                 break
# #             yield chunk

# #     # ================= AI (STREAMING) =================

# #     async def handle_ai_reply(self, text):
# #         """
# #         ⚡ STREAMING PIPELINE — replaces the old blocking process_message call.

# #         Flow:
# #         1. prepare_streaming() — builds system prompt, handles static replies
# #         2. _stream_llm() — streams LLM tokens asynchronously
# #         3. As each sentence completes → immediately synthesize + play TTS
# #         4. finalize_streaming() — saves response to session state

# #         Result: first audio plays ~500-700ms after LLM starts generating,
# #         instead of waiting 1.5-2s for the full response.
# #         """
# #         pipeline_start = time.time()
# #         text = text.strip()
# #         if not text:
# #             return

# #         normalized = text.lower().strip()

# #         # ── END INTENT (unchanged) ────────────────────────────
# #         if is_end_intent(normalized):
# #             print("📴 END INTENT DETECTED:", text)

# #             await save_message(self.conversation, "user", text)

# #             farewell_en = "Thank you for calling. Have a great day!"
# #             farewell = farewell_en
# #             if self.language != "en":
# #                 farewell = await sync_to_async(translate_text)(
# #                     farewell_en, from_lang="en", to_lang=self.language
# #                 )

# #             await save_message(self.conversation, "bot", farewell)

# #             if self.tts_task and not self.tts_task.done():
# #                 self.tts_task.cancel()
# #                 try:
# #                     await self.tts_task
# #                 except asyncio.CancelledError:
# #                     pass

# #             await self.send_tts(farewell)
# #             await close_conversation(self.conversation)

# #             await self.send(text_data=json.dumps({"event": "stop"}))

# #             self.is_connected = False
# #             await self.close()
# #             return

# #         # ── MAIN STREAMING PIPELINE ───────────────────────────
# #         print("🧠 AI INPUT:", text)
# #         await save_message(self.conversation, "user", text)

# #         # Step 1: Translate input if needed
# #         t_translate_in = time.time()
# #         message_for_ai = text
# #         if self.language != "en":
# #             message_for_ai = await sync_to_async(translate_text)(
# #                 text, from_lang=self.language, to_lang="en"
# #             )
# #             print(f"🌐 [{self.language}→en]: {message_for_ai}")
# #         translate_in_ms = round((time.time() - t_translate_in) * 1000)

# #         # Step 2: Prepare (builds system prompt OR returns static reply)
# #         t_prep = time.time()
# #         prep_result = await sync_to_async(prepare_streaming)(
# #             self.agent_id, message_for_ai, self.session_id
# #         )
# #         prep_ms = round((time.time() - t_prep) * 1000)

# #         # Step 3a: Static reply — no LLM streaming needed
# #         if "static_reply" in prep_result:
# #             reply = prep_result["static_reply"]
# #             if not reply:
# #                 return

# #             reply_for_user = reply
# #             if self.language != "en":
# #                 reply_for_user = await sync_to_async(translate_text)(
# #                     reply, from_lang="en", to_lang=self.language
# #                 )

# #             total_ms = round((time.time() - pipeline_start) * 1000)
# #             print(f"⏱ PIPELINE (static): prep={prep_ms}ms | TOTAL={total_ms}ms")

# #             await save_message(self.conversation, "bot", reply_for_user)
# #             print("🤖 BOT REPLY:", reply_for_user)

# #             if self.tts_task and not self.tts_task.done():
# #                 self.tts_task.cancel()
# #                 try:
# #                     await self.tts_task
# #                 except asyncio.CancelledError:
# #                     pass

# #             self.tts_task = asyncio.create_task(self.send_tts(reply_for_user))
# #             return

# #         # Step 3b: ⚡ STREAMING LLM + PER-SENTENCE TTS
# #         system_prompt = prep_result["system_prompt"]
# #         user_message = prep_result["user_message"]

# #         # Cancel any existing TTS
# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         self.is_bot_speaking = True
# #         t_llm = time.time()

# #         # Audio queue bridges LLM sentence producer → TTS audio consumer
# #         audio_queue = asyncio.Queue()
# #         full_response = ""
# #         first_sentence_time = None

# #         async def streaming_producer():
# #             """
# #             Reads LLM chunks, accumulates into sentences, synthesizes TTS
# #             for each sentence, and pushes audio into the queue.
# #             The LLM keeps generating in its background thread even while
# #             we're doing TTS synthesis — chunks buffer in _stream_llm's queue.
# #             """
# #             nonlocal full_response, first_sentence_time
# #             sentence_buffer = ""
# #             loop = asyncio.get_event_loop()

# #             async for chunk in self._stream_llm(system_prompt, user_message):
# #                 if not self.is_bot_speaking:
# #                     break
# #                 full_response += chunk
# #                 sentence_buffer += chunk

# #                 # Check for sentence boundary (period/exclamation/question followed by space)
# #                 boundary = re.search(r'[.!?।]\s', sentence_buffer)
# #                 if boundary:
# #                     sentence = sentence_buffer[:boundary.start() + 1].strip()
# #                     sentence_buffer = sentence_buffer[boundary.end():]
# #                     if sentence:
# #                         if first_sentence_time is None:
# #                             first_sentence_time = time.time()
# #                             print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

# #                         # Translate sentence if needed
# #                         tts_text = sentence
# #                         if self.language != "en":
# #                             tts_text = await sync_to_async(translate_text)(
# #                                 sentence, from_lang="en", to_lang=self.language
# #                             )

# #                         try:
# #                             ulaw = await asyncio.wait_for(
# #                                 loop.run_in_executor(
# #                                     None,
# #                                     lambda s=tts_text: self._synthesize_ulaw(s)
# #                                 ),
# #                                 timeout=15
# #                             )
# #                             await audio_queue.put(ulaw)
# #                         except asyncio.TimeoutError:
# #                             print(f"❌ TTS timeout: {sentence[:40]}")

# #             # Handle remaining text that didn't end with punctuation
# #             if sentence_buffer.strip() and self.is_bot_speaking:
# #                 sentence = sentence_buffer.strip()
# #                 if first_sentence_time is None:
# #                     first_sentence_time = time.time()
# #                     print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

# #                 tts_text = sentence
# #                 if self.language != "en":
# #                     tts_text = await sync_to_async(translate_text)(
# #                         sentence, from_lang="en", to_lang=self.language
# #                     )
# #                 try:
# #                     ulaw = await asyncio.wait_for(
# #                         loop.run_in_executor(
# #                             None,
# #                             lambda s=tts_text: self._synthesize_ulaw(s)
# #                         ),
# #                         timeout=15
# #                     )
# #                     await audio_queue.put(ulaw)
# #                 except asyncio.TimeoutError:
# #                     pass

# #             # Signal consumer that all audio is ready
# #             await audio_queue.put(None)

# #         async def streaming_consumer():
# #             """Streams audio to Twilio as soon as each sentence's TTS is ready."""
# #             while True:
# #                 ulaw = await audio_queue.get()
# #                 if ulaw is None:
# #                     break
# #                 if not self.is_bot_speaking:
# #                     break
# #                 await self._stream_ulaw(ulaw)

# #         # Run producer + consumer concurrently
# #         producer_task = asyncio.create_task(streaming_producer())
# #         consumer_task = asyncio.create_task(streaming_consumer())
# #         # Set tts_task so interrupt detection can cancel audio playback
# #         self.tts_task = consumer_task

# #         try:
# #             await asyncio.gather(producer_task, consumer_task)
# #         except asyncio.CancelledError:
# #             print("🛑 STREAMING TTS CANCELLED")
# #         except Exception as e:
# #             print("❌ STREAMING ERROR:", e)
# #         finally:
# #             self.is_bot_speaking = False

# #         llm_ms = round((time.time() - t_llm) * 1000)
# #         total_ms = round((time.time() - pipeline_start) * 1000)
# #         print(f"⏱ STREAMING PIPELINE: translate_in={translate_in_ms}ms | prep={prep_ms}ms | LLM+TTS={llm_ms}ms | TOTAL={total_ms}ms")

# #         # Save full response to DB
# #         reply_for_user = full_response
# #         if self.language != "en" and full_response:
# #             reply_for_user = await sync_to_async(translate_text)(
# #                 full_response, from_lang="en", to_lang=self.language
# #             )
# #         if reply_for_user:
# #             await save_message(self.conversation, "bot", reply_for_user)
# #         print("🤖 BOT REPLY:", reply_for_user)

# #         # Finalize session state
# #         if full_response:
# #             await sync_to_async(finalize_streaming)(full_response, prep_result)

# #     # ================= TTS HELPERS =================

# #     def _build_tts_synthesizer(self):
# #         """
# #         Build and return a reusable SpeechSynthesizer for the current language.
# #         Creating a new synthesizer per-call costs 300-800ms of connection setup —
# #         reusing one eliminates that overhead entirely.
# #         """
# #         TTS_VOICE_MAP = {
# #             "en": "en-IN-AnanyaNeural",
# #             "hi": "hi-IN-AnanyaNeural"
# #         }
# #         speech_config = speechsdk.SpeechConfig(
# #             subscription=os.getenv("AZURE_SPEECH_KEY"),
# #             region=os.getenv("AZURE_SPEECH_REGION")
# #         )
# #         speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(
# #             self.language, "en-IN-AnanyaNeural"
# #         )
# #         speech_config.set_speech_synthesis_output_format(
# #             speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
# #         )
# #         return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

# #     def _synthesize_ulaw(self, text: str) -> bytes:
# #         """
# #         Synthesize a single sentence to raw u-law bytes using the reused synthesizer.
# #         Runs in a thread executor — safe to call from run_in_executor.
# #         """
# #         result = self._tts_synthesizer.speak_text_async(text).get()

# #         if result.reason == speechsdk.ResultReason.Canceled:
# #             details = result.cancellation_details
# #             print("❌ TTS Canceled:", details.reason, details.error_details)
# #             return b""

# #         pcm = result.audio_data
# #         pcm = strip_wav_header(pcm)

# #         if len(pcm) % 2 != 0:
# #             pcm = pcm[:-1]

# #         return encode_g711(pcm)

# #     async def _stream_ulaw(self, ulaw: bytes):
# #         """
# #         FIX 1: Attaches self.stream_sid to every outgoing media frame.
# #                 Twilio silently drops frames that are missing streamSid.
# #         FIX 2: Clock-anchored timing loop — self-corrects for event loop jitter.
# #                 Old asyncio.sleep(0.02) drifted by 5–15ms per frame under load.
# #         FIX 3: Silence padding (3 frames before + after) prevents clipping at
# #                 the start and end of each audio segment.
# #         """
# #         if not ulaw:
# #             return

# #         loop = asyncio.get_event_loop()

# #         # 3 silence frames before audio (~60ms) to prevent leading clip
# #         for _ in range(3):
# #             if not self.is_bot_speaking:
# #                 return
# #             await self._send_media_frame(SILENCE_FRAME)
# #             await asyncio.sleep(0.020)

# #         # Main audio — clock-anchored so timing never drifts
# #         start_time = loop.time()
# #         for idx, i in enumerate(range(0, len(ulaw), 160)):
# #             if not self.is_bot_speaking:
# #                 print("🛑 TTS stopped mid-stream")
# #                 return

# #             # Pad the last chunk to a full frame if needed
# #             chunk = ulaw[i:i + 160].ljust(160, b'\x7f')
# #             await self._send_media_frame(chunk)

# #             # Sleep only the REMAINING time — compensates for send() latency
# #             target_time = start_time + (idx + 1) * 0.020
# #             sleep_duration = target_time - loop.time()
# #             if sleep_duration > 0:
# #                 await asyncio.sleep(sleep_duration)

# #         # 3 silence frames after audio (~60ms) to prevent trailing click/pop
# #         for _ in range(3):
# #             if not self.is_bot_speaking:
# #                 return
# #             await self._send_media_frame(SILENCE_FRAME)
# #             await asyncio.sleep(0.020)

# #     async def _send_media_frame(self, chunk: bytes):
# #         """
# #         FIX: Centralised send helper that always includes streamSid.
# #         Twilio's media stream requires streamSid on outgoing frames
# #         otherwise packets are silently dropped causing audio gaps.
# #         """
# #         payload = base64.b64encode(chunk).decode()
# #         msg = {
# #             "event": "media",
# #             "media": {"payload": payload}
# #         }
# #         # Only attach streamSid once it has been captured from the "start" event
# #         if self.stream_sid:
# #             msg["streamSid"] = self.stream_sid
# #         await self.send(text_data=json.dumps(msg))

# #     # ================= TTS (kept for static replies / intro) =================

# #     async def send_tts(self, text):
# #         self.is_bot_speaking = True
# #         loop = asyncio.get_event_loop()

# #         try:
# #             sentences = split_into_sentences(text)

# #             # Queue holds pre-synthesized ulaw audio ready to stream
# #             audio_queue = asyncio.Queue()

# #             async def producer():
# #                 """Synthesizes all sentences and puts audio into the queue."""
# #                 for sentence in sentences:
# #                     if not self.is_bot_speaking:
# #                         break
# #                     try:
# #                         ulaw = await asyncio.wait_for(
# #                             loop.run_in_executor(
# #                                 None,
# #                                 lambda s=sentence: self._synthesize_ulaw(s)
# #                             ),
# #                             timeout=15
# #                         )
# #                     except asyncio.TimeoutError:
# #                         print(f"❌ TTS TIMEOUT for sentence: {sentence[:40]}")
# #                         ulaw = b""
# #                     await audio_queue.put(ulaw)
# #                 # Sentinel signals the consumer that production is done
# #                 await audio_queue.put(None)

# #             async def consumer():
# #                 """Streams audio chunks as soon as they are ready."""
# #                 while True:
# #                     ulaw = await audio_queue.get()
# #                     if ulaw is None:
# #                         break  # All sentences done
# #                     if not self.is_bot_speaking:
# #                         break
# #                     await self._stream_ulaw(ulaw)

# #             # Run both concurrently — producer fills queue while consumer drains it
# #             producer_task = asyncio.create_task(producer())
# #             consumer_task = asyncio.create_task(consumer())

# #             await asyncio.gather(producer_task, consumer_task)

# #         except asyncio.CancelledError:
# #             print("🛑 TTS CANCELLED")
# #             raise

# #         except Exception as e:
# #             print("❌ TTS ERROR:", e)

# #         finally:
# #             self.is_bot_speaking = False

# #     # ================= DISCONNECT =================

# #     async def disconnect(self, close_code):
# #         print("🔌 DISCONNECTED:", close_code)
# #         self.is_connected = False

# #         if hasattr(self, "final_consumer_task"):
# #             self.final_consumer_task.cancel()
# #             try:
# #                 await self.final_consumer_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if hasattr(self, "recognizer"):
# #             try:
# #                 self.recognizer.stop_continuous_recognition_async()
# #             except Exception:
# #                 pass

# #         if hasattr(self, "push_stream"):
# #             try:
# #                 self.push_stream.close()
# #             except Exception:
# #                 pass

# #         if hasattr(self, "conversation"):
# #             await close_conversation(self.conversation)




































































# #sir na chnage valo live nathi karelo but working code....(a work kare chhe complete hinglsih all bot no gujrati and if you want to open these code you should to change dialougeengine code)



# # from urllib.parse import parse_qs
# # import audioop
# # from asgiref.sync import sync_to_async
# # import json
# # from channels.generic.websocket import AsyncWebsocketConsumer
# # from conversations.services.core.dialogue_engine import process_message, prepare_streaming, finalize_streaming
# # from conversations.services.azure_openai_service import generate_response_streaming
# # from conversations.services.speech_service import create_speech_recognizer
# # from conversations.services.translator_service import translate_text
# # import asyncio
# # import os
# # import azure.cognitiveservices.speech as speechsdk
# # import time
# # import base64
# # import uuid
# # import numpy as np
# # import re
# # from django.utils import timezone

# # from agents.models import VoiceAgent
# # from conversations.models import Conversation, Message


# # # ================= DATABASE =================

# # @sync_to_async
# # def create_conversation(agent_id, session_id, user_number):
# #     return Conversation.objects.create(
# #         agent_id=agent_id,
# #         session_id=session_id,
# #         user_number=user_number
# #     )


# # @sync_to_async
# # def save_message(conversation, role, text):
# #     last = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
# #     if last and last.text.strip() == text.strip() and last.role == role:
# #         return
# #     Message.objects.create(conversation=conversation, role=role, text=text)


# # @sync_to_async
# # def update_user_number(conversation, number):
# #     conversation.user_number = number
# #     conversation.save()


# # @sync_to_async
# # def close_conversation(conversation):
# #     conversation.ended_at = timezone.now()
# #     conversation.save()


# # @sync_to_async
# # def get_agent_summary(agent_id):
# #     try:
# #         agent = VoiceAgent.objects.get(id=agent_id)
# #         company = agent.company_name or "our company"
# #         if agent.summary:
# #             summary = agent.summary.strip().rstrip(".")
# #             return f"Hello, I am {agent.name} from {company}. {summary}."
# #         return f"Hello, I am {agent.name} from {company}."
# #     except VoiceAgent.DoesNotExist:
# #         return "Hello, how can I assist you today?"


# # @sync_to_async
# # def mark_intro_shown(agent_id, session_id):
# #     from conversations.models import ConversationSession
# #     from agents.models import VoiceAgent
# #     try:
# #         agent = VoiceAgent.objects.get(id=agent_id)
# #         session, _ = ConversationSession.objects.get_or_create(
# #             agent=agent,
# #             session_id=session_id
# #         )
# #         state = session.state or {}
# #         state["intro_shown"] = True
# #         session.state = state
# #         session.save()
# #     except Exception as e:
# #         print("❌ mark_intro_shown error:", e)


# # # ================= AUDIO =================

# # def decode_g711(ulaw):
# #     return audioop.ulaw2lin(ulaw, 2)


# # def encode_g711(pcm):
# #     return audioop.lin2ulaw(pcm, 2)


# # # FIX: Proper RIFF/WAV header parser — reads actual data chunk offset
# # # Old code assumed fixed 44 bytes; Azure sometimes returns 58+ bytes
# # def strip_wav_header(data: bytes) -> bytes:
# #     if data[:4] != b'RIFF':
# #         return data
# #     offset = 12
# #     while offset < len(data) - 8:
# #         chunk_id = data[offset:offset + 4]
# #         chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
# #         if chunk_id == b'data':
# #             return data[offset + 8:]
# #         offset += 8 + chunk_size
# #     return data[44:]  # safe fallback


# # # G.711 u-law silence value is 0x7F — used for padding frames
# # SILENCE_FRAME = b'\x7f' * 160


# # def split_into_sentences(text: str) -> list:
# #     """Split reply into sentences for faster first-audio delivery."""
# #     sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
# #     return sentences if sentences else [text]


# # def is_end_intent(text: str) -> bool:
# #     text = text.lower().strip()
# #     end_keywords = [
# #         # English
# #         "bye", "goodbye", "ok bye", "okay bye",
# #         "thank you", "thanks a lot",
# #         "that's all", "no thanks", "call end",
# #         # Hindi
# #         "अलविदा",
# #         # Gujarati
# #         "બાય", "આભાર"
# #     ]
# #     return any(keyword in text for keyword in end_keywords)


# # # ================= SSML BUILDER =================

# # # CHANGE 1: Voice map upgraded to recommended Neural voices (Section 2 of guide)
# # # EN: NeerjaExpressiveNeural (was AnanyaNeural) — best for customer support
# # # HI: MadhurNeural (was AnanyaNeural) — flagship Hindi Neural voice
# # # GU: DhwaniNeural (new) — only Gujarati Neural voice on Azure
# # TTS_VOICE_MAP = {
# #     "en": "en-IN-AnanyaNeural",
# #     "hi": "hi-IN-AnanyaNeural",
# #     # "gu": "gu-IN-DhwaniNeural",
# # }

# # # CHANGE 2: SSML style map — expressive style per language
# # # NeerjaExpressiveNeural supports mstts:express-as with customerservice style
# # SSML_STYLE_MAP = {
# #     "en": None,
# #     "hi": None,   # MadhurNeural does not support express-as styles
# #     # "gu": None,   # DhwaniNeural does not support express-as styles
# # }

# # # CHANGE 2: SSML prosody defaults — rate/pitch tuning per voice
# # SSML_PROSODY_MAP = {
# #     "en": {"rate": "-3%", "pitch": "+1Hz"},
# #     "hi": {"rate": "-3%", "pitch": "0Hz"},
# #     # "gu": {"rate": "-3%", "pitch": "0Hz"},
# # }


# # def build_ssml(text: str, language: str) -> str:
# #     """
# #     CHANGE 2: Build SSML markup for the given text and language.
# #     Uses NeerjaExpressiveNeural's customerservice style for EN.
# #     Falls back to prosody-only SSML for HI/GU (no express-as support).
# #     """
# #     voice = TTS_VOICE_MAP.get(language, TTS_VOICE_MAP["en"])
# #     style = SSML_STYLE_MAP.get(language)
# #     prosody = SSML_PROSODY_MAP.get(language, SSML_PROSODY_MAP["en"])
# #     lang_tag = {"en": "en-IN", "hi": "hi-IN"}.get(language, "en-IN")

# #     prosody_open = f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}">'
# #     prosody_close = '</prosody>'

# #     if style:
# #         inner = (
# #             f'<mstts:express-as style="{style}">'
# #             f'{prosody_open}{text}{prosody_close}'
# #             f'</mstts:express-as>'
# #         )
# #     else:
# #         inner = f'{prosody_open}{text}{prosody_close}'

# #     return (
# #         f'<speak version="1.0" '
# #         f'xmlns="http://www.w3.org/2001/10/synthesis" '
# #         f'xmlns:mstts="http://www.w3.org/2001/mstts" '
# #         f'xml:lang="{lang_tag}">'
# #         f'<voice name="{voice}">'
# #         f'{inner}'
# #         f'</voice>'
# #         f'</speak>'
# #     )


# # # ================= CONSUMER =================

# # class VoiceBotConsumer(AsyncWebsocketConsumer):

# #     async def connect(self):
# #         self.loop = asyncio.get_running_loop()

# #         params = parse_qs(self.scope["query_string"].decode())
# #         self.agent_id = params.get("agent_id", [None])[0]
# #         self.user_number = params.get("from", ["unknown"])[0]
# #         self.language = params.get("language", ["en"])[0]

# #         if not self.agent_id:
# #             await self.close()
# #             return

# #         self.session_id = str(uuid.uuid4())
# #         self.conversation = await create_conversation(
# #             self.agent_id, self.session_id, self.user_number
# #         )

# #         # FIX: Capture streamSid from Twilio "start" event — required on every outgoing media frame
# #         self.stream_sid = None

# #         # ── STATE ──────────────────────────────────────────────
# #         self.is_bot_speaking = False
# #         self.is_connected = True
# #         self.is_processing = False

# #         self.partial_text = ""
# #         self.final_text_queue = asyncio.Queue()

# #         self.last_dispatched_text = ""
# #         self.last_dispatch_time = 0.0

# #         # ── LOCKS & TASKS ──────────────────────────────────────
# #         self.processing_lock = asyncio.Lock()
# #         self.tts_task = None

# #         # ── AUDIO / VAD ────────────────────────────────────────
# #         self.jitter_buffer = []
# #         self.jitter_delay = 2

# #         self.speech_active = False
# #         self.silence_start_time = None

# #         self.SPEECH_DETECT_RMS = 200
# #         self.SILENCE_TRIGGER_SEC = 1.2
# #         self.MIN_WORD_COUNT = 1

# #         # Interrupt detection
# #         self.interrupt_start_time = None
# #         self.INTERRUPT_RMS = 300
# #         self.INTERRUPT_HOLD_SEC = 0.3

# #         # ── STT SETUP ──────────────────────────────────────────
# #         self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
# #         self._setup_stt_callbacks()
# #         self.recognizer.start_continuous_recognition_async()

# #         # ── TTS SYNTHESIZER (reused — avoids per-call connection overhead) ──
# #         self._tts_synthesizer = self._build_tts_synthesizer()

# #         await self.accept()

# #         summary = await get_agent_summary(self.agent_id)
# #         if self.language != "en":
# #             summary = await sync_to_async(translate_text)(
# #                 summary, from_lang="en", to_lang=self.language
# #             )
# #         asyncio.create_task(self.send_tts(summary))
# #         await mark_intro_shown(self.agent_id, self.session_id)

# #         self.final_consumer_task = asyncio.create_task(self._final_text_consumer())

# #         # CHANGE 3: Start keepalive loop — prevents silent WebSocket drop on long calls
# #         self.keepalive_task = asyncio.create_task(self._keepalive_loop())

# #     # ================= CHANGE 3: KEEPALIVE =================

# #     async def _keepalive_loop(self):
# #         """
# #         CHANGE 3: Send a ping every 25s to keep the WebSocket alive.
# #         SIP and WebSocket connections silently drop during pauses without this.
# #         """
# #         while self.is_connected:
# #             await asyncio.sleep(25)
# #             if not self.is_connected:
# #                 break
# #             try:
# #                 await self.send(text_data=json.dumps({"event": "ping"}))
# #                 print("🏓 Keepalive ping sent")
# #             except Exception as e:
# #                 print(f"❌ Keepalive failed: {e}")
# #                 break

# #     def _setup_stt_callbacks(self):
# #         def handle_recognizing(evt):
# #             text = evt.result.text.strip() if evt.result.text else ""
# #             self.loop.call_soon_threadsafe(self._set_partial, text)

# #         def handle_recognized(evt):
# #             text = evt.result.text.strip() if evt.result.text else ""
# #             if text:
# #                 detected_lang = evt.result.properties.get(
# #                     speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
# #                 )
# #                 lang_code = detected_lang.split("-")[0] if detected_lang else "en"
# #                 # CHANGE 1: Added "gu" to language detection alongside en/hi
# #                 if lang_code in ["en", "hi", "gu"]:
# #                     self.loop.call_soon_threadsafe(self._set_language, lang_code)

# #                 print(f"✅ Azure FINAL [{detected_lang}]: {text}")
# #                 self.loop.call_soon_threadsafe(
# #                     lambda: self.final_text_queue.put_nowait(text)
# #                 )

# #         def handle_canceled(evt):
# #             print("⚠️ STT Canceled:", evt.result.cancellation_details)

# #         self.recognizer.recognizing.connect(handle_recognizing)
# #         self.recognizer.recognized.connect(handle_recognized)
# #         self.recognizer.canceled.connect(handle_canceled)

# #     def _set_partial(self, text):
# #         self.partial_text = text

# #     def _set_language(self, lang_code):
# #         if self.language != lang_code:
# #             print(f"🌐 Language switched to: {lang_code}")
# #             self.language = lang_code
# #             # Rebuild synthesizer so next TTS call uses the correct voice
# #             self._tts_synthesizer = self._build_tts_synthesizer()

# #     async def _final_text_consumer(self):
# #         while self.is_connected:
# #             try:
# #                 text = await asyncio.wait_for(self.final_text_queue.get(), timeout=1.0)
# #             except asyncio.TimeoutError:
# #                 continue
# #             except Exception:
# #                 break

# #             if not text:
# #                 continue

# #             if self.is_bot_speaking or self.is_processing:
# #                 print("⏭️ Skipped (bot busy):", text)
# #                 continue

# #             normalized = text.lower().strip()
# #             if normalized == self.last_dispatched_text:
# #                 print("⏭️ Duplicate skipped:", text)
# #                 continue

# #             if time.time() - self.last_dispatch_time < 0.8:
# #                 print("⏭️ Cooldown skip:", text)
# #                 continue

# #             if len(text.split()) < self.MIN_WORD_COUNT:
# #                 print("⏭️ Too short:", text)
# #                 continue

# #             print("⚡ DISPATCHING TO AI:", text)
# #             self.last_dispatched_text = normalized
# #             self.last_dispatch_time = time.time()
# #             self.partial_text = ""

# #             self.is_processing = True
# #             try:
# #                 async with self.processing_lock:
# #                     await self.handle_ai_reply(text)
# #             finally:
# #                 self.is_processing = False

# #     # ================= RECEIVE =================

# #     async def receive(self, text_data=None, bytes_data=None):
# #         if not text_data:
# #             return

# #         try:
# #             data = json.loads(text_data)

# #             if data.get("event") == "start":
# #                 self.stream_sid = data["start"].get("streamSid")
# #                 print(f"📡 streamSid captured: {self.stream_sid}")
# #                 try:
# #                     number = data["start"]["customParameters"]["callerNumber"]
# #                     self.user_number = number
# #                     await update_user_number(self.conversation, number)
# #                 except Exception:
# #                     pass

# #             if data.get("event") == "media":
# #                 await self._handle_audio_chunk(data)

# #         except Exception as e:
# #             print("❌ RECEIVE ERROR:", e)

# #     async def _handle_audio_chunk(self, data):
# #         payload = base64.b64decode(data["media"]["payload"])
# #         pcm = decode_g711(payload)

# #         # Dynamic gain — boosts quiet/soft/slow voices automatically
# #         pcm_np = np.frombuffer(pcm, dtype=np.int16).copy()
# #         current_rms = audioop.rms(pcm, 2)
# #         if current_rms > 50:
# #             gain = min(1200 / current_rms, 6.0)
# #             pcm_np = np.clip(pcm_np * gain, -32768, 32767).astype(np.int16)
# #         pcm = pcm_np.tobytes()

# #         if len(pcm) % 2 != 0:
# #             pcm = pcm[:-1]

# #         # Jitter buffer
# #         self.jitter_buffer.append(pcm)
# #         if len(self.jitter_buffer) < self.jitter_delay:
# #             return

# #         pcm = self.jitter_buffer.pop(0)
# #         rms = audioop.rms(pcm, 2)

# #         # Drop truly corrupt packets only
# #         pcm_check = np.frombuffer(pcm, dtype=np.int16)
# #         if int(np.abs(pcm_check).max()) == 32767 and rms > 28000:
# #             return

# #         # ── INTERRUPT DETECTION ────────────────────────────────
# #         if self.is_bot_speaking:
# #             return  # Do NOT feed audio to Azure STT while bot is speaking

# #         # Feed to Azure STT only when bot is silent
# #         self.push_stream.write(pcm)

# #         # ── AGGRESSIVE PARTIAL-TEXT DISPATCH ───────────────────
# #         if rms > self.SPEECH_DETECT_RMS:
# #             self.speech_active = True
# #             self.silence_start_time = None
# #         else:
# #             if self.speech_active:
# #                 if self.silence_start_time is None:
# #                     self.silence_start_time = time.time()
# #                 elif time.time() - self.silence_start_time > self.SILENCE_TRIGGER_SEC:
# #                     self.speech_active = False
# #                     self.silence_start_time = None

# #                     if (
# #                         not self.is_bot_speaking
# #                         and not self.is_processing
# #                         and self.partial_text
# #                     ):
# #                         fallback_text = self.partial_text.strip()
# #                         self.partial_text = ""

# #                         if len(fallback_text.split()) >= self.MIN_WORD_COUNT:
# #                             normalized = fallback_text.lower()
# #                             if normalized != self.last_dispatched_text:
# #                                 if time.time() - self.last_dispatch_time >= 0.8:
# #                                     print("⚡ FAST DISPATCH (partial VAD):", fallback_text)
# #                                     self.last_dispatched_text = normalized
# #                                     self.last_dispatch_time = time.time()
# #                                     self.is_processing = True
# #                                     try:
# #                                         async with self.processing_lock:
# #                                             await self.handle_ai_reply(fallback_text)
# #                                     finally:
# #                                         self.is_processing = False

# #     async def _check_interrupt(self, rms):
# #         """Detect user barge-in while bot is speaking."""
# #         if rms < self.INTERRUPT_RMS:
# #             self.interrupt_start_time = None
# #             return

# #         if self.interrupt_start_time is None:
# #             self.interrupt_start_time = time.time()
# #             return

# #         if time.time() - self.interrupt_start_time < self.INTERRUPT_HOLD_SEC:
# #             return

# #         print("🛑 INTERRUPT DETECTED — stopping bot, capturing user speech")

# #         interrupted_partial = self.partial_text.strip()
# #         interrupt_time = time.time()

# #         self.is_bot_speaking = False
# #         self.interrupt_start_time = None

# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         await self._send_clear_event()

# #         self.jitter_buffer.clear()

# #         asyncio.create_task(
# #             self._interruption_fallback(interrupted_partial, interrupt_time)
# #         )

# #     # ================= INTERRUPT HELPERS =================

# #     async def _send_clear_event(self):
# #         """Send Twilio 'clear' event to flush queued audio on the caller's phone."""
# #         if self.stream_sid:
# #             try:
# #                 await self.send(text_data=json.dumps({
# #                     "event": "clear",
# #                     "streamSid": self.stream_sid
# #                 }))
# #                 print("📢 Twilio audio buffer cleared")
# #             except Exception as e:
# #                 print(f"❌ Clear event failed: {e}")

# #     async def _interruption_fallback(self, partial_text, interrupt_time):
# #         """Safety net for interrupt handling."""
# #         await asyncio.sleep(1.5)

# #         if self.last_dispatch_time > interrupt_time:
# #             print("✅ Interrupt speech already dispatched via normal path")
# #             return

# #         if self.is_bot_speaking or self.is_processing:
# #             print("⏭️ Interrupt fallback skipped (pipeline busy)")
# #             return

# #         final_text = None
# #         try:
# #             final_text = self.final_text_queue.get_nowait()
# #         except asyncio.QueueEmpty:
# #             pass

# #         text = final_text or self.partial_text.strip() or partial_text
# #         self.partial_text = ""

# #         if not text or len(text.split()) < self.MIN_WORD_COUNT:
# #             print("⏭️ Interrupt text too short:", text)
# #             return

# #         normalized = text.lower().strip()
# #         if normalized == self.last_dispatched_text:
# #             print("⏭️ Interrupt duplicate skipped:", text)
# #             return

# #         print("⚡ INTERRUPT FALLBACK DISPATCH:", text)
# #         self.last_dispatched_text = normalized
# #         self.last_dispatch_time = time.time()

# #         self.is_processing = True
# #         try:
# #             async with self.processing_lock:
# #                 await self.handle_ai_reply(text)
# #         finally:
# #             self.is_processing = False

# #     # ================= STREAMING LLM BRIDGE =================

# #     async def _stream_llm(self, system_prompt, user_message):
# #         """
# #         Async generator that bridges the synchronous streaming LLM
# #         into the async event loop via a queue.
# #         """
# #         queue = asyncio.Queue()
# #         loop = asyncio.get_event_loop()

# #         def _run_streaming():
# #             try:
# #                 for chunk in generate_response_streaming(system_prompt, user_message):
# #                     loop.call_soon_threadsafe(queue.put_nowait, chunk)
# #             except Exception as e:
# #                 print(f"❌ LLM Streaming error: {e}")
# #             loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

# #         loop.run_in_executor(None, _run_streaming)

# #         while True:
# #             chunk = await queue.get()
# #             if chunk is None:
# #                 break
# #             yield chunk

# #     # ================= AI (STREAMING) =================

# #     async def handle_ai_reply(self, text):
# #         """
# #         STREAMING PIPELINE — streams LLM tokens, synthesizes per sentence, plays audio.
# #         """
# #         pipeline_start = time.time()
# #         text = text.strip()
# #         if not text:
# #             return

# #         normalized = text.lower().strip()

# #         # ── END INTENT ────────────────────────────────────────
# #         if is_end_intent(normalized):
# #             print("📴 END INTENT DETECTED:", text)

# #             await save_message(self.conversation, "user", text)

# #             farewell_en = "Thank you for calling. Have a great day!"
# #             farewell = farewell_en
# #             if self.language != "en":
# #                 farewell = await sync_to_async(translate_text)(
# #                     farewell_en, from_lang="en", to_lang=self.language
# #                 )

# #             await save_message(self.conversation, "bot", farewell)

# #             if self.tts_task and not self.tts_task.done():
# #                 self.tts_task.cancel()
# #                 try:
# #                     await self.tts_task
# #                 except asyncio.CancelledError:
# #                     pass

# #             await self.send_tts(farewell)
# #             await close_conversation(self.conversation)

# #             await self.send(text_data=json.dumps({"event": "stop"}))

# #             self.is_connected = False
# #             await self.close()
# #             return

# #         # ── MAIN STREAMING PIPELINE ───────────────────────────
# #         print("🧠 AI INPUT:", text)
# #         await save_message(self.conversation, "user", text)

# #         # Step 1: Translate input if needed
# #         t_translate_in = time.time()
# #         message_for_ai = text
# #         if self.language != "en":
# #             message_for_ai = await sync_to_async(translate_text)(
# #                 text, from_lang=self.language, to_lang="en"
# #             )
# #             print(f"🌐 [{self.language}→en]: {message_for_ai}")
# #         translate_in_ms = round((time.time() - t_translate_in) * 1000)

# #         # Step 2: Prepare (builds system prompt OR returns static reply)
# #         t_prep = time.time()
# #         prep_result = await sync_to_async(prepare_streaming)(
# #             self.agent_id, message_for_ai, self.session_id
# #         )
# #         prep_ms = round((time.time() - t_prep) * 1000)

# #         # Step 3a: Static reply — no LLM streaming needed
# #         if "static_reply" in prep_result:
# #             reply = prep_result["static_reply"]
# #             if not reply:
# #                 return

# #             reply_for_user = reply
# #             if self.language != "en":
# #                 reply_for_user = await sync_to_async(translate_text)(
# #                     reply, from_lang="en", to_lang=self.language
# #                 )

# #             total_ms = round((time.time() - pipeline_start) * 1000)
# #             print(f"⏱ PIPELINE (static): prep={prep_ms}ms | TOTAL={total_ms}ms")

# #             await save_message(self.conversation, "bot", reply_for_user)
# #             print("🤖 BOT REPLY:", reply_for_user)

# #             if self.tts_task and not self.tts_task.done():
# #                 self.tts_task.cancel()
# #                 try:
# #                     await self.tts_task
# #                 except asyncio.CancelledError:
# #                     pass

# #             self.tts_task = asyncio.create_task(self.send_tts(reply_for_user))
# #             return

# #         # Step 3b: STREAMING LLM + PER-SENTENCE TTS
# #         system_prompt = prep_result["system_prompt"]
# #         user_message = prep_result["user_message"]

# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         self.is_bot_speaking = True
# #         t_llm = time.time()

# #         audio_queue = asyncio.Queue()
# #         full_response = ""
# #         first_sentence_time = None

# #         async def streaming_producer():
# #             nonlocal full_response, first_sentence_time
# #             sentence_buffer = ""
# #             loop = asyncio.get_event_loop()

# #             async for chunk in self._stream_llm(system_prompt, user_message):
# #                 if not self.is_bot_speaking:
# #                     break
# #                 full_response += chunk
# #                 sentence_buffer += chunk

# #                 boundary = re.search(r'[.!?।]\s', sentence_buffer)
# #                 if boundary:
# #                     sentence = sentence_buffer[:boundary.start() + 1].strip()
# #                     sentence_buffer = sentence_buffer[boundary.end():]
# #                     if sentence:
# #                         if first_sentence_time is None:
# #                             first_sentence_time = time.time()
# #                             print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

# #                         tts_text = sentence
# #                         if self.language != "en":
# #                             tts_text = await sync_to_async(translate_text)(
# #                                 sentence, from_lang="en", to_lang=self.language
# #                             )

# #                         try:
# #                             ulaw = await asyncio.wait_for(
# #                                 loop.run_in_executor(
# #                                     None,
# #                                     lambda s=tts_text: self._synthesize_ulaw(s)
# #                                 ),
# #                                 timeout=15
# #                             )
# #                             await audio_queue.put(ulaw)
# #                         except asyncio.TimeoutError:
# #                             print(f"❌ TTS timeout: {sentence[:40]}")

# #             # Handle remaining text
# #             if sentence_buffer.strip() and self.is_bot_speaking:
# #                 sentence = sentence_buffer.strip()
# #                 if first_sentence_time is None:
# #                     first_sentence_time = time.time()
# #                     print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

# #                 tts_text = sentence
# #                 if self.language != "en":
# #                     tts_text = await sync_to_async(translate_text)(
# #                         sentence, from_lang="en", to_lang=self.language
# #                     )
# #                 try:
# #                     ulaw = await asyncio.wait_for(
# #                         loop.run_in_executor(
# #                             None,
# #                             lambda s=tts_text: self._synthesize_ulaw(s)
# #                         ),
# #                         timeout=15
# #                     )
# #                     await audio_queue.put(ulaw)
# #                 except asyncio.TimeoutError:
# #                     pass

# #             await audio_queue.put(None)

# #         async def streaming_consumer():
# #             """Streams audio to Twilio as soon as each sentence's TTS is ready."""
# #             while True:
# #                 ulaw = await audio_queue.get()
# #                 if ulaw is None:
# #                     break
# #                 if not self.is_bot_speaking:
# #                     break
# #                 await self._stream_ulaw(ulaw)

# #         producer_task = asyncio.create_task(streaming_producer())
# #         consumer_task = asyncio.create_task(streaming_consumer())
# #         self.tts_task = consumer_task

# #         try:
# #             await asyncio.gather(producer_task, consumer_task)
# #         except asyncio.CancelledError:
# #             print("🛑 STREAMING TTS CANCELLED")
# #         except Exception as e:
# #             print("❌ STREAMING ERROR:", e)
# #         finally:
# #             self.is_bot_speaking = False

# #         llm_ms = round((time.time() - t_llm) * 1000)
# #         total_ms = round((time.time() - pipeline_start) * 1000)
# #         print(f"⏱ STREAMING PIPELINE: translate_in={translate_in_ms}ms | prep={prep_ms}ms | LLM+TTS={llm_ms}ms | TOTAL={total_ms}ms")

# #         reply_for_user = full_response
# #         if self.language != "en" and full_response:
# #             reply_for_user = await sync_to_async(translate_text)(
# #                 full_response, from_lang="en", to_lang=self.language
# #             )
# #         if reply_for_user:
# #             await save_message(self.conversation, "bot", reply_for_user)
# #         print("🤖 BOT REPLY:", reply_for_user)

# #         if full_response:
# #             await sync_to_async(finalize_streaming)(full_response, prep_result)

# #     # ================= TTS HELPERS =================

# #     def _build_tts_synthesizer(self):
# #         """
# #         Build and return a reusable SpeechSynthesizer for the current language.
# #         CHANGE 1: Now uses upgraded Neural voice map (NeerjaExpressiveNeural, MadhurNeural, DhwaniNeural).
# #         CHANGE 2: Output format stays Raw8Khz16BitMonoPcm for Twilio mulaw compatibility.
# #         """
# #         speech_config = speechsdk.SpeechConfig(
# #             subscription=os.getenv("AZURE_SPEECH_KEY"),
# #             region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
# #             # CHANGE 3 (region): Default to centralindia — lowest latency for India calls.
# #             # If AZURE_SPEECH_REGION env var is set correctly, this fallback is never used.
# #         )
# #         # CHANGE 1: Voice pulled from upgraded TTS_VOICE_MAP
# #         speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(
# #             self.language, TTS_VOICE_MAP["en"]
# #         )
# #         speech_config.set_speech_synthesis_output_format(
# #             speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
# #         )
# #         return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

# #     def _synthesize_ulaw(self, text: str) -> bytes:
# #         """
# #         CHANGE 2: Synthesize using SSML (speak_ssml_async) instead of plain text.
# #         This enables NeerjaExpressiveNeural's customerservice style + prosody tuning.
# #         Falls back gracefully on cancellation.
# #         """
# #         ssml = build_ssml(text, self.language)
# #         result = self._tts_synthesizer.speak_ssml_async(ssml).get()

# #         if result.reason == speechsdk.ResultReason.Canceled:
# #             details = result.cancellation_details
# #             print("❌ TTS Canceled:", details.reason, details.error_details)
# #             return b""

# #         pcm = result.audio_data
# #         pcm = strip_wav_header(pcm)

# #         if len(pcm) % 2 != 0:
# #             pcm = pcm[:-1]

# #         return encode_g711(pcm)

# #     async def _stream_ulaw(self, ulaw: bytes):
# #         """
# #         Stream u-law audio frames to Twilio with clock-anchored timing.
# #         Silence padding prevents clipping at start/end of each segment.
# #         """
# #         if not ulaw:
# #             return

# #         loop = asyncio.get_event_loop()

# #         # 3 silence frames before audio (~60ms) to prevent leading clip
# #         for _ in range(3):
# #             if not self.is_bot_speaking:
# #                 return
# #             await self._send_media_frame(SILENCE_FRAME)
# #             await asyncio.sleep(0.020)

# #         # Main audio — clock-anchored so timing never drifts
# #         start_time = loop.time()
# #         for idx, i in enumerate(range(0, len(ulaw), 160)):
# #             if not self.is_bot_speaking:
# #                 print("🛑 TTS stopped mid-stream")
# #                 return

# #             chunk = ulaw[i:i + 160].ljust(160, b'\x7f')
# #             await self._send_media_frame(chunk)

# #             target_time = start_time + (idx + 1) * 0.020
# #             sleep_duration = target_time - loop.time()
# #             if sleep_duration > 0:
# #                 await asyncio.sleep(sleep_duration)

# #         # 3 silence frames after audio (~60ms) to prevent trailing click/pop
# #         for _ in range(3):
# #             if not self.is_bot_speaking:
# #                 return
# #             await self._send_media_frame(SILENCE_FRAME)
# #             await asyncio.sleep(0.020)

# #     async def _send_media_frame(self, chunk: bytes):
# #         """Centralised send helper that always includes streamSid."""
# #         payload = base64.b64encode(chunk).decode()
# #         msg = {
# #             "event": "media",
# #             "media": {"payload": payload}
# #         }
# #         if self.stream_sid:
# #             msg["streamSid"] = self.stream_sid
# #         await self.send(text_data=json.dumps(msg))

# #     # ================= TTS (kept for static replies / intro) =================

# #     async def send_tts(self, text):
# #         self.is_bot_speaking = True
# #         loop = asyncio.get_event_loop()

# #         try:
# #             sentences = split_into_sentences(text)
# #             audio_queue = asyncio.Queue()

# #             async def producer():
# #                 for sentence in sentences:
# #                     if not self.is_bot_speaking:
# #                         break
# #                     try:
# #                         ulaw = await asyncio.wait_for(
# #                             loop.run_in_executor(
# #                                 None,
# #                                 lambda s=sentence: self._synthesize_ulaw(s)
# #                             ),
# #                             timeout=15
# #                         )
# #                     except asyncio.TimeoutError:
# #                         print(f"❌ TTS TIMEOUT for sentence: {sentence[:40]}")
# #                         ulaw = b""
# #                     await audio_queue.put(ulaw)
# #                 await audio_queue.put(None)

# #             async def consumer():
# #                 while True:
# #                     ulaw = await audio_queue.get()
# #                     if ulaw is None:
# #                         break
# #                     if not self.is_bot_speaking:
# #                         break
# #                     await self._stream_ulaw(ulaw)

# #             producer_task = asyncio.create_task(producer())
# #             consumer_task = asyncio.create_task(consumer())

# #             await asyncio.gather(producer_task, consumer_task)

# #         except asyncio.CancelledError:
# #             print("🛑 TTS CANCELLED")
# #             raise

# #         except Exception as e:
# #             print("❌ TTS ERROR:", e)

# #         finally:
# #             self.is_bot_speaking = False

# #     # ================= DISCONNECT =================

# #     async def disconnect(self, close_code):
# #         print("🔌 DISCONNECTED:", close_code)
# #         self.is_connected = False

# #         # CHANGE 3: Cancel keepalive task on disconnect
# #         if hasattr(self, "keepalive_task"):
# #             self.keepalive_task.cancel()
# #             try:
# #                 await self.keepalive_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if hasattr(self, "final_consumer_task"):
# #             self.final_consumer_task.cancel()
# #             try:
# #                 await self.final_consumer_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if hasattr(self, "recognizer"):
# #             try:
# #                 self.recognizer.stop_continuous_recognition_async()
# #             except Exception:
# #                 pass

# #         if hasattr(self, "push_stream"):
# #             try:
# #                 self.push_stream.close()
# #             except Exception:
# #                 pass

# #         if hasattr(self, "conversation"):
# #             await close_conversation(self.conversation)





































# #a code chhe je gujrati ma suppoer kare chhe and a code ma gujarati e srvam ma kam kare chhe interview bot and baki na bot hinglish ma vat kare chhe....








# # from urllib.parse import parse_qs
# # import audioop
# # from asgiref.sync import sync_to_async
# # import json
# # from channels.generic.websocket import AsyncWebsocketConsumer
# # from conversations.services.core.dialogue_engine import process_message, prepare_streaming, finalize_streaming, get_agent_tts_language
# # from conversations.services.azure_openai_service import generate_response_streaming
# # from conversations.services.speech_service import create_speech_recognizer
# # from conversations.services.translator_service import translate_text
# # import asyncio
# # import os
# # import azure.cognitiveservices.speech as speechsdk
# # import time
# # import base64
# # import uuid
# # import numpy as np
# # import re
# # from django.utils import timezone

# # from agents.models import VoiceAgent
# # from conversations.models import Conversation, Message


# # # ================= DATABASE =================

# # @sync_to_async
# # def create_conversation(agent_id, session_id, user_number):
# #     return Conversation.objects.create(
# #         agent_id=agent_id,
# #         session_id=session_id,
# #         user_number=user_number
# #     )


# # @sync_to_async
# # def save_message(conversation, role, text):
# #     last = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
# #     if last and last.text.strip() == text.strip() and last.role == role:
# #         return
# #     Message.objects.create(conversation=conversation, role=role, text=text)


# # @sync_to_async
# # def update_user_number(conversation, number):
# #     conversation.user_number = number
# #     conversation.save()


# # @sync_to_async
# # def close_conversation(conversation):
# #     conversation.ended_at = timezone.now()
# #     conversation.save()


# # @sync_to_async
# # def get_agent_summary(agent_id):
# #     try:
# #         agent = VoiceAgent.objects.get(id=agent_id)
# #         company = agent.company_name or "our company"
# #         if agent.summary:
# #             summary = agent.summary.strip().rstrip(".")
# #             return f"Hello, I am {agent.name} from {company}. {summary}."
# #         return f"Hello, I am {agent.name} from {company}."
# #     except VoiceAgent.DoesNotExist:
# #         return "Hello, how can I assist you today?"


# # @sync_to_async
# # def mark_intro_shown(agent_id, session_id):
# #     from conversations.models import ConversationSession
# #     from agents.models import VoiceAgent
# #     try:
# #         agent = VoiceAgent.objects.get(id=agent_id)
# #         session, _ = ConversationSession.objects.get_or_create(
# #             agent=agent,
# #             session_id=session_id
# #         )
# #         state = session.state or {}
# #         state["intro_shown"] = True
# #         session.state = state
# #         session.save()
# #     except Exception as e:
# #         print("❌ mark_intro_shown error:", e)


# # # ================= AUDIO =================

# # def decode_g711(ulaw):
# #     return audioop.ulaw2lin(ulaw, 2)


# # def encode_g711(pcm):
# #     return audioop.lin2ulaw(pcm, 2)


# # def strip_wav_header(data: bytes) -> bytes:
# #     if data[:4] != b'RIFF':
# #         return data
# #     offset = 12
# #     while offset < len(data) - 8:
# #         chunk_id = data[offset:offset + 4]
# #         chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
# #         if chunk_id == b'data':
# #             return data[offset + 8:]
# #         offset += 8 + chunk_size
# #     return data[44:]  # safe fallback


# # # G.711 u-law silence value is 0x7F
# # SILENCE_FRAME = b'\x7f' * 160


# # def split_into_sentences(text: str) -> list:
# #     sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', text) if s.strip()]
# #     return sentences if sentences else [text]


# # def is_end_intent(text: str) -> bool:
# #     text = text.lower().strip()
# #     end_keywords = [
# #         "bye", "goodbye", "ok bye", "okay bye",
# #         "thank you", "thanks a lot",
# #         "that's all", "no thanks", "call end",
# #         "અلविदा",
# #         "બાय", "આભાર"
# #     ]
# #     return any(keyword in text for keyword in end_keywords)


# # # ================= SSML BUILDER =================

# # TTS_VOICE_MAP = {
# #     "en": "en-IN-AnanyaNeural",
# #     "hi": "hi-IN-AnanyaNeural",
# #     "gu": "gu-IN-DhwaniNeural",
# # }

# # SSML_STYLE_MAP = {
# #     "en": None,
# #     "hi": None,
# #     "gu": None,
# # }

# # SSML_PROSODY_MAP = {
# #     "en": {"rate": "-3%", "pitch": "+1Hz"},
# #     "hi": {"rate": "-3%", "pitch": "0Hz"},
# #     "gu": {"rate": "+15%", "pitch": "0Hz"},  # slightly slower for Gujarati clarity
# # }


# # def build_ssml(text: str, language: str) -> str:
# #     voice = TTS_VOICE_MAP.get(language, TTS_VOICE_MAP["en"])
# #     style = SSML_STYLE_MAP.get(language)
# #     prosody = SSML_PROSODY_MAP.get(language, SSML_PROSODY_MAP["en"])
# #     lang_tag = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}.get(language, "en-IN")

# #     prosody_open = f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}">'
# #     prosody_close = '</prosody>'

# #     if style:
# #         inner = (
# #             f'<mstts:express-as style="{style}">'
# #             f'{prosody_open}{text}{prosody_close}'
# #             f'</mstts:express-as>'
# #         )
# #     else:
# #         inner = f'{prosody_open}{text}{prosody_close}'

# #     return (
# #         f'<speak version="1.0" '
# #         f'xmlns="http://www.w3.org/2001/10/synthesis" '
# #         f'xmlns:mstts="http://www.w3.org/2001/mstts" '
# #         f'xml:lang="{lang_tag}">'
# #         f'<voice name="{voice}">'
# #         f'{inner}'
# #         f'</voice>'
# #         f'</speak>'
# #     )


# # # ================= CONSUMER =================

# # class VoiceBotConsumer(AsyncWebsocketConsumer):

# #     async def connect(self):
# #         self.loop = asyncio.get_running_loop()

# #         params = parse_qs(self.scope["query_string"].decode())
# #         self.agent_id = params.get("agent_id", [None])[0]
# #         self.user_number = params.get("from", ["unknown"])[0]
# #         self.language = params.get("language", ["en"])[0]

# #         if not self.agent_id:
# #             await self.close()
# #             return

# #         self.session_id = str(uuid.uuid4())
# #         self.conversation = await create_conversation(
# #             self.agent_id, self.session_id, self.user_number
# #         )

# #         self.stream_sid = None

# #         # ── STATE ──────────────────────────────────────────────
# #         self.is_bot_speaking = False
# #         self.is_connected = True
# #         self.is_processing = False
# #         ###
# #         self.use_sarvam = False
# #         self.partial_text = ""
# #         self.final_text_queue = asyncio.Queue()

# #         self.last_dispatched_text = ""
# #         self.last_dispatch_time = 0.0

# #         # ── LOCKS & TASKS ──────────────────────────────────────
# #         self.processing_lock = asyncio.Lock()
# #         self.tts_task = None

# #         # ── AUDIO / VAD ────────────────────────────────────────
# #         self.jitter_buffer = []
# #         self.jitter_delay = 2

# #         self.speech_active = False
# #         self.silence_start_time = None

# #         self.SPEECH_DETECT_RMS = 200
# #         self.SILENCE_TRIGGER_SEC = 1.2
# #         self.MIN_WORD_COUNT = 1

# #         # Interrupt detection
# #         self.interrupt_start_time = None
# #         self.INTERRUPT_RMS = 300
# #         self.INTERRUPT_HOLD_SEC = 0.3

# #         # ── STT SETUP ──────────────────────────────────────────
# #         self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
# #         self._setup_stt_callbacks()
# #         self.recognizer.start_continuous_recognition_async()

# #         # ── TTS SYNTHESIZER (reused — avoids per-call connection overhead) ──
# #         self._tts_synthesizer = self._build_tts_synthesizer()

# #         await self.accept()

# #         summary = await get_agent_summary(self.agent_id)

# #         # Get agent's required TTS language
# #         agent_tts_lang = await sync_to_async(get_agent_tts_language)(self.agent_id)

# #         if agent_tts_lang == "gu":
# #             self.use_sarvam = True 
# #             # Interview bot only — translate intro to Gujarati, play with Sarvam voice
# #             summary = await sync_to_async(translate_text)(
# #                 summary, from_lang="en", to_lang="gu"
# #             )
# #             print(f"🌐 Interview bot intro in Gujarati: {summary}")
# #             asyncio.create_task(self.send_tts(summary, tts_language="gu"))
# #         else:
# #             # All other bots — existing behaviour unchanged
# #             if self.language != "en":
# #                 summary = await sync_to_async(translate_text)(
# #                     summary, from_lang="en", to_lang=self.language
# #                 )
# #             asyncio.create_task(self.send_tts(summary))

# #         await mark_intro_shown(self.agent_id, self.session_id)

# #         self.final_consumer_task = asyncio.create_task(self._final_text_consumer())

# #         self.keepalive_task = asyncio.create_task(self._keepalive_loop())

# #     # ================= KEEPALIVE =================

# #     async def _keepalive_loop(self):
# #         while self.is_connected:
# #             await asyncio.sleep(25)
# #             if not self.is_connected:
# #                 break
# #             try:
# #                 await self.send(text_data=json.dumps({"event": "ping"}))
# #                 print("🏓 Keepalive ping sent")
# #             except Exception as e:
# #                 print(f"❌ Keepalive failed: {e}")
# #                 break

# #     def _setup_stt_callbacks(self):
# #         def handle_recognizing(evt):
# #             text = evt.result.text.strip() if evt.result.text else ""
# #             self.loop.call_soon_threadsafe(self._set_partial, text)

# #         def handle_recognized(evt):
# #             text = evt.result.text.strip() if evt.result.text else ""
# #             if text:
# #                 detected_lang = evt.result.properties.get(
# #                     speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
# #                 )
# #                 lang_code = detected_lang.split("-")[0] if detected_lang else "en"
# #                 if lang_code in ["en", "hi", "gu"]:
# #                     self.loop.call_soon_threadsafe(self._set_language, lang_code)

# #                 print(f"✅ Azure FINAL [{detected_lang}]: {text}")
# #                 self.loop.call_soon_threadsafe(
# #                     lambda: self.final_text_queue.put_nowait(text)
# #                 )

# #         def handle_canceled(evt):
# #             print("⚠️ STT Canceled:", evt.result.cancellation_details)

# #         self.recognizer.recognizing.connect(handle_recognizing)
# #         self.recognizer.recognized.connect(handle_recognized)
# #         self.recognizer.canceled.connect(handle_canceled)

# #     def _set_partial(self, text):
# #         self.partial_text = text

# #     def _set_language(self, lang_code):
# #         if self.language != lang_code:
# #             print(f"🌐 Language switched to: {lang_code}")
# #             self.language = lang_code
# #             # Rebuild synthesizer so next TTS call uses the correct voice
# #             self._tts_synthesizer = self._build_tts_synthesizer()

# #     async def _final_text_consumer(self):
# #         while self.is_connected:
# #             try:
# #                 text = await asyncio.wait_for(self.final_text_queue.get(), timeout=1.0)
# #             except asyncio.TimeoutError:
# #                 continue
# #             except Exception:
# #                 break

# #             if not text:
# #                 continue

# #             if self.is_bot_speaking or self.is_processing:
# #                 print("⏭️ Skipped (bot busy):", text)
# #                 continue

# #             normalized = text.lower().strip()
# #             if normalized == self.last_dispatched_text:
# #                 print("⏭️ Duplicate skipped:", text)
# #                 continue

# #             if time.time() - self.last_dispatch_time < 0.8:
# #                 print("⏭️ Cooldown skip:", text)
# #                 continue

# #             if len(text.split()) < self.MIN_WORD_COUNT:
# #                 print("⏭️ Too short:", text)
# #                 continue

# #             print("⚡ DISPATCHING TO AI:", text)
# #             self.last_dispatched_text = normalized
# #             self.last_dispatch_time = time.time()
# #             self.partial_text = ""

# #             self.is_processing = True
# #             try:
# #                 async with self.processing_lock:
# #                     await self.handle_ai_reply(text)
# #             finally:
# #                 self.is_processing = False

# #     # ================= RECEIVE =================

# #     async def receive(self, text_data=None, bytes_data=None):
# #         if not text_data:
# #             return

# #         try:
# #             data = json.loads(text_data)

# #             if data.get("event") == "start":
# #                 self.stream_sid = data["start"].get("streamSid")
# #                 print(f"📡 streamSid captured: {self.stream_sid}")
# #                 try:
# #                     number = data["start"]["customParameters"]["callerNumber"]
# #                     self.user_number = number
# #                     await update_user_number(self.conversation, number)
# #                 except Exception:
# #                     pass

# #             if data.get("event") == "media":
# #                 await self._handle_audio_chunk(data)

# #         except Exception as e:
# #             print("❌ RECEIVE ERROR:", e)

# #     async def _handle_audio_chunk(self, data):
# #         payload = base64.b64decode(data["media"]["payload"])
# #         pcm = decode_g711(payload)

# #         # Dynamic gain — boosts quiet/soft/slow voices automatically
# #         pcm_np = np.frombuffer(pcm, dtype=np.int16).copy()
# #         current_rms = audioop.rms(pcm, 2)
# #         if current_rms > 50:
# #             gain = min(1200 / current_rms, 6.0)
# #             pcm_np = np.clip(pcm_np * gain, -32768, 32767).astype(np.int16)
# #         pcm = pcm_np.tobytes()

# #         if len(pcm) % 2 != 0:
# #             pcm = pcm[:-1]

# #         # Jitter buffer
# #         self.jitter_buffer.append(pcm)
# #         if len(self.jitter_buffer) < self.jitter_delay:
# #             return

# #         pcm = self.jitter_buffer.pop(0)
# #         rms = audioop.rms(pcm, 2)

# #         # Drop truly corrupt packets only
# #         pcm_check = np.frombuffer(pcm, dtype=np.int16)
# #         if int(np.abs(pcm_check).max()) == 32767 and rms > 28000:
# #             return

# #         # ── INTERRUPT DETECTION ────────────────────────────────
# #         if self.is_bot_speaking:
# #             return  # Do NOT feed audio to Azure STT while bot is speaking

# #         # Feed to Azure STT only when bot is silent
# #         self.push_stream.write(pcm)

# #         # ── AGGRESSIVE PARTIAL-TEXT DISPATCH ───────────────────
# #         if rms > self.SPEECH_DETECT_RMS:
# #             self.speech_active = True
# #             self.silence_start_time = None
# #         else:
# #             if self.speech_active:
# #                 if self.silence_start_time is None:
# #                     self.silence_start_time = time.time()
# #                 elif time.time() - self.silence_start_time > self.SILENCE_TRIGGER_SEC:
# #                     self.speech_active = False
# #                     self.silence_start_time = None

# #                     if (
# #                         not self.is_bot_speaking
# #                         and not self.is_processing
# #                         and self.partial_text
# #                     ):
# #                         fallback_text = self.partial_text.strip()
# #                         self.partial_text = ""

# #                         if len(fallback_text.split()) >= self.MIN_WORD_COUNT:
# #                             normalized = fallback_text.lower()
# #                             if normalized != self.last_dispatched_text:
# #                                 if time.time() - self.last_dispatch_time >= 0.8:
# #                                     print("⚡ FAST DISPATCH (partial VAD):", fallback_text)
# #                                     self.last_dispatched_text = normalized
# #                                     self.last_dispatch_time = time.time()
# #                                     self.is_processing = True
# #                                     try:
# #                                         async with self.processing_lock:
# #                                             await self.handle_ai_reply(fallback_text)
# #                                     finally:
# #                                         self.is_processing = False

# #     async def _check_interrupt(self, rms):
# #         """Detect user barge-in while bot is speaking."""
# #         if rms < self.INTERRUPT_RMS:
# #             self.interrupt_start_time = None
# #             return

# #         if self.interrupt_start_time is None:
# #             self.interrupt_start_time = time.time()
# #             return

# #         if time.time() - self.interrupt_start_time < self.INTERRUPT_HOLD_SEC:
# #             return

# #         print("🛑 INTERRUPT DETECTED — stopping bot, capturing user speech")

# #         interrupted_partial = self.partial_text.strip()
# #         interrupt_time = time.time()

# #         self.is_bot_speaking = False
# #         self.interrupt_start_time = None

# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         await self._send_clear_event()

# #         self.jitter_buffer.clear()

# #         asyncio.create_task(
# #             self._interruption_fallback(interrupted_partial, interrupt_time)
# #         )

# #     # ================= INTERRUPT HELPERS =================

# #     async def _send_clear_event(self):
# #         if self.stream_sid:
# #             try:
# #                 await self.send(text_data=json.dumps({
# #                     "event": "clear",
# #                     "streamSid": self.stream_sid
# #                 }))
# #                 print("📢 Twilio audio buffer cleared")
# #             except Exception as e:
# #                 print(f"❌ Clear event failed: {e}")

# #     async def _interruption_fallback(self, partial_text, interrupt_time):
# #         await asyncio.sleep(1.5)

# #         if self.last_dispatch_time > interrupt_time:
# #             print("✅ Interrupt speech already dispatched via normal path")
# #             return

# #         if self.is_bot_speaking or self.is_processing:
# #             print("⏭️ Interrupt fallback skipped (pipeline busy)")
# #             return

# #         final_text = None
# #         try:
# #             final_text = self.final_text_queue.get_nowait()
# #         except asyncio.QueueEmpty:
# #             pass

# #         text = final_text or self.partial_text.strip() or partial_text
# #         self.partial_text = ""

# #         if not text or len(text.split()) < self.MIN_WORD_COUNT:
# #             print("⏭️ Interrupt text too short:", text)
# #             return

# #         normalized = text.lower().strip()
# #         if normalized == self.last_dispatched_text:
# #             print("⏭️ Interrupt duplicate skipped:", text)
# #             return

# #         print("⚡ INTERRUPT FALLBACK DISPATCH:", text)
# #         self.last_dispatched_text = normalized
# #         self.last_dispatch_time = time.time()

# #         self.is_processing = True
# #         try:
# #             async with self.processing_lock:
# #                 await self.handle_ai_reply(text)
# #         finally:
# #             self.is_processing = False

# #     # ================= STREAMING LLM BRIDGE =================

# #     async def _stream_llm(self, system_prompt, user_message):
# #         queue = asyncio.Queue()
# #         loop = asyncio.get_event_loop()

# #         def _run_streaming():
# #             try:
# #                 for chunk in generate_response_streaming(system_prompt, user_message):
# #                     loop.call_soon_threadsafe(queue.put_nowait, chunk)
# #             except Exception as e:
# #                 print(f"❌ LLM Streaming error: {e}")
# #             loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

# #         loop.run_in_executor(None, _run_streaming)

# #         while True:
# #             chunk = await queue.get()
# #             if chunk is None:
# #                 break
# #             yield chunk

# #     # ================= AI (STREAMING) =================

# #     async def handle_ai_reply(self, text):
# #         """
# #         STREAMING PIPELINE — streams LLM tokens, synthesizes per sentence, plays audio.
# #         Respects tts_language and skip_output_translation flags from strategy prep_result.
# #         """
# #         pipeline_start = time.time()
# #         text = text.strip()
# #         if not text:
# #             return

# #         normalized = text.lower().strip()

# #         # ── END INTENT ────────────────────────────────────────
# #         if is_end_intent(normalized):
# #             print("📴 END INTENT DETECTED:", text)

# #             await save_message(self.conversation, "user", text)

# #             farewell_en = "Thank you for calling. Have a great day!"
# #             farewell = farewell_en
# #             if self.language != "en":
# #                 farewell = await sync_to_async(translate_text)(
# #                     farewell_en, from_lang="en", to_lang=self.language
# #                 )

# #             await save_message(self.conversation, "bot", farewell)

# #             if self.tts_task and not self.tts_task.done():
# #                 self.tts_task.cancel()
# #                 try:
# #                     await self.tts_task
# #                 except asyncio.CancelledError:
# #                     pass

# #             await self.send_tts(farewell)
# #             await close_conversation(self.conversation)

# #             await self.send(text_data=json.dumps({"event": "stop"}))

# #             self.is_connected = False
# #             await self.close()
# #             return

# #         # ── MAIN STREAMING PIPELINE ───────────────────────────
# #         # ── MAIN STREAMING PIPELINE ───────────────────────────
# #         print("🧠 AI INPUT:", text)
# #         await save_message(self.conversation, "user", text)

# #         # Step 1: Prepare FIRST — so we can read flags before deciding to translate
# #         t_prep = time.time()
# #         prep_result = await sync_to_async(prepare_streaming)(
# #             self.agent_id, text, self.session_id  # pass raw text
# #         )
# #         prep_ms = round((time.time() - t_prep) * 1000)

# #         # Read language control flags
# #         tts_language = prep_result.get("tts_language", self.language)
# #         skip_output_translation = prep_result.get("skip_output_translation", False)
# #         skip_input_translation = prep_result.get("skip_input_translation", False)  # ← NEW

# #         # Step 2: Translate input to English ONLY if not skipped
# #         # t_translate_in = time.time()
# #         # message_for_ai = text
# #         # if not skip_input_translation and self.language != "en":
# #         #     message_for_ai = await sync_to_async(translate_text)(
# #         #         text, from_lang=self.language, to_lang="en"
# #         #     )
# #         #     print(f"🌐 [{self.language}→en]: {message_for_ai}")
# #         # translate_in_ms = round((time.time() - t_translate_in) * 1000)


# #         # Step 2: Translate input
# #         t_translate_in = time.time()
# #         message_for_ai = text
# #         translate_input_to = prep_result.get("translate_input_to", None)  # None = normal bot

# #         if translate_input_to == "gu":
# #             # Interview bot only — translate to Gujarati
# #             if self.language != "gu":
# #                 message_for_ai = await sync_to_async(translate_text)(
# #                     text, from_lang=self.language, to_lang="gu"
# #                 )
# #                 print(f"🌐 [{self.language}→gu]: {message_for_ai}")

# #         elif translate_input_to is None and self.language != "en":
# #             # Normal bots — translate to English as original behaviour
# #             message_for_ai = await sync_to_async(translate_text)(
# #                 text, from_lang=self.language, to_lang="en"
# #             )
# #             print(f"🌐 [{self.language}→en]: {message_for_ai}")

# #         translate_in_ms = round((time.time() - t_translate_in) * 1000)

# #         # Step 3a: Static reply — no LLM streaming needed
# #         if "static_reply" in prep_result:
# #             reply = prep_result["static_reply"]
# #             if not reply:
# #                 return

# #             reply_for_user = reply
# #             # Skip translation if strategy has already produced the correct output language
# #             if not skip_output_translation and self.language != "en":
# #                 reply_for_user = await sync_to_async(translate_text)(
# #                     reply, from_lang="en", to_lang=self.language
# #                 )

# #             total_ms = round((time.time() - pipeline_start) * 1000)
# #             print(f"⏱ PIPELINE (static): prep={prep_ms}ms | TOTAL={total_ms}ms")

# #             await save_message(self.conversation, "bot", reply_for_user)
# #             print("🤖 BOT REPLY:", reply_for_user)

# #             if self.tts_task and not self.tts_task.done():
# #                 self.tts_task.cancel()
# #                 try:
# #                     await self.tts_task
# #                 except asyncio.CancelledError:
# #                     pass

# #             # Use tts_language for synthesis (may differ from self.language)
# #             self.tts_task = asyncio.create_task(
# #                 self.send_tts(reply_for_user, tts_language=tts_language)
# #             )
# #             return

# #         # Step 3b: STREAMING LLM + PER-SENTENCE TTS
# #         system_prompt = prep_result["system_prompt"]
# #         user_message = prep_result["user_message"]

# #         if not skip_input_translation and message_for_ai != text:
# #             user_message = message_for_ai

# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         self.is_bot_speaking = True
# #         t_llm = time.time()

# #         audio_queue = asyncio.Queue()
# #         full_response = ""
# #         first_sentence_time = None

# #         async def streaming_producer():
# #             nonlocal full_response, first_sentence_time
# #             sentence_buffer = ""
# #             loop = asyncio.get_event_loop()

# #             async for chunk in self._stream_llm(system_prompt, user_message):
# #                 if not self.is_bot_speaking:
# #                     break
# #                 full_response += chunk
# #                 sentence_buffer += chunk

# #                 boundary = re.search(r'[.!?।]\s', sentence_buffer)
# #                 if boundary:
# #                     sentence = sentence_buffer[:boundary.start() + 1].strip()
# #                     sentence_buffer = sentence_buffer[boundary.end():]
# #                     if sentence:
# #                         if first_sentence_time is None:
# #                             first_sentence_time = time.time()
# #                             print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

# #                         tts_text = sentence
# #                         # Only translate if strategy hasn't taken ownership of output language
# #                         if not skip_output_translation and self.language != "en":
# #                             tts_text = await sync_to_async(translate_text)(
# #                                 sentence, from_lang="en", to_lang=self.language
# #                             )

# #                         try:
# #                             ulaw = await asyncio.wait_for(
# #                                 loop.run_in_executor(
# #                                     None,
# #                                     lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
# #                                 ),
# #                                 timeout=15
# #                             )
# #                             await audio_queue.put(ulaw)
# #                         except asyncio.TimeoutError:
# #                             print(f"❌ TTS timeout: {sentence[:40]}")

# #             # Handle remaining text after stream ends
# #             if sentence_buffer.strip() and self.is_bot_speaking:
# #                 sentence = sentence_buffer.strip()
# #                 if first_sentence_time is None:
# #                     first_sentence_time = time.time()
# #                     print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

# #                 tts_text = sentence
# #                 # Only translate if strategy hasn't taken ownership of output language
# #                 if not skip_output_translation and self.language != "en":
# #                     tts_text = await sync_to_async(translate_text)(
# #                         sentence, from_lang="en", to_lang=self.language
# #                     )
# #                 try:
# #                     ulaw = await asyncio.wait_for(
# #                         loop.run_in_executor(
# #                             None,
# #                             lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
# #                         ),
# #                         timeout=15
# #                     )
# #                     await audio_queue.put(ulaw)
# #                 except asyncio.TimeoutError:
# #                     pass

# #             await audio_queue.put(None)

# #         async def streaming_consumer():
# #             """Streams audio to Twilio as soon as each sentence's TTS is ready."""
# #             while True:
# #                 ulaw = await audio_queue.get()
# #                 if ulaw is None:
# #                     break
# #                 if not self.is_bot_speaking:
# #                     break
# #                 await self._stream_ulaw(ulaw)

# #         producer_task = asyncio.create_task(streaming_producer())
# #         consumer_task = asyncio.create_task(streaming_consumer())
# #         self.tts_task = consumer_task

# #         try:
# #             await asyncio.gather(producer_task, consumer_task)
# #         except asyncio.CancelledError:
# #             print("🛑 STREAMING TTS CANCELLED")
# #         except Exception as e:
# #             print("❌ STREAMING ERROR:", e)
# #         finally:
# #             self.is_bot_speaking = False

# #         llm_ms = round((time.time() - t_llm) * 1000)
# #         total_ms = round((time.time() - pipeline_start) * 1000)
# #         print(f"⏱ STREAMING PIPELINE: translate_in={translate_in_ms}ms | prep={prep_ms}ms | LLM+TTS={llm_ms}ms | TOTAL={total_ms}ms")

# #         # Save the full bot reply — no translation needed if strategy owns the language
# #         reply_for_user = full_response
# #         if not skip_output_translation and self.language != "en" and full_response:
# #             reply_for_user = await sync_to_async(translate_text)(
# #                 full_response, from_lang="en", to_lang=self.language
# #             )
# #         if reply_for_user:
# #             await save_message(self.conversation, "bot", reply_for_user)
# #         print("🤖 BOT REPLY:", reply_for_user)

# #         if full_response:
# #             await sync_to_async(finalize_streaming)(full_response, prep_result)

# #     # ================= TTS HELPERS =================

# #     def _build_tts_synthesizer(self, language: str = None):
# #         """
# #         Build and return a reusable SpeechSynthesizer.
# #         language param allows building for a specific language (e.g. "gu" for interview bot).
# #         Defaults to self.language if not specified.
# #         """
# #         lang = language or self.language
# #         speech_config = speechsdk.SpeechConfig(
# #             subscription=os.getenv("AZURE_SPEECH_KEY"),
# #             region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
# #         )
# #         speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
# #         speech_config.set_speech_synthesis_output_format(
# #             speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
# #         )
# #         return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)



# #     def _synthesize_ulaw_sarvam(self, text: str) -> bytes:
# #         """
# #         Synthesize Gujarati speech using Sarvam AI (Bulbul v3 — priya voice).
# #         Gets WAV (PCM 8khz 16bit mono) from Sarvam, strips header, encodes to G711 ulaw for Twilio.
# #         """
# #         import requests as req
# #         import base64

# #         url = "https://api.sarvam.ai/text-to-speech"

# #         headers = {
# #             "api-subscription-key": os.getenv("SARVAM_API_KEY"),
# #             "Content-Type": "application/json"
# #         }

# #         payload = {
# #             "inputs": [text],
# #             "target_language_code": "gu-IN",
# #             "speaker": "ishita",
# #             "model": "bulbul:v3",
# #             "pace": 1.1,
# #             "speech_sample_rate": 8000,   # 8khz — must match Twilio
# #             "enable_preprocessing": True,
# #             "enc_format": "wav"           # get WAV — safer than mulaw, we convert ourselves
# #         }

# #         try:
# #             response = req.post(url, headers=headers, json=payload, timeout=10)
# #             result = response.json()
# #             print(f"🎙️ Sarvam response keys: {list(result.keys())}")

# #             audio_b64 = result["audios"][0]
# #             wav_bytes = base64.b64decode(audio_b64)
# #             print(f"✅ Sarvam WAV received: {len(wav_bytes)} bytes")

# #             # Strip WAV header to get raw PCM
# #             pcm = strip_wav_header(wav_bytes)
# #             print(f"✅ PCM after header strip: {len(pcm)} bytes")

# #             # Ensure even number of bytes
# #             if len(pcm) % 2 != 0:
# #                 pcm = pcm[:-1]

# #             # Convert PCM 16bit → G711 ulaw for Twilio
# #             ulaw = encode_g711(pcm)
# #             print(f"✅ Sarvam ulaw encoded: {len(ulaw)} bytes")
# #             return ulaw

# #         except Exception as e:
# #             print(f"❌ Sarvam TTS error: {e}")
# #             print(f"❌ Sarvam response: {response.text if 'response' in locals() else 'no response'}")
# #             return b""


# #     def _synthesize_ulaw(self, text: str, language: str = None) -> bytes:
# #         lang = language or self.language

# #         # ── Gujarati → use Sarvam AI ──────────────────────────
# #         if self.use_sarvam and lang == "gu":
# #             print(f"🎙️ Using Sarvam TTS for Gujarati")
# #             return self._synthesize_ulaw_sarvam(text)

# #         # ── English / Hindi → use Azure as before ─────────────
# #         ssml = build_ssml(text, lang)

# #         if lang != self.language:
# #             speech_config = speechsdk.SpeechConfig(
# #                 subscription=os.getenv("AZURE_SPEECH_KEY"),
# #                 region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
# #             )
# #             speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
# #             speech_config.set_speech_synthesis_output_format(
# #                 speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
# #             )
# #             synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
# #             result = synthesizer.speak_ssml_async(ssml).get()
# #         else:
# #             result = self._tts_synthesizer.speak_ssml_async(ssml).get()

# #         if result.reason == speechsdk.ResultReason.Canceled:
# #             details = result.cancellation_details
# #             print("❌ TTS Canceled:", details.reason, details.error_details)
# #             return b""

# #         pcm = result.audio_data
# #         pcm = strip_wav_header(pcm)

# #         if len(pcm) % 2 != 0:
# #             pcm = pcm[:-1]

# #         return encode_g711(pcm)

# #     async def _stream_ulaw(self, ulaw: bytes):
# #         """
# #         Stream u-law audio frames to Twilio with clock-anchored timing.
# #         Silence padding prevents clipping at start/end of each segment.
# #         """
# #         if not ulaw:
# #             return

# #         loop = asyncio.get_event_loop()

# #         # 3 silence frames before audio (~60ms) to prevent leading clip
# #         for _ in range(3):
# #             if not self.is_bot_speaking:
# #                 return
# #             await self._send_media_frame(SILENCE_FRAME)
# #             await asyncio.sleep(0.020)

# #         # Main audio — clock-anchored so timing never drifts
# #         start_time = loop.time()
# #         for idx, i in enumerate(range(0, len(ulaw), 160)):
# #             if not self.is_bot_speaking:
# #                 print("🛑 TTS stopped mid-stream")
# #                 return

# #             chunk = ulaw[i:i + 160].ljust(160, b'\x7f')
# #             await self._send_media_frame(chunk)

# #             target_time = start_time + (idx + 1) * 0.020
# #             sleep_duration = target_time - loop.time()
# #             if sleep_duration > 0:
# #                 await asyncio.sleep(sleep_duration)

# #         # 3 silence frames after audio (~60ms) to prevent trailing click/pop
# #         for _ in range(3):
# #             if not self.is_bot_speaking:
# #                 return
# #             await self._send_media_frame(SILENCE_FRAME)
# #             await asyncio.sleep(0.020)

# #     async def _send_media_frame(self, chunk: bytes):
# #         """Centralised send helper that always includes streamSid."""
# #         payload = base64.b64encode(chunk).decode()
# #         msg = {
# #             "event": "media",
# #             "media": {"payload": payload}
# #         }
# #         if self.stream_sid:
# #             msg["streamSid"] = self.stream_sid
# #         await self.send(text_data=json.dumps(msg))

# #     # ================= TTS (kept for static replies / intro) =================

# #     async def send_tts(self, text, tts_language: str = None):
# #         """
# #         Synthesize and stream a full text reply.
# #         tts_language overrides self.language for synthesis — used by interview bot
# #         to force Gujarati voice on static replies and intro.
# #         """
# #         self.is_bot_speaking = True
# #         loop = asyncio.get_event_loop()
# #         lang = tts_language or self.language

# #         try:
# #             sentences = split_into_sentences(text)
# #             audio_queue = asyncio.Queue()

# #             async def producer():
# #                 for sentence in sentences:
# #                     if not self.is_bot_speaking:
# #                         break
# #                     try:
# #                         ulaw = await asyncio.wait_for(
# #                             loop.run_in_executor(
# #                                 None,
# #                                 lambda s=sentence, l=lang: self._synthesize_ulaw(s, l)
# #                             ),
# #                             timeout=15
# #                         )
# #                     except asyncio.TimeoutError:
# #                         print(f"❌ TTS TIMEOUT for sentence: {sentence[:40]}")
# #                         ulaw = b""
# #                     await audio_queue.put(ulaw)
# #                 await audio_queue.put(None)

# #             async def consumer():
# #                 while True:
# #                     ulaw = await audio_queue.get()
# #                     if ulaw is None:
# #                         break
# #                     if not self.is_bot_speaking:
# #                         break
# #                     await self._stream_ulaw(ulaw)

# #             producer_task = asyncio.create_task(producer())
# #             consumer_task = asyncio.create_task(consumer())

# #             await asyncio.gather(producer_task, consumer_task)

# #         except asyncio.CancelledError:
# #             print("🛑 TTS CANCELLED")
# #             raise

# #         except Exception as e:
# #             print("❌ TTS ERROR:", e)

# #         finally:
# #             self.is_bot_speaking = False

# #     # ================= DISCONNECT =================

# #     async def disconnect(self, close_code):
# #         print("🔌 DISCONNECTED:", close_code)
# #         self.is_connected = False

# #         if hasattr(self, "keepalive_task"):
# #             self.keepalive_task.cancel()
# #             try:
# #                 await self.keepalive_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if hasattr(self, "final_consumer_task"):
# #             self.final_consumer_task.cancel()
# #             try:
# #                 await self.final_consumer_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if hasattr(self, "recognizer"):
# #             try:
# #                 self.recognizer.stop_continuous_recognition_async()
# #             except Exception:
# #                 pass

# #         if hasattr(self, "push_stream"):
# #             try:
# #                 self.push_stream.close()
# #             except Exception:
# #                 pass

# #         if hasattr(self, "conversation"):
# #             await close_conversation(self.conversation)


























































#a azure vado chhe je switch bi thay chhe






# from urllib.parse import parse_qs
# import audioop
# from asgiref.sync import sync_to_async
# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from conversations.services.core.dialogue_engine import process_message, prepare_streaming, finalize_streaming, get_agent_tts_language
# from conversations.services.azure_openai_service import generate_response_streaming
# from conversations.services.speech_service import create_speech_recognizer
# from conversations.services.translator_service import translate_text
# import asyncio
# import os
# import azure.cognitiveservices.speech as speechsdk
# import time
# import base64
# import uuid
# import numpy as np
# import re
# from django.utils import timezone

# from agents.models import VoiceAgent
# from conversations.models import Conversation, Message


# # ================= DATABASE =================

# @sync_to_async
# def create_conversation(agent_id, session_id, user_number):
#     return Conversation.objects.create(
#         agent_id=agent_id,
#         session_id=session_id,
#         user_number=user_number
#     )


# @sync_to_async
# def save_message(conversation, role, text):
#     last = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
#     if last and last.text.strip() == text.strip() and last.role == role:
#         return
#     Message.objects.create(conversation=conversation, role=role, text=text)


# @sync_to_async
# def update_user_number(conversation, number):
#     conversation.user_number = number
#     conversation.save()


# @sync_to_async
# def close_conversation(conversation):
#     conversation.ended_at = timezone.now()
#     conversation.save()


# @sync_to_async
# def get_agent_summary(agent_id):
#     try:
#         agent = VoiceAgent.objects.get(id=agent_id)
#         company = agent.company_name or "our company"
#         if agent.summary:
#             summary = agent.summary.strip().rstrip(".")
#             return f"Hello, me {agent.name} hu, {company} se. {summary}."
#         return f"Hello, me {agent.name} hu, {company}."
#     except VoiceAgent.DoesNotExist:
#         return "Hello, how can I assist you today?"


# @sync_to_async
# def mark_intro_shown(agent_id, session_id):
#     from conversations.models import ConversationSession
#     from agents.models import VoiceAgent
#     try:
#         agent = VoiceAgent.objects.get(id=agent_id)
#         session, _ = ConversationSession.objects.get_or_create(
#             agent=agent,
#             session_id=session_id
#         )
#         state = session.state or {}
#         state["intro_shown"] = True
#         session.state = state
#         session.save()
#     except Exception as e:
#         print("❌ mark_intro_shown error:", e)


# # ================= AUDIO =================

# def decode_g711(ulaw):
#     return audioop.ulaw2lin(ulaw, 2)


# def encode_g711(pcm):
#     return audioop.lin2ulaw(pcm, 2)


# def strip_wav_header(data: bytes) -> bytes:
#     if data[:4] != b'RIFF':
#         return data
#     offset = 12
#     while offset < len(data) - 8:
#         chunk_id = data[offset:offset + 4]
#         chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
#         if chunk_id == b'data':
#             return data[offset + 8:]
#         offset += 8 + chunk_size
#     return data[44:]  # safe fallback


# # G.711 u-law silence value is 0x7F
# SILENCE_FRAME = b'\x7f' * 160


# def split_into_sentences(text: str) -> list:
#     sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', text) if s.strip()]
#     return sentences if sentences else [text]


# def is_end_intent(text: str) -> bool:
#     text = text.lower().strip()
#     end_keywords = [
#         "bye", "goodbye", "ok bye", "okay bye",
#         "thank you", "thanks a lot",
#         "that's all", "no thanks", "call end",
#         "અلविदा",
#         "બાय", "આભાર"
#     ]
#     return any(keyword in text for keyword in end_keywords)


# # ================= SSML BUILDER =================

# TTS_VOICE_MAP = {
#     "en": "en-IN-AnanyaNeural",
#     "hi": "hi-IN-AnanyaNeural",
#     "gu": "gu-IN-DhwaniNeural",
# }

# SSML_STYLE_MAP = {
#     "en": None,
#     "hi": None,
#     "gu": None,
# }

# SSML_PROSODY_MAP = {
#     "en": {"rate": "-3%", "pitch": "+1Hz"},
#     "hi": {"rate": "-3%", "pitch": "0Hz"},
#     "gu": {"rate": "+10%", "pitch": "0Hz"},  # slightly slower for Gujarati clarity
# }

# # def _inject_english_lang_tags(text: str) -> str:
# #     """
# #     Wraps ALL English words (uppercase, lowercase, acronyms, mixed like B.Tech, MIS, HR)
# #     in <lang xml:lang="en-IN"> tags so Azure gu-IN-DhwaniNeural pronounces them
# #     correctly instead of skipping them silently.
# #     """
# #     import re

# #     # Escape any XML special chars in the text BEFORE injecting tags
# #     # (but don't escape our own injected tags)
# #     def escape_xml(s):
# #         return s.replace('&', '&amp;').replace('"', '&quot;')

# #     # Split text into Gujarati chunks and English chunks
# #     # English = any sequence containing A-Za-z (includes MIS, HR, B.Tech, v2, 10th etc.)
# #     pattern = re.compile(r'([A-Za-z][A-Za-z0-9.\-/]*)')

# #     result = []
# #     last_end = 0

# #     for match in pattern.finditer(text):
# #         start, end = match.start(), match.end()

# #         # Gujarati part before this English word — escape it
# #         gujarati_part = text[last_end:start]
# #         if gujarati_part:
# #             result.append(escape_xml(gujarati_part))

# #         # English word — wrap in lang tag
# #         english_word = match.group(1)
# #         result.append(f'<lang xml:lang="en-IN">{escape_xml(english_word)}</lang>')

# #         last_end = end

# #     # Remaining Gujarati text after last English word
# #     remaining = text[last_end:]
# #     if remaining:
# #         result.append(escape_xml(remaining))

# #     return ''.join(result)




# def _inject_english_lang_tags(text: str) -> str:
#     import re

#     def escape_xml(s):
#         return s.replace('&', '&amp;').replace('"', '&quot;')

#     def expand_if_acronym(word: str) -> str:
#         # Pure acronym: all caps only (MIS, HR, GST, TDS)
#         if re.match(r'^[A-Z][A-Z0-9]+$', word):
#             return ' '.join(word)           # "MIS" → "M I S"

#         # Complex technical codes: starts with 2+ caps, has digits/hyphens/slashes
#         # e.g. GSTR-2A → G S T R 2 A,  GSTR-2A/2B → G S T R 2 A 2 B
#         if re.match(r'^[A-Z]{2,}', word) and re.search(r'[-/0-9]', word):
#             # Strip hyphens/slashes → split alphanumeric segments → spell each out
#             parts = re.split(r'[-/]', word)      # ["GSTR", "2A"] or ["GSTR", "2A", "2B"]
#             spelled = []
#             for part in parts:
#                 if re.match(r'^[A-Z0-9]+$', part):
#                     spelled.append(' '.join(part))  # "GSTR" → "G S T R", "2A" → "2 A"
#                 else:
#                     spelled.append(part)            # mixed-case stays as-is
#             return ' '.join(spelled)               # "G S T R 2 A"

#         return word  # normal mixed-case words: B.Tech, prepare, report — untouched

#     pattern = re.compile(r'([A-Za-z][A-Za-z0-9.\-/]*)')

#     result = []
#     last_end = 0

#     for match in pattern.finditer(text):
#         start, end = match.start(), match.end()

#         gujarati_part = text[last_end:start]
#         if gujarati_part:
#             result.append(escape_xml(gujarati_part))

#         english_word = match.group(1)
#         expanded = expand_if_acronym(english_word)
#         result.append(f'<lang xml:lang="en-IN">{escape_xml(expanded)}</lang>')

#         last_end = end

#     remaining = text[last_end:]
#     if remaining:
#         result.append(escape_xml(remaining))

#     return ''.join(result)




# def build_ssml(text: str, language: str) -> str:
#     voice = TTS_VOICE_MAP.get(language, TTS_VOICE_MAP["en"])
#     style = SSML_STYLE_MAP.get(language)
#     prosody = SSML_PROSODY_MAP.get(language, SSML_PROSODY_MAP["en"])
#     lang_tag = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}.get(language, "en-IN")

#     # For Gujarati: wrap English words in English lang tags before building SSML
#     if language == "gu":
#         text = _inject_english_lang_tags(text)
#     else:
#         # For non-Gujarati: just escape XML special chars
#         text = text.replace('&', '&amp;')

#     prosody_open = f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}">'
#     prosody_close = '</prosody>'

#     if style:
#         inner = (
#             f'<mstts:express-as style="{style}">'
#             f'{prosody_open}{text}{prosody_close}'
#             f'</mstts:express-as>'
#         )
#     else:
#         inner = f'{prosody_open}{text}{prosody_close}'

#     return (
#         f'<speak version="1.0" '
#         f'xmlns="http://www.w3.org/2001/10/synthesis" '
#         f'xmlns:mstts="http://www.w3.org/2001/mstts" '
#         f'xml:lang="{lang_tag}">'
#         f'<voice name="{voice}">'
#         f'{inner}'
#         f'</voice>'
#         f'</speak>'
#     )

# # ================= CONSUMER =================

# class VoiceBotConsumer(AsyncWebsocketConsumer):

#     async def connect(self):
#         self.loop = asyncio.get_running_loop()

#         params = parse_qs(self.scope["query_string"].decode())
#         self.agent_id = params.get("agent_id", [None])[0]
#         self.user_number = params.get("from", ["unknown"])[0]
#         self.language = params.get("language", ["en"])[0]

#         if not self.agent_id:
#             await self.close()
#             return

#         self.session_id = str(uuid.uuid4())
#         self.conversation = await create_conversation(
#             self.agent_id, self.session_id, self.user_number
#         )

#         self.stream_sid = None

#         # ── STATE ──────────────────────────────────────────────
#         self.is_bot_speaking = False
#         self.is_connected = True
#         self.is_processing = False
#         self.partial_text = ""
#         self.final_text_queue = asyncio.Queue()

#         self.last_dispatched_text = ""
#         self.last_dispatch_time = 0.0

#         # ── LOCKS & TASKS ──────────────────────────────────────
#         self.processing_lock = asyncio.Lock()
#         self.tts_task = None

#         # ── AUDIO / VAD ────────────────────────────────────────
#         self.jitter_buffer = []
#         self.jitter_delay = 2

#         self.speech_active = False
#         self.silence_start_time = None

#         self.SPEECH_DETECT_RMS = 200
#         self.SILENCE_TRIGGER_SEC = 1.2
#         self.MIN_WORD_COUNT = 1

#         # Interrupt detection
#         self.interrupt_start_time = None
#         self.INTERRUPT_RMS = 300
#         self.INTERRUPT_HOLD_SEC = 0.3

#         # ── STT SETUP ──────────────────────────────────────────
#         self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
#         self._setup_stt_callbacks()
#         self.recognizer.start_continuous_recognition_async()

#         # ── TTS SYNTHESIZER (reused — avoids per-call connection overhead) ──
#         self._tts_synthesizer = self._build_tts_synthesizer()

#         await self.accept()

#         summary = await get_agent_summary(self.agent_id)

#         # Get agent's required TTS language
#         agent_tts_lang = await sync_to_async(get_agent_tts_language)(self.agent_id)

#         if agent_tts_lang != "en":
#             # Interview bot — translate intro to Gujarati, play with Azure gu voice
#             summary = await sync_to_async(translate_text)(
#                 summary, from_lang="en", to_lang=agent_tts_lang
#             )
#             print(f"🌐 Interview bot intro in {agent_tts_lang}: {summary}")
#             asyncio.create_task(self.send_tts(summary, tts_language=agent_tts_lang))
#         else:
#             # All other bots
#             if self.language != "en":
#                 summary = await sync_to_async(translate_text)(
#                     summary, from_lang="en", to_lang=self.language
#                 )
#             asyncio.create_task(self.send_tts(summary))

#         await mark_intro_shown(self.agent_id, self.session_id)

#         self.final_consumer_task = asyncio.create_task(self._final_text_consumer())

#         self.keepalive_task = asyncio.create_task(self._keepalive_loop())

#     # ================= KEEPALIVE =================

#     async def _keepalive_loop(self):
#         while self.is_connected:
#             await asyncio.sleep(25)
#             if not self.is_connected:
#                 break
#             try:
#                 await self.send(text_data=json.dumps({"event": "ping"}))
#                 print("🏓 Keepalive ping sent")
#             except Exception as e:
#                 print(f"❌ Keepalive failed: {e}")
#                 break

#     def _setup_stt_callbacks(self):
#         def handle_recognizing(evt):
#             text = evt.result.text.strip() if evt.result.text else ""
#             self.loop.call_soon_threadsafe(self._set_partial, text)

#         def handle_recognized(evt):
#             text = evt.result.text.strip() if evt.result.text else ""
#             if text:
#                 detected_lang = evt.result.properties.get(
#                     speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
#                 )
#                 lang_code = detected_lang.split("-")[0] if detected_lang else "en"
#                 if lang_code in ["en", "hi", "gu"]:
#                     self.loop.call_soon_threadsafe(self._set_language, lang_code)

#                 print(f"✅ Azure FINAL [{detected_lang}]: {text}")
#                 self.loop.call_soon_threadsafe(
#                     lambda: self.final_text_queue.put_nowait(text)
#                 )

#         def handle_canceled(evt):
#             print("⚠️ STT Canceled:", evt.result.cancellation_details)

#         self.recognizer.recognizing.connect(handle_recognizing)
#         self.recognizer.recognized.connect(handle_recognized)
#         self.recognizer.canceled.connect(handle_canceled)

#     def _set_partial(self, text):
#         self.partial_text = text

#     def _set_language(self, lang_code):
#         if self.language != lang_code:
#             print(f"🌐 Language switched to: {lang_code}")
#             self.language = lang_code
#             # Rebuild synthesizer so next TTS call uses the correct voice
#             self._tts_synthesizer = self._build_tts_synthesizer()

#     async def _final_text_consumer(self):
#         while self.is_connected:
#             try:
#                 text = await asyncio.wait_for(self.final_text_queue.get(), timeout=1.0)
#             except asyncio.TimeoutError:
#                 continue
#             except Exception:
#                 break

#             if not text:
#                 continue

#             if self.is_bot_speaking or self.is_processing:
#                 print("⏭️ Skipped (bot busy):", text)
#                 continue

#             normalized = text.lower().strip()
#             if normalized == self.last_dispatched_text:
#                 print("⏭️ Duplicate skipped:", text)
#                 continue

#             if time.time() - self.last_dispatch_time < 0.8:
#                 print("⏭️ Cooldown skip:", text)
#                 continue

#             if len(text.split()) < self.MIN_WORD_COUNT:
#                 print("⏭️ Too short:", text)
#                 continue

#             print("⚡ DISPATCHING TO AI:", text)
#             self.last_dispatched_text = normalized
#             self.last_dispatch_time = time.time()
#             self.partial_text = ""

#             self.is_processing = True
#             try:
#                 async with self.processing_lock:
#                     await self.handle_ai_reply(text)
#             finally:
#                 self.is_processing = False

#     # ================= RECEIVE =================

#     async def receive(self, text_data=None, bytes_data=None):
#         if not text_data:
#             return

#         try:
#             data = json.loads(text_data)

#             if data.get("event") == "start":
#                 self.stream_sid = data["start"].get("streamSid")
#                 print(f"📡 streamSid captured: {self.stream_sid}")
#                 try:
#                     number = data["start"]["customParameters"]["callerNumber"]
#                     self.user_number = number
#                     await update_user_number(self.conversation, number)
#                 except Exception:
#                     pass

#             if data.get("event") == "media":
#                 await self._handle_audio_chunk(data)

#         except Exception as e:
#             print("❌ RECEIVE ERROR:", e)

#     async def _handle_audio_chunk(self, data):
#         payload = base64.b64decode(data["media"]["payload"])
#         pcm = decode_g711(payload)

#         # Dynamic gain — boosts quiet/soft/slow voices automatically
#         pcm_np = np.frombuffer(pcm, dtype=np.int16).copy()
#         current_rms = audioop.rms(pcm, 2)
#         if current_rms > 50:
#             gain = min(1200 / current_rms, 6.0)
#             pcm_np = np.clip(pcm_np * gain, -32768, 32767).astype(np.int16)
#         pcm = pcm_np.tobytes()

#         if len(pcm) % 2 != 0:
#             pcm = pcm[:-1]

#         # Jitter buffer
#         self.jitter_buffer.append(pcm)
#         if len(self.jitter_buffer) < self.jitter_delay:
#             return

#         pcm = self.jitter_buffer.pop(0)
#         rms = audioop.rms(pcm, 2)

#         # Drop truly corrupt packets only
#         pcm_check = np.frombuffer(pcm, dtype=np.int16)
#         if int(np.abs(pcm_check).max()) == 32767 and rms > 28000:
#             return

#         # ── INTERRUPT DETECTION ────────────────────────────────
#         if self.is_bot_speaking:
#             return  # Do NOT feed audio to Azure STT while bot is speaking

#         # Feed to Azure STT only when bot is silent
#         self.push_stream.write(pcm)

#         # ── AGGRESSIVE PARTIAL-TEXT DISPATCH ───────────────────
#         if rms > self.SPEECH_DETECT_RMS:
#             self.speech_active = True
#             self.silence_start_time = None
#         else:
#             if self.speech_active:
#                 if self.silence_start_time is None:
#                     self.silence_start_time = time.time()
#                 elif time.time() - self.silence_start_time > self.SILENCE_TRIGGER_SEC:
#                     self.speech_active = False
#                     self.silence_start_time = None

#                     if (
#                         not self.is_bot_speaking
#                         and not self.is_processing
#                         and self.partial_text
#                     ):
#                         fallback_text = self.partial_text.strip()
#                         self.partial_text = ""

#                         if len(fallback_text.split()) >= self.MIN_WORD_COUNT:
#                             normalized = fallback_text.lower()
#                             if normalized != self.last_dispatched_text:
#                                 if time.time() - self.last_dispatch_time >= 0.8:
#                                     print("⚡ FAST DISPATCH (partial VAD):", fallback_text)
#                                     self.last_dispatched_text = normalized
#                                     self.last_dispatch_time = time.time()
#                                     self.is_processing = True
#                                     try:
#                                         async with self.processing_lock:
#                                             await self.handle_ai_reply(fallback_text)
#                                     finally:
#                                         self.is_processing = False

#     async def _check_interrupt(self, rms):
#         """Detect user barge-in while bot is speaking."""
#         if rms < self.INTERRUPT_RMS:
#             self.interrupt_start_time = None
#             return

#         if self.interrupt_start_time is None:
#             self.interrupt_start_time = time.time()
#             return

#         if time.time() - self.interrupt_start_time < self.INTERRUPT_HOLD_SEC:
#             return

#         print("🛑 INTERRUPT DETECTED — stopping bot, capturing user speech")

#         interrupted_partial = self.partial_text.strip()
#         interrupt_time = time.time()

#         self.is_bot_speaking = False
#         self.interrupt_start_time = None

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         await self._send_clear_event()

#         self.jitter_buffer.clear()

#         asyncio.create_task(
#             self._interruption_fallback(interrupted_partial, interrupt_time)
#         )

#     # ================= INTERRUPT HELPERS =================

#     async def _send_clear_event(self):
#         if self.stream_sid:
#             try:
#                 await self.send(text_data=json.dumps({
#                     "event": "clear",
#                     "streamSid": self.stream_sid
#                 }))
#                 print("📢 Twilio audio buffer cleared")
#             except Exception as e:
#                 print(f"❌ Clear event failed: {e}")

#     async def _interruption_fallback(self, partial_text, interrupt_time):
#         await asyncio.sleep(1.5)

#         if self.last_dispatch_time > interrupt_time:
#             print("✅ Interrupt speech already dispatched via normal path")
#             return

#         if self.is_bot_speaking or self.is_processing:
#             print("⏭️ Interrupt fallback skipped (pipeline busy)")
#             return

#         final_text = None
#         try:
#             final_text = self.final_text_queue.get_nowait()
#         except asyncio.QueueEmpty:
#             pass

#         text = final_text or self.partial_text.strip() or partial_text
#         self.partial_text = ""

#         if not text or len(text.split()) < self.MIN_WORD_COUNT:
#             print("⏭️ Interrupt text too short:", text)
#             return

#         normalized = text.lower().strip()
#         if normalized == self.last_dispatched_text:
#             print("⏭️ Interrupt duplicate skipped:", text)
#             return

#         print("⚡ INTERRUPT FALLBACK DISPATCH:", text)
#         self.last_dispatched_text = normalized
#         self.last_dispatch_time = time.time()

#         self.is_processing = True
#         try:
#             async with self.processing_lock:
#                 await self.handle_ai_reply(text)
#         finally:
#             self.is_processing = False

#     # ================= STREAMING LLM BRIDGE =================

#     async def _stream_llm(self, system_prompt, user_message):
#         queue = asyncio.Queue()
#         loop = asyncio.get_event_loop()

#         def _run_streaming():
#             try:
#                 for chunk in generate_response_streaming(system_prompt, user_message):
#                     loop.call_soon_threadsafe(queue.put_nowait, chunk)
#             except Exception as e:
#                 print(f"❌ LLM Streaming error: {e}")
#             loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

#         loop.run_in_executor(None, _run_streaming)

#         while True:
#             chunk = await queue.get()
#             if chunk is None:
#                 break
#             yield chunk

#     # ================= AI (STREAMING) =================

#     async def handle_ai_reply(self, text):
#         """
#         STREAMING PIPELINE — streams LLM tokens, synthesizes per sentence, plays audio.
#         Respects tts_language and skip_output_translation flags from strategy prep_result.
#         """
#         pipeline_start = time.time()
#         text = text.strip()
#         if not text:
#             return

#         normalized = text.lower().strip()

#         # ── END INTENT ────────────────────────────────────────
#         if is_end_intent(normalized):
#             print("📴 END INTENT DETECTED:", text)

#             await save_message(self.conversation, "user", text)

#             farewell_en = "Thank you! call kar ne ke liye apka sukriya!"
#             farewell = farewell_en
#             if self.language != "en":
#                 farewell = await sync_to_async(translate_text)(
#                     farewell_en, from_lang="en", to_lang=self.language
#                 )

#             await save_message(self.conversation, "bot", farewell)

#             if self.tts_task and not self.tts_task.done():
#                 self.tts_task.cancel()
#                 try:
#                     await self.tts_task
#                 except asyncio.CancelledError:
#                     pass

#             await self.send_tts(farewell)
#             await close_conversation(self.conversation)

#             await self.send(text_data=json.dumps({"event": "stop"}))

#             self.is_connected = False
#             await self.close()
#             return

#         # ── MAIN STREAMING PIPELINE ───────────────────────────
#         # ── MAIN STREAMING PIPELINE ───────────────────────────
#         print("🧠 AI INPUT:", text)
#         await save_message(self.conversation, "user", text)

#         # Step 1: Prepare FIRST — so we can read flags before deciding to translate
#         t_prep = time.time()
#         prep_result = await sync_to_async(prepare_streaming)(
#             self.agent_id, text, self.session_id  # pass raw text
#         )
#         prep_ms = round((time.time() - t_prep) * 1000)

#         # Read language control flags
#         tts_language = prep_result.get("tts_language", self.language)
#         skip_output_translation = prep_result.get("skip_output_translation", False)
#         skip_input_translation = prep_result.get("skip_input_translation", False)  # ← NEW

#         # Step 2: Translate input to English ONLY if not skipped
#         # t_translate_in = time.time()
#         # message_for_ai = text
#         # if not skip_input_translation and self.language != "en":
#         #     message_for_ai = await sync_to_async(translate_text)(
#         #         text, from_lang=self.language, to_lang="en"
#         #     )
#         #     print(f"🌐 [{self.language}→en]: {message_for_ai}")
#         # translate_in_ms = round((time.time() - t_translate_in) * 1000)


#         # Step 2: Translate input
#         t_translate_in = time.time()
#         message_for_ai = text
#         translate_input_to = prep_result.get("translate_input_to", None)  # None = normal bot

#         if translate_input_to == "gu":
#             # Interview bot only — translate to Gujarati
#             if self.language != "gu":
#                 message_for_ai = await sync_to_async(translate_text)(
#                     text, from_lang=self.language, to_lang="gu"
#                 )
#                 print(f"🌐 [{self.language}→gu]: {message_for_ai}")

#         elif translate_input_to is None and self.language != "en":
#             # Normal bots — translate to English as original behaviour
#             message_for_ai = await sync_to_async(translate_text)(
#                 text, from_lang=self.language, to_lang="en"
#             )
#             print(f"🌐 [{self.language}→en]: {message_for_ai}")

#         translate_in_ms = round((time.time() - t_translate_in) * 1000)

#         # Step 3a: Static reply — no LLM streaming needed
#         if "static_reply" in prep_result:
#             reply = prep_result["static_reply"]
#             if not reply:
#                 return

#             reply_for_user = reply
#             # Skip translation if strategy has already produced the correct output language
#             if not skip_output_translation and self.language != "en":
#                 reply_for_user = await sync_to_async(translate_text)(
#                     reply, from_lang="en", to_lang=self.language
#                 )

#             total_ms = round((time.time() - pipeline_start) * 1000)
#             print(f"⏱ PIPELINE (static): prep={prep_ms}ms | TOTAL={total_ms}ms")

#             await save_message(self.conversation, "bot", reply_for_user)
#             print("🤖 BOT REPLY:", reply_for_user)

#             if self.tts_task and not self.tts_task.done():
#                 self.tts_task.cancel()
#                 try:
#                     await self.tts_task
#                 except asyncio.CancelledError:
#                     pass

#             # Use tts_language for synthesis (may differ from self.language)
#             self.tts_task = asyncio.create_task(
#                 self.send_tts(reply_for_user, tts_language=tts_language)
#             )
#             return

#         # Step 3b: STREAMING LLM + PER-SENTENCE TTS
#         system_prompt = prep_result["system_prompt"]
#         user_message = prep_result["user_message"]

#         if not skip_input_translation and message_for_ai != text:
#             user_message = message_for_ai

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         self.is_bot_speaking = True
#         t_llm = time.time()

#         audio_queue = asyncio.Queue()
#         full_response = ""
#         first_sentence_time = None

#         async def streaming_producer():
#             nonlocal full_response, first_sentence_time
#             sentence_buffer = ""
#             loop = asyncio.get_event_loop()

#             async for chunk in self._stream_llm(system_prompt, user_message):
#                 if not self.is_bot_speaking:
#                     break
#                 full_response += chunk
#                 sentence_buffer += chunk

#                 boundary = re.search(r'[.!?।]\s', sentence_buffer)
#                 if boundary:
#                     sentence = sentence_buffer[:boundary.start() + 1].strip()
#                     sentence_buffer = sentence_buffer[boundary.end():]
#                     if sentence:
#                         if first_sentence_time is None:
#                             first_sentence_time = time.time()
#                             print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

#                         tts_text = sentence
#                         # Only translate if strategy hasn't taken ownership of output language
#                         if not skip_output_translation and self.language != "en":
#                             tts_text = await sync_to_async(translate_text)(
#                                 sentence, from_lang="en", to_lang=self.language
#                             )

#                         try:
#                             ulaw = await asyncio.wait_for(
#                                 loop.run_in_executor(
#                                     None,
#                                     lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
#                                 ),
#                                 timeout=15
#                             )
#                             await audio_queue.put(ulaw)
#                         except asyncio.TimeoutError:
#                             print(f"❌ TTS timeout: {sentence[:40]}")

#             # Handle remaining text after stream ends
#             if sentence_buffer.strip() and self.is_bot_speaking:
#                 sentence = sentence_buffer.strip()
#                 if first_sentence_time is None:
#                     first_sentence_time = time.time()
#                     print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

#                 tts_text = sentence
#                 # Only translate if strategy hasn't taken ownership of output language
#                 if not skip_output_translation and self.language != "en":
#                     tts_text = await sync_to_async(translate_text)(
#                         sentence, from_lang="en", to_lang=self.language
#                     )
#                 try:
#                     ulaw = await asyncio.wait_for(
#                         loop.run_in_executor(
#                             None,
#                             lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
#                         ),
#                         timeout=15
#                     )
#                     await audio_queue.put(ulaw)
#                 except asyncio.TimeoutError:
#                     pass

#             await audio_queue.put(None)

#         async def streaming_consumer():
#             """Streams audio to Twilio as soon as each sentence's TTS is ready."""
#             while True:
#                 ulaw = await audio_queue.get()
#                 if ulaw is None:
#                     break
#                 if not self.is_bot_speaking:
#                     break
#                 await self._stream_ulaw(ulaw)

#         producer_task = asyncio.create_task(streaming_producer())
#         consumer_task = asyncio.create_task(streaming_consumer())
#         self.tts_task = consumer_task

#         try:
#             await asyncio.gather(producer_task, consumer_task)
#         except asyncio.CancelledError:
#             print("🛑 STREAMING TTS CANCELLED")
#         except Exception as e:
#             print("❌ STREAMING ERROR:", e)
#         finally:
#             self.is_bot_speaking = False

#         llm_ms = round((time.time() - t_llm) * 1000)
#         total_ms = round((time.time() - pipeline_start) * 1000)
#         print(f"⏱ STREAMING PIPELINE: translate_in={translate_in_ms}ms | prep={prep_ms}ms | LLM+TTS={llm_ms}ms | TOTAL={total_ms}ms")

#         # Save the full bot reply — no translation needed if strategy owns the language
#         reply_for_user = full_response
#         if not skip_output_translation and self.language != "en" and full_response:
#             reply_for_user = await sync_to_async(translate_text)(
#                 full_response, from_lang="en", to_lang=self.language
#             )
#         if reply_for_user:
#             await save_message(self.conversation, "bot", reply_for_user)
#         print("🤖 BOT REPLY:", reply_for_user)

#         if full_response:
#             await sync_to_async(finalize_streaming)(full_response, prep_result)

#     # ================= TTS HELPERS =================

#     def _build_tts_synthesizer(self, language: str = None):
#         """
#         Build and return a reusable SpeechSynthesizer.
#         language param allows building for a specific language (e.g. "gu" for interview bot).
#         Defaults to self.language if not specified.
#         """
#         lang = language or self.language
#         speech_config = speechsdk.SpeechConfig(
#             subscription=os.getenv("AZURE_SPEECH_KEY"),
#             region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
#         )
#         speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
#         speech_config.set_speech_synthesis_output_format(
#             speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#         )
#         return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)


#     def _synthesize_ulaw(self, text: str, language: str = None) -> bytes:
#         lang = language or self.language
#         # ── All languages (en / hi / gu) → Azure ─────────────
#         ssml = build_ssml(text, lang)

#         if lang != self.language:
#             speech_config = speechsdk.SpeechConfig(
#                 subscription=os.getenv("AZURE_SPEECH_KEY"),
#                 region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
#             )
#             speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
#             speech_config.set_speech_synthesis_output_format(
#                 speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#             )
#             synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
#             result = synthesizer.speak_ssml_async(ssml).get()
#         else:
#             result = self._tts_synthesizer.speak_ssml_async(ssml).get()

#         if result.reason == speechsdk.ResultReason.Canceled:
#             details = result.cancellation_details
#             print("❌ TTS Canceled:", details.reason, details.error_details)
#             return b""

#         pcm = result.audio_data
#         pcm = strip_wav_header(pcm)

#         if len(pcm) % 2 != 0:
#             pcm = pcm[:-1]

#         return encode_g711(pcm)

#     async def _stream_ulaw(self, ulaw: bytes):
#         """
#         Stream u-law audio frames to Twilio with clock-anchored timing.
#         Silence padding prevents clipping at start/end of each segment.
#         """
#         if not ulaw:
#             return

#         loop = asyncio.get_event_loop()

#         # 3 silence frames before audio (~60ms) to prevent leading clip
#         for _ in range(3):
#             if not self.is_bot_speaking:
#                 return
#             await self._send_media_frame(SILENCE_FRAME)
#             await asyncio.sleep(0.020)

#         # Main audio — clock-anchored so timing never drifts
#         start_time = loop.time()
#         for idx, i in enumerate(range(0, len(ulaw), 160)):
#             if not self.is_bot_speaking:
#                 print("🛑 TTS stopped mid-stream")
#                 return

#             chunk = ulaw[i:i + 160].ljust(160, b'\x7f')
#             await self._send_media_frame(chunk)

#             target_time = start_time + (idx + 1) * 0.020
#             sleep_duration = target_time - loop.time()
#             if sleep_duration > 0:
#                 await asyncio.sleep(sleep_duration)

#         # 3 silence frames after audio (~60ms) to prevent trailing click/pop
#         for _ in range(3):
#             if not self.is_bot_speaking:
#                 return
#             await self._send_media_frame(SILENCE_FRAME)
#             await asyncio.sleep(0.020)

#     async def _send_media_frame(self, chunk: bytes):
#         """Centralised send helper that always includes streamSid."""
#         payload = base64.b64encode(chunk).decode()
#         msg = {
#             "event": "media",
#             "media": {"payload": payload}
#         }
#         if self.stream_sid:
#             msg["streamSid"] = self.stream_sid
#         await self.send(text_data=json.dumps(msg))

#     # ================= TTS (kept for static replies / intro) =================

#     async def send_tts(self, text, tts_language: str = None):
#         """
#         Synthesize and stream a full text reply.
#         tts_language overrides self.language for synthesis — used by interview bot
#         to force Gujarati voice on static replies and intro.
#         """
#         self.is_bot_speaking = True
#         loop = asyncio.get_event_loop()
#         lang = tts_language or self.language

#         try:
#             sentences = split_into_sentences(text)
#             audio_queue = asyncio.Queue()

#             async def producer():
#                 for sentence in sentences:
#                     if not self.is_bot_speaking:
#                         break
#                     try:
#                         ulaw = await asyncio.wait_for(
#                             loop.run_in_executor(
#                                 None,
#                                 lambda s=sentence, l=lang: self._synthesize_ulaw(s, l)
#                             ),
#                             timeout=15
#                         )
#                     except asyncio.TimeoutError:
#                         print(f"❌ TTS TIMEOUT for sentence: {sentence[:40]}")
#                         ulaw = b""
#                     await audio_queue.put(ulaw)
#                 await audio_queue.put(None)

#             async def consumer():
#                 while True:
#                     ulaw = await audio_queue.get()
#                     if ulaw is None:
#                         break
#                     if not self.is_bot_speaking:
#                         break
#                     await self._stream_ulaw(ulaw)

#             producer_task = asyncio.create_task(producer())
#             consumer_task = asyncio.create_task(consumer())

#             await asyncio.gather(producer_task, consumer_task)

#         except asyncio.CancelledError:
#             print("🛑 TTS CANCELLED")
#             raise

#         except Exception as e:
#             print("❌ TTS ERROR:", e)

#         finally:
#             self.is_bot_speaking = False

#     # ================= DISCONNECT =================

#     async def disconnect(self, close_code):
#         print("🔌 DISCONNECTED:", close_code)
#         self.is_connected = False

#         if hasattr(self, "keepalive_task"):
#             self.keepalive_task.cancel()
#             try:
#                 await self.keepalive_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "final_consumer_task"):
#             self.final_consumer_task.cancel()
#             try:
#                 await self.final_consumer_task
#             except asyncio.CancelledError:
#                 pass

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "recognizer"):
#             try:
#                 self.recognizer.stop_continuous_recognition_async()
#             except Exception:
#                 pass

#         if hasattr(self, "push_stream"):
#             try:
#                 self.push_stream.close()
#             except Exception:
#                 pass

#         if hasattr(self, "conversation"):
#             await close_conversation(self.conversation)















# #a etele mukyo chhe kem ke 3 lan bot bhega thaya ani uer no code complete working chhe a code same uper jevo chhe uper vado cplpmlate working chhe ane ama ame sravam umeri chhe gujrati mate 






# from urllib.parse import parse_qs
# import audioop
# from asgiref.sync import sync_to_async
# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from conversations.services.core.dialogue_engine import process_message, prepare_streaming, finalize_streaming, get_agent_tts_language
# from conversations.services.azure_openai_service import generate_response_streaming
# from conversations.services.speech_service import create_speech_recognizer
# from conversations.services.translator_service import translate_text
# import asyncio
# import os
# import azure.cognitiveservices.speech as speechsdk
# import time
# import base64
# import uuid
# import numpy as np
# import re
# from django.utils import timezone

# from agents.models import VoiceAgent
# from conversations.models import Conversation, Message


# # ================= DATABASE =================

# @sync_to_async
# def create_conversation(agent_id, session_id, user_number):
#     return Conversation.objects.create(
#         agent_id=agent_id,
#         session_id=session_id,
#         user_number=user_number
#     )


# @sync_to_async
# def save_message(conversation, role, text):
#     last = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
#     if last and last.text.strip() == text.strip() and last.role == role:
#         return
#     Message.objects.create(conversation=conversation, role=role, text=text)


# @sync_to_async
# def update_user_number(conversation, number):
#     conversation.user_number = number
#     conversation.save()


# @sync_to_async
# def close_conversation(conversation):
#     conversation.ended_at = timezone.now()
#     conversation.save()


# @sync_to_async
# def get_agent_summary(agent_id, agent_tts_lang="en"):
#     try:
#         agent = VoiceAgent.objects.get(id=agent_id)
#         company = agent.company_name or "our company"
#         summary = agent.summary.strip().rstrip(".") if agent.summary else ""

#         if agent_tts_lang == "gu":
#             # Real estate — greeting directly in Gujarati, no translation needed
#             if summary:
#                 return f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. {summary}"
#             return f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. મિલકત ખરીદવી, વેચવી, ભાડે આપવી કે રોકાણ — કોઈ પણ બાબતમાં મદદ જોઈએ તો કહો!"

#         elif agent_tts_lang == "interview_en":
#             # Interview — clean English
#             if summary:
#                 return f"Hello, I am {agent.name} from {company}. {summary}."
#             return f"Hello, I am {agent.name}."

#         else:
#             # All other bots — Hinglish
#             if summary:
#                 return f"Hello, main {agent.name} hoon, {company} se. {summary}."
#             return f"Hello, main {agent.name} hoon, {company} se."

#     except VoiceAgent.DoesNotExist:
#         return "Hello, how can I assist you today?"

# @sync_to_async
# def mark_intro_shown(agent_id, session_id):
#     from conversations.models import ConversationSession
#     from agents.models import VoiceAgent
#     try:
#         agent = VoiceAgent.objects.get(id=agent_id)
#         session, _ = ConversationSession.objects.get_or_create(
#             agent=agent,
#             session_id=session_id
#         )
#         state = session.state or {}
#         state["intro_shown"] = True
#         session.state = state
#         session.save()
#     except Exception as e:
#         print("❌ mark_intro_shown error:", e)


# # ================= AUDIO =================

# def decode_g711(ulaw):
#     return audioop.ulaw2lin(ulaw, 2)


# def encode_g711(pcm):
#     return audioop.lin2ulaw(pcm, 2)


# def strip_wav_header(data: bytes) -> bytes:
#     if data[:4] != b'RIFF':
#         return data
#     offset = 12
#     while offset < len(data) - 8:
#         chunk_id = data[offset:offset + 4]
#         chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
#         if chunk_id == b'data':
#             return data[offset + 8:]
#         offset += 8 + chunk_size
#     return data[44:]  # safe fallback


# # G.711 u-law silence value is 0x7F
# SILENCE_FRAME = b'\x7f' * 160
# SARVAM_API_KEY = "sk_a2r0mlxx_s7tfO2DKXgEx7NkbmVfOGFva"
# print(f"🔑 Sarvam key loaded: {SARVAM_API_KEY[:10]}...")

# def split_into_sentences(text: str, language: str = "en") -> list:
#     if language == "gu":
#         sentences = [s.strip() for s in re.split(r'(?<=[!?।])\s+|(?<=[.])\s+(?=[A-Z\u0A80-\u0AFF])', text) if s.strip()]
#     else:
#         sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', text) if s.strip()]
#     return sentences if sentences else [text]


# def is_end_intent(text: str) -> bool:
#     text = text.lower().strip()
#     end_keywords = [
#         "bye", "goodbye", "ok bye", "okay bye",
#         "thank you", "thanks a lot",
#         "that's all", "no thanks", "call end",
#         "અلविदा",
#         "બાय", "આભાર"
#     ]
#     return any(keyword in text for keyword in end_keywords)


# # ================= SSML BUILDER =================

# TTS_VOICE_MAP = {
#     "en": "en-IN-AnanyaNeural",
#     "hi": "hi-IN-AnanyaNeural",
#     "gu": "gu-IN-DhwaniNeural",
# }

# SSML_STYLE_MAP = {
#     "en": None,
#     "hi": None,
#     "gu": None,
# }

# SSML_PROSODY_MAP = {
#     "en": {"rate": "-3%", "pitch": "+1Hz"},
#     "hi": {"rate": "-3%", "pitch": "0Hz"},
#     "gu": {"rate": "+10%", "pitch": "0Hz"},  # slightly slower for Gujarati clarity
# }

# # def _inject_english_lang_tags(text: str) -> str:
# #     """
# #     Wraps ALL English words (uppercase, lowercase, acronyms, mixed like B.Tech, MIS, HR)
# #     in <lang xml:lang="en-IN"> tags so Azure gu-IN-DhwaniNeural pronounces them
# #     correctly instead of skipping them silently.
# #     """
# #     import re

# #     # Escape any XML special chars in the text BEFORE injecting tags
# #     # (but don't escape our own injected tags)
# #     def escape_xml(s):
# #         return s.replace('&', '&amp;').replace('"', '&quot;')

# #     # Split text into Gujarati chunks and English chunks
# #     # English = any sequence containing A-Za-z (includes MIS, HR, B.Tech, v2, 10th etc.)
# #     pattern = re.compile(r'([A-Za-z][A-Za-z0-9.\-/]*)')

# #     result = []
# #     last_end = 0

# #     for match in pattern.finditer(text):
# #         start, end = match.start(), match.end()

# #         # Gujarati part before this English word — escape it
# #         gujarati_part = text[last_end:start]
# #         if gujarati_part:
# #             result.append(escape_xml(gujarati_part))

# #         # English word — wrap in lang tag
# #         english_word = match.group(1)
# #         result.append(f'<lang xml:lang="en-IN">{escape_xml(english_word)}</lang>')

# #         last_end = end

# #     # Remaining Gujarati text after last English word
# #     remaining = text[last_end:]
# #     if remaining:
# #         result.append(escape_xml(remaining))

# #     return ''.join(result)




# def _inject_english_lang_tags(text: str) -> str:
#     import re

#     def escape_xml(s):
#         return s.replace('&', '&amp;').replace('"', '&quot;')

#     def expand_if_acronym(word: str) -> str:
#         # Pure acronym: all caps only (MIS, HR, GST, TDS)
#         if re.match(r'^[A-Z][A-Z0-9]+$', word):
#             return ' '.join(word)           # "MIS" → "M I S"

#         # Complex technical codes: starts with 2+ caps, has digits/hyphens/slashes
#         # e.g. GSTR-2A → G S T R 2 A,  GSTR-2A/2B → G S T R 2 A 2 B
#         if re.match(r'^[A-Z]{2,}', word) and re.search(r'[-/0-9]', word):
#             # Strip hyphens/slashes → split alphanumeric segments → spell each out
#             parts = re.split(r'[-/]', word)      # ["GSTR", "2A"] or ["GSTR", "2A", "2B"]
#             spelled = []
#             for part in parts:
#                 if re.match(r'^[A-Z0-9]+$', part):
#                     spelled.append(' '.join(part))  # "GSTR" → "G S T R", "2A" → "2 A"
#                 else:
#                     spelled.append(part)            # mixed-case stays as-is
#             return ' '.join(spelled)               # "G S T R 2 A"

#         return word  # normal mixed-case words: B.Tech, prepare, report — untouched

#     pattern = re.compile(r'([A-Za-z][A-Za-z0-9.\-/]*)')

#     result = []
#     last_end = 0

#     for match in pattern.finditer(text):
#         start, end = match.start(), match.end()

#         gujarati_part = text[last_end:start]
#         if gujarati_part:
#             result.append(escape_xml(gujarati_part))

#         english_word = match.group(1)
#         expanded = expand_if_acronym(english_word)
#         result.append(f'<lang xml:lang="en-IN">{escape_xml(expanded)}</lang>')

#         last_end = end

#     remaining = text[last_end:]
#     if remaining:
#         result.append(escape_xml(remaining))

#     return ''.join(result)




# def build_ssml(text: str, language: str) -> str:
#     voice = TTS_VOICE_MAP.get(language, TTS_VOICE_MAP["en"])
#     style = SSML_STYLE_MAP.get(language)
#     prosody = SSML_PROSODY_MAP.get(language, SSML_PROSODY_MAP["en"])
#     lang_tag = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}.get(language, "en-IN")

#     # For Gujarati: wrap English words in English lang tags before building SSML
#     if language == "gu":
#         text = _inject_english_lang_tags(text)
#     else:
#         # For non-Gujarati: just escape XML special chars
#         text = text.replace('&', '&amp;')

#     prosody_open = f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}">'
#     prosody_close = '</prosody>'

#     if style:
#         inner = (
#             f'<mstts:express-as style="{style}">'
#             f'{prosody_open}{text}{prosody_close}'
#             f'</mstts:express-as>'
#         )
#     else:
#         inner = f'{prosody_open}{text}{prosody_close}'

#     return (
#         f'<speak version="1.0" '
#         f'xmlns="http://www.w3.org/2001/10/synthesis" '
#         f'xmlns:mstts="http://www.w3.org/2001/mstts" '
#         f'xml:lang="{lang_tag}">'
#         f'<voice name="{voice}">'
#         f'{inner}'
#         f'</voice>'
#         f'</speak>'
#     )

# # ================= CONSUMER =================

# class VoiceBotConsumer(AsyncWebsocketConsumer):

#     async def connect(self):
#         self.loop = asyncio.get_running_loop()

#         params = parse_qs(self.scope["query_string"].decode())
#         self.agent_id = params.get("agent_id", [None])[0]
#         self.user_number = params.get("from", ["unknown"])[0]
#         self.language = params.get("language", ["en"])[0]

#         if not self.agent_id:
#             await self.close()
#             return

#         self.session_id = str(uuid.uuid4())
#         self.conversation = await create_conversation(
#             self.agent_id, self.session_id, self.user_number
#         )

#         self.stream_sid = None

#         # ── STATE ──────────────────────────────────────────────
#         self.is_bot_speaking = False
#         self.is_connected = True
#         self.is_processing = False
#         self.partial_text = ""
#         self.final_text_queue = asyncio.Queue()

#         self.last_dispatched_text = ""
#         self.last_dispatch_time = 0.0

#         # ── LOCKS & TASKS ──────────────────────────────────────
#         self.processing_lock = asyncio.Lock()
#         self.tts_task = None

#         # ── AUDIO / VAD ────────────────────────────────────────
#         self.jitter_buffer = []
#         self.jitter_delay = 2

#         self.speech_active = False
#         self.silence_start_time = None

#         self.SPEECH_DETECT_RMS = 200
#         self.SILENCE_TRIGGER_SEC = 1.2   # ⚡ was 1.2 — saves ~600ms per turn
#         self.MIN_WORD_COUNT = 1

#         # Interrupt detection
#         self.interrupt_start_time = None
#         self.INTERRUPT_RMS = 300
#         self.INTERRUPT_HOLD_SEC = 0.3

#         # ── STT SETUP ──────────────────────────────────────────
#         self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
#         self._setup_stt_callbacks()
#         self.recognizer.start_continuous_recognition_async()

#         # ── TTS SYNTHESIZER (reused — avoids per-call connection overhead) ──
#         self._tts_synthesizer = self._build_tts_synthesizer()

#         await self.accept()

#         # Get TTS language FIRST so greeting is built in correct language
#         agent_tts_lang = await sync_to_async(get_agent_tts_language)(self.agent_id)
#         self.agent_tts_lang = agent_tts_lang

#         # Get greeting already in correct language
#         summary = await get_agent_summary(self.agent_id, agent_tts_lang)

#         if agent_tts_lang == "gu":
#             # Real estate — greeting already in Gujarati
#             print(f"🌐 Real estate greeting in Gujarati: {summary}")
#             asyncio.create_task(self.send_tts(summary, tts_language="gu"))

#         elif agent_tts_lang == "interview_en":
#             # Interview — greeting already in English
#             print(f"🌐 Interview greeting in English: {summary}")
#             asyncio.create_task(self.send_tts(summary, tts_language="en"))

#         else:
#             # All other bots — greeting already in Hinglish
#             print(f"🌐 Hinglish greeting: {summary}")
#             asyncio.create_task(self.send_tts(summary))

#         await mark_intro_shown(self.agent_id, self.session_id)

#         self.final_consumer_task = asyncio.create_task(self._final_text_consumer())

#         self.keepalive_task = asyncio.create_task(self._keepalive_loop())

#     # ================= KEEPALIVE =================

#     async def _keepalive_loop(self):
#         while self.is_connected:
#             await asyncio.sleep(25)
#             if not self.is_connected:
#                 break
#             try:
#                 await self.send(text_data=json.dumps({"event": "ping"}))
#                 print("🏓 Keepalive ping sent")
#             except Exception as e:
#                 print(f"❌ Keepalive failed: {e}")
#                 break

#     def _setup_stt_callbacks(self):
#         def handle_recognizing(evt):
#             text = evt.result.text.strip() if evt.result.text else ""
#             self.loop.call_soon_threadsafe(self._set_partial, text)

#         def handle_recognized(evt):
#             text = evt.result.text.strip() if evt.result.text else ""
#             if text:
#                 detected_lang = evt.result.properties.get(
#                     speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
#                 )
#                 lang_code = detected_lang.split("-")[0] if detected_lang else "en"
#                 if lang_code in ["en", "hi", "gu"]:
#                     self.loop.call_soon_threadsafe(self._set_language, lang_code)

#                 print(f"✅ Azure FINAL [{detected_lang}]: {text}")
#                 self.loop.call_soon_threadsafe(
#                     lambda: self.final_text_queue.put_nowait(text)
#                 )

#         def handle_canceled(evt):
#             print("⚠️ STT Canceled:", evt.result.cancellation_details)

#         self.recognizer.recognizing.connect(handle_recognizing)
#         self.recognizer.recognized.connect(handle_recognized)
#         self.recognizer.canceled.connect(handle_canceled)

#     def _set_partial(self, text):
#         self.partial_text = text

#     def _set_language(self, lang_code):
#         if self.language != lang_code:
#             print(f"🌐 Language switched to: {lang_code}")
#             self.language = lang_code
#             # Rebuild synthesizer so next TTS call uses the correct voice
#             self._tts_synthesizer = self._build_tts_synthesizer()

#     async def _final_text_consumer(self):
#         while self.is_connected:
#             try:
#                 text = await asyncio.wait_for(self.final_text_queue.get(), timeout=1.0)
#             except asyncio.TimeoutError:
#                 continue
#             except Exception:
#                 break

#             if not text:
#                 continue

#             if self.is_bot_speaking or self.is_processing:
#                 print("⏭️ Skipped (bot busy):", text)
#                 continue

#             normalized = text.lower().strip()
#             if normalized == self.last_dispatched_text:
#                 print("⏭️ Duplicate skipped:", text)
#                 continue

#             if time.time() - self.last_dispatch_time < 0.5:  # ⚡ was 0.8 — faster turn-taking
#                 print("⏭️ Cooldown skip:", text)
#                 continue

#             if len(text.split()) < self.MIN_WORD_COUNT:
#                 print("⏭️ Too short:", text)
#                 continue

#             print("⚡ DISPATCHING TO AI:", text)
#             self.last_dispatched_text = normalized
#             self.last_dispatch_time = time.time()
#             self.partial_text = ""

#             self.is_processing = True
#             try:
#                 async with self.processing_lock:
#                     await self.handle_ai_reply(text)
#             finally:
#                 self.is_processing = False

#     # ================= RECEIVE =================

#     async def receive(self, text_data=None, bytes_data=None):
#         if not text_data:
#             return

#         try:
#             data = json.loads(text_data)

#             if data.get("event") == "start":
#                 self.stream_sid = data["start"].get("streamSid")
#                 print(f"📡 streamSid captured: {self.stream_sid}")
#                 try:
#                     number = data["start"]["customParameters"]["callerNumber"]
#                     self.user_number = number
#                     await update_user_number(self.conversation, number)
#                 except Exception:
#                     pass

#             if data.get("event") == "media":
#                 await self._handle_audio_chunk(data)

#         except Exception as e:
#             print("❌ RECEIVE ERROR:", e)

#     async def _handle_audio_chunk(self, data):
#         payload = base64.b64decode(data["media"]["payload"])
#         pcm = decode_g711(payload)

#         # Dynamic gain — boosts quiet/soft/slow voices automatically
#         pcm_np = np.frombuffer(pcm, dtype=np.int16).copy()
#         current_rms = audioop.rms(pcm, 2)
#         if current_rms > 50:
#             gain = min(1200 / current_rms, 6.0)
#             pcm_np = np.clip(pcm_np * gain, -32768, 32767).astype(np.int16)
#         pcm = pcm_np.tobytes()

#         if len(pcm) % 2 != 0:
#             pcm = pcm[:-1]

#         # Jitter buffer
#         self.jitter_buffer.append(pcm)
#         if len(self.jitter_buffer) < self.jitter_delay:
#             return

#         pcm = self.jitter_buffer.pop(0)
#         rms = audioop.rms(pcm, 2)

#         # Drop truly corrupt packets only
#         pcm_check = np.frombuffer(pcm, dtype=np.int16)
#         if int(np.abs(pcm_check).max()) == 32767 and rms > 28000:
#             return

#         # ── INTERRUPT DETECTION ────────────────────────────────
#         if self.is_bot_speaking:
#             return  # Do NOT feed audio to Azure STT while bot is speaking

#         # Feed to Azure STT only when bot is silent
#         self.push_stream.write(pcm)

#         # ── AGGRESSIVE PARTIAL-TEXT DISPATCH ───────────────────
#         if rms > self.SPEECH_DETECT_RMS:
#             self.speech_active = True
#             self.silence_start_time = None
#         else:
#             if self.speech_active:
#                 if self.silence_start_time is None:
#                     self.silence_start_time = time.time()
#                 elif time.time() - self.silence_start_time > self.SILENCE_TRIGGER_SEC:
#                     self.speech_active = False
#                     self.silence_start_time = None

#                     if (
#                         not self.is_bot_speaking
#                         and not self.is_processing
#                         and self.partial_text
#                     ):
#                         fallback_text = self.partial_text.strip()
#                         self.partial_text = ""

#                         if len(fallback_text.split()) >= self.MIN_WORD_COUNT:
#                             normalized = fallback_text.lower()
#                             if normalized != self.last_dispatched_text:
#                                 if time.time() - self.last_dispatch_time >= 0.5:  # ⚡ was 0.8
#                                     print("⚡ FAST DISPATCH (partial VAD):", fallback_text)
#                                     self.last_dispatched_text = normalized
#                                     self.last_dispatch_time = time.time()
#                                     self.is_processing = True
#                                     try:
#                                         async with self.processing_lock:
#                                             await self.handle_ai_reply(fallback_text)
#                                     finally:
#                                         self.is_processing = False

#     async def _check_interrupt(self, rms):
#         """Detect user barge-in while bot is speaking."""
#         if rms < self.INTERRUPT_RMS:
#             self.interrupt_start_time = None
#             return

#         if self.interrupt_start_time is None:
#             self.interrupt_start_time = time.time()
#             return

#         if time.time() - self.interrupt_start_time < self.INTERRUPT_HOLD_SEC:
#             return

#         print("🛑 INTERRUPT DETECTED — stopping bot, capturing user speech")

#         interrupted_partial = self.partial_text.strip()
#         interrupt_time = time.time()

#         self.is_bot_speaking = False
#         self.interrupt_start_time = None

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         await self._send_clear_event()

#         self.jitter_buffer.clear()

#         asyncio.create_task(
#             self._interruption_fallback(interrupted_partial, interrupt_time)
#         )

#     # ================= INTERRUPT HELPERS =================

#     async def _send_clear_event(self):
#         if self.stream_sid:
#             try:
#                 await self.send(text_data=json.dumps({
#                     "event": "clear",
#                     "streamSid": self.stream_sid
#                 }))
#                 print("📢 Twilio audio buffer cleared")
#             except Exception as e:
#                 print(f"❌ Clear event failed: {e}")

#     async def _interruption_fallback(self, partial_text, interrupt_time):
#         await asyncio.sleep(1.5)

#         if self.last_dispatch_time > interrupt_time:
#             print("✅ Interrupt speech already dispatched via normal path")
#             return

#         if self.is_bot_speaking or self.is_processing:
#             print("⏭️ Interrupt fallback skipped (pipeline busy)")
#             return

#         final_text = None
#         try:
#             final_text = self.final_text_queue.get_nowait()
#         except asyncio.QueueEmpty:
#             pass

#         text = final_text or self.partial_text.strip() or partial_text
#         self.partial_text = ""

#         if not text or len(text.split()) < self.MIN_WORD_COUNT:
#             print("⏭️ Interrupt text too short:", text)
#             return

#         normalized = text.lower().strip()
#         if normalized == self.last_dispatched_text:
#             print("⏭️ Interrupt duplicate skipped:", text)
#             return

#         print("⚡ INTERRUPT FALLBACK DISPATCH:", text)
#         self.last_dispatched_text = normalized
#         self.last_dispatch_time = time.time()

#         self.is_processing = True
#         try:
#             async with self.processing_lock:
#                 await self.handle_ai_reply(text)
#         finally:
#             self.is_processing = False

#     # ================= STREAMING LLM BRIDGE =================

#     async def _stream_llm(self, system_prompt, user_message):
#         queue = asyncio.Queue()
#         loop = asyncio.get_event_loop()

#         def _run_streaming():
#             try:
#                 for chunk in generate_response_streaming(system_prompt, user_message):
#                     loop.call_soon_threadsafe(queue.put_nowait, chunk)
#             except Exception as e:
#                 print(f"❌ LLM Streaming error: {e}")
#             loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

#         loop.run_in_executor(None, _run_streaming)

#         while True:
#             chunk = await queue.get()
#             if chunk is None:
#                 break
#             yield chunk

#     # ================= AI (STREAMING) =================

#     async def handle_ai_reply(self, text):
#         """
#         STREAMING PIPELINE — streams LLM tokens, synthesizes per sentence, plays audio.
#         Respects tts_language and skip_output_translation flags from strategy prep_result.
#         """
#         pipeline_start = time.time()
#         text = text.strip()
#         if not text:
#             return

#         normalized = text.lower().strip()

#         # ── END INTENT ────────────────────────────────────────
#         # ── END INTENT ────────────────────────────────────────
#         if is_end_intent(normalized):
#             print("📴 END INTENT DETECTED:", text)

#             await save_message(self.conversation, "user", text)

#             if self.agent_tts_lang == "gu":
#                 # Real estate — goodbye directly in Gujarati, no translation
#                 farewell = "આપનો ખૂબ ખૂબ આભાર! જ્યારે પણ મિલકત વિશે કોઈ પ્રશ્ન હોય, અમે હંમેશા ઉપલબ્ધ છીએ. ધ્યાન રાખજો!"

#             elif self.agent_tts_lang == "interview_en":
#                 # Interview — English goodbye
#                 farewell = "Thank you for your time. All the best for your preparation!"

#             else:
#                 # All other bots — Hinglish goodbye
#                 farewell = "Thank you for calling! Koi aur help chahiye toh zaroor call karna. Take care!"

#             await save_message(self.conversation, "bot", farewell)

#             if self.tts_task and not self.tts_task.done():
#                 self.tts_task.cancel()
#                 try:
#                     await self.tts_task
#                 except asyncio.CancelledError:
#                     pass

#             tts_lang_for_farewell = "gu" if self.agent_tts_lang == "gu" else "en"
#             await self.send_tts(farewell, tts_language=tts_lang_for_farewell)
#             await close_conversation(self.conversation)

#             await self.send(text_data=json.dumps({"event": "stop"}))

#             self.is_connected = False
#             await self.close()
#             return
#         # ── MAIN STREAMING PIPELINE ───────────────────────────
#         print("🧠 AI INPUT:", text)
#         await save_message(self.conversation, "user", text)

#         # Step 1: Prepare FIRST — so we can read flags before deciding to translate
#         t_prep = time.time()
#         prep_result = await sync_to_async(prepare_streaming)(
#             self.agent_id, text, self.session_id  # pass raw text
#         )
#         prep_ms = round((time.time() - t_prep) * 1000)

#         # Read language control flags
#         tts_language = prep_result.get("tts_language", self.language)
#         skip_output_translation = prep_result.get("skip_output_translation", False)
#         skip_input_translation = prep_result.get("skip_input_translation", False)  # ← NEW

#         # Step 2: Translate input to English ONLY if not skipped
#         # t_translate_in = time.time()
#         # message_for_ai = text
#         # if not skip_input_translation and self.language != "en":
#         #     message_for_ai = await sync_to_async(translate_text)(
#         #         text, from_lang=self.language, to_lang="en"
#         #     )
#         #     print(f"🌐 [{self.language}→en]: {message_for_ai}")
#         # translate_in_ms = round((time.time() - t_translate_in) * 1000)


#         # Step 2: Translate input
#         t_translate_in = time.time()
#         message_for_ai = text
#         translate_input_to = prep_result.get("translate_input_to", None)  # None = normal bot

#         if translate_input_to == "gu":
#             # Interview bot only — translate to Gujarati
#             if self.language != "gu":
#                 message_for_ai = await sync_to_async(translate_text)(
#                     text, from_lang=self.language, to_lang="gu"
#                 )
#                 print(f"🌐 [{self.language}→gu]: {message_for_ai}")

#         elif translate_input_to is None and self.language != "en":
#             # Normal bots — translate to English as original behaviour
#             message_for_ai = await sync_to_async(translate_text)(
#                 text, from_lang=self.language, to_lang="en"
#             )
#             print(f"🌐 [{self.language}→en]: {message_for_ai}")

#         translate_in_ms = round((time.time() - t_translate_in) * 1000)

#         # Step 3a: Static reply — no LLM streaming needed
#         if "static_reply" in prep_result:
#             reply = prep_result["static_reply"]
#             if not reply:
#                 return

#             reply_for_user = reply
#             # Skip translation if strategy has already produced the correct output language
#             if not skip_output_translation and self.language != "en":
#                 reply_for_user = await sync_to_async(translate_text)(
#                     reply, from_lang="en", to_lang=self.language
#                 )

#             total_ms = round((time.time() - pipeline_start) * 1000)
#             print(f"⏱ PIPELINE (static): prep={prep_ms}ms | TOTAL={total_ms}ms")

#             await save_message(self.conversation, "bot", reply_for_user)
#             print("🤖 BOT REPLY:", reply_for_user)

#             if self.tts_task and not self.tts_task.done():
#                 self.tts_task.cancel()
#                 try:
#                     await self.tts_task
#                 except asyncio.CancelledError:
#                     pass

#             # Use tts_language for synthesis (may differ from self.language)
#             self.tts_task = asyncio.create_task(
#                 self.send_tts(reply_for_user, tts_language=tts_language)
#             )
#             return

#         # Step 3b: STREAMING LLM + PER-SENTENCE TTS
#         system_prompt = prep_result["system_prompt"]
#         user_message = prep_result["user_message"]

#         if not skip_input_translation and message_for_ai != text:
#             user_message = message_for_ai

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         self.is_bot_speaking = True
#         t_llm = time.time()

#         audio_queue = asyncio.Queue()
#         full_response = ""
#         first_sentence_time = None

#         async def streaming_producer():
#             nonlocal full_response, first_sentence_time
#             sentence_buffer = ""
#             loop = asyncio.get_event_loop()

#             async for chunk in self._stream_llm(system_prompt, user_message):
#                 if not self.is_bot_speaking:
#                     break
#                 full_response += chunk
#                 sentence_buffer += chunk

#                 if tts_language == "gu":
#                     boundary = re.search(r'[!?।]\s|[.]\s+(?=[A-Z\u0A80-\u0AFF])', sentence_buffer)
#                 else:
#                     boundary = re.search(r'[.!?।]\s', sentence_buffer)
#                 if boundary:
#                     sentence = sentence_buffer[:boundary.start() + 1].strip()
#                     sentence_buffer = sentence_buffer[boundary.end():]
#                     if sentence:
#                         if first_sentence_time is None:
#                             first_sentence_time = time.time()
#                             print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

#                         tts_text = sentence
#                         # Only translate if strategy hasn't taken ownership of output language
#                         if not skip_output_translation and self.language != "en":
#                             tts_text = await sync_to_async(translate_text)(
#                                 sentence, from_lang="en", to_lang=self.language
#                             )

#                         try:
#                             ulaw = await asyncio.wait_for(
#                                 loop.run_in_executor(
#                                     None,
#                                     lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
#                                 ),
#                                 timeout=15
#                             )
#                             await audio_queue.put(ulaw)
#                         except asyncio.TimeoutError:
#                             print(f"❌ TTS timeout: {sentence[:40]}")

#             # Handle remaining text after stream ends
#             if sentence_buffer.strip() and self.is_bot_speaking:
#                 sentence = sentence_buffer.strip()
#                 if first_sentence_time is None:
#                     first_sentence_time = time.time()
#                     print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

#                 tts_text = sentence
#                 # Only translate if strategy hasn't taken ownership of output language
#                 if not skip_output_translation and self.language != "en":
#                     tts_text = await sync_to_async(translate_text)(
#                         sentence, from_lang="en", to_lang=self.language
#                     )
#                 try:
#                     ulaw = await asyncio.wait_for(
#                         loop.run_in_executor(
#                             None,
#                             lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
#                         ),
#                         timeout=15
#                     )
#                     await audio_queue.put(ulaw)
#                 except asyncio.TimeoutError:
#                     pass

#             await audio_queue.put(None)

#         async def streaming_consumer():
#             """Streams audio to Twilio as soon as each sentence's TTS is ready."""
#             while True:
#                 ulaw = await audio_queue.get()
#                 if ulaw is None:
#                     break
#                 if not self.is_bot_speaking:
#                     break
#                 await self._stream_ulaw(ulaw)

#         producer_task = asyncio.create_task(streaming_producer())
#         consumer_task = asyncio.create_task(streaming_consumer())
#         self.tts_task = consumer_task

#         try:
#             await asyncio.gather(producer_task, consumer_task)
#         except asyncio.CancelledError:
#             print("🛑 STREAMING TTS CANCELLED")
#         except Exception as e:
#             print("❌ STREAMING ERROR:", e)
#         finally:
#             self.is_bot_speaking = False

#         llm_ms = round((time.time() - t_llm) * 1000)
#         total_ms = round((time.time() - pipeline_start) * 1000)
#         print(f"⏱ STREAMING PIPELINE: translate_in={translate_in_ms}ms | prep={prep_ms}ms | LLM+TTS={llm_ms}ms | TOTAL={total_ms}ms")

#         # Save the full bot reply — no translation needed if strategy owns the language
#         reply_for_user = full_response
#         if not skip_output_translation and self.language != "en" and full_response:
#             reply_for_user = await sync_to_async(translate_text)(
#                 full_response, from_lang="en", to_lang=self.language
#             )
#         if reply_for_user:
#             await save_message(self.conversation, "bot", reply_for_user)
#         print("🤖 BOT REPLY:", reply_for_user)

#         if full_response:
#             await sync_to_async(finalize_streaming)(full_response, prep_result)

#     # ================= TTS HELPERS =================
    
#     def _build_tts_synthesizer(self, language: str = None):
        
#         """
#         Build and return a reusable SpeechSynthesizer.
#         language param allows building for a specific language (e.g. "gu" for interview bot).
#         Defaults to self.language if not specified.
#         """
#         lang = language or self.language
#         speech_config = speechsdk.SpeechConfig(
#             subscription=os.getenv("AZURE_SPEECH_KEY"),
#             region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
#         )
#         speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
#         speech_config.set_speech_synthesis_output_format(
#             speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#         )
#         return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    
    
#     def _synthesize_ulaw_sarvam(self, text: str) -> bytes:
#         """
#         Synthesize Gujarati speech using Sarvam AI (Bulbul v3 — priya voice).
#         Gets WAV (PCM 8khz 16bit mono) from Sarvam, strips header, encodes to G711 ulaw for Twilio.
#         """
#         import requests as req
#         import base64

#         url = "https://api.sarvam.ai/text-to-speech"

#         headers = {
#             "api-subscription-key": SARVAM_API_KEY,
#             "Content-Type": "application/json"
#         }

#         payload = {
#             "inputs": [text],
#             "target_language_code": "gu-IN",
#             "speaker": "ishita",
#             "model": "bulbul:v3",
#             "pace": 1.1,
#             "speech_sample_rate": 8000,   # 8khz — must match Twilio
#             "enable_preprocessing": True,
#             "enc_format": "wav"           # get WAV — safer than mulaw, we convert ourselves
#         }

#         try:
#             response = req.post(url, headers=headers, json=payload, timeout=10)
#             result = response.json()
#             print(f"🎙️ Sarvam response keys: {list(result.keys())}")

#             audio_b64 = result["audios"][0]
#             wav_bytes = base64.b64decode(audio_b64)
#             print(f"✅ Sarvam WAV received: {len(wav_bytes)} bytes")

#             # Strip WAV header to get raw PCM
#             pcm = strip_wav_header(wav_bytes)
#             print(f"✅ PCM after header strip: {len(pcm)} bytes")

#             # Ensure even number of bytes
#             if len(pcm) % 2 != 0:
#                 pcm = pcm[:-1]

#             # Convert PCM 16bit → G711 ulaw for Twilio
#             ulaw = encode_g711(pcm)
#             print(f"✅ Sarvam ulaw encoded: {len(ulaw)} bytes")
#             return ulaw

#         except Exception as e:
#             print(f"❌ Sarvam TTS error: {e}")
#             print(f"❌ Sarvam response: {response.text if 'response' in locals() else 'no response'}")
#             return b""
    
    

#     def _synthesize_ulaw(self, text: str, language: str = None) -> bytes:
#         lang = language or self.language
        
        
#         # ── Gujarati → Sarvam AI ──────────────────────────────
#         if lang == "gu":
#             return self._synthesize_ulaw_sarvam(text)
        
#         # ── All languages (en / hi / gu) → Azure ─────────────
#         ssml = build_ssml(text, lang)

#         if lang != self.language:
#             speech_config = speechsdk.SpeechConfig(
#                 subscription=os.getenv("AZURE_SPEECH_KEY"),
#                 region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
#             )
#             speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
#             speech_config.set_speech_synthesis_output_format(
#                 speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#             )
#             synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
#             result = synthesizer.speak_ssml_async(ssml).get()
#         else:
#             result = self._tts_synthesizer.speak_ssml_async(ssml).get()

#         if result.reason == speechsdk.ResultReason.Canceled:
#             details = result.cancellation_details
#             print("❌ TTS Canceled:", details.reason, details.error_details)
#             return b""

#         pcm = result.audio_data
#         pcm = strip_wav_header(pcm)

#         if len(pcm) % 2 != 0:
#             pcm = pcm[:-1]

#         return encode_g711(pcm)

#     async def _stream_ulaw(self, ulaw: bytes):
#         """
#         Stream u-law audio frames to Twilio with clock-anchored timing.
#         Silence padding prevents clipping at start/end of each segment.
#         """
#         if not ulaw:
#             return

#         loop = asyncio.get_event_loop()

#         # 2 silence frames before audio (~40ms) to prevent leading clip
#         for _ in range(2):
#             if not self.is_bot_speaking:
#                 return
#             await self._send_media_frame(SILENCE_FRAME)
#             await asyncio.sleep(0.020)

#         # Main audio — clock-anchored so timing never drifts
#         start_time = loop.time()
#         for idx, i in enumerate(range(0, len(ulaw), 160)):
#             if not self.is_bot_speaking:
#                 print("🛑 TTS stopped mid-stream")
#                 return

#             chunk = ulaw[i:i + 160].ljust(160, b'\x7f')
#             await self._send_media_frame(chunk)

#             target_time = start_time + (idx + 1) * 0.020
#             sleep_duration = target_time - loop.time()
#             if sleep_duration > 0:
#                 await asyncio.sleep(sleep_duration)

#         # 2 silence frames after audio (~40ms) to prevent trailing click/pop
#         for _ in range(2):
#             if not self.is_bot_speaking:
#                 return
#             await self._send_media_frame(SILENCE_FRAME)
#             await asyncio.sleep(0.020)

#     async def _send_media_frame(self, chunk: bytes):
#         """Centralised send helper that always includes streamSid."""
#         payload = base64.b64encode(chunk).decode()
#         msg = {
#             "event": "media",
#             "media": {"payload": payload}
#         }
#         if self.stream_sid:
#             msg["streamSid"] = self.stream_sid
#         await self.send(text_data=json.dumps(msg))

#     # ================= TTS (kept for static replies / intro) =================

#     async def send_tts(self, text, tts_language: str = None):
#         """
#         Synthesize and stream a full text reply.
#         tts_language overrides self.language for synthesis — used by interview bot
#         to force Gujarati voice on static replies and intro.
#         """
#         self.is_bot_speaking = True
#         loop = asyncio.get_event_loop()
#         lang = tts_language or self.language

#         try:
#             sentences = split_into_sentences(text, lang)
#             audio_queue = asyncio.Queue()

#             async def producer():
#                 for sentence in sentences:
#                     if not self.is_bot_speaking:
#                         break
#                     try:
#                         ulaw = await asyncio.wait_for(
#                             loop.run_in_executor(
#                                 None,
#                                 lambda s=sentence, l=lang: self._synthesize_ulaw(s, l)
#                             ),
#                             timeout=15
#                         )
#                     except asyncio.TimeoutError:
#                         print(f"❌ TTS TIMEOUT for sentence: {sentence[:40]}")
#                         ulaw = b""
#                     await audio_queue.put(ulaw)
#                 await audio_queue.put(None)

#             async def consumer():
#                 while True:
#                     ulaw = await audio_queue.get()
#                     if ulaw is None:
#                         break
#                     if not self.is_bot_speaking:
#                         break
#                     await self._stream_ulaw(ulaw)

#             producer_task = asyncio.create_task(producer())
#             consumer_task = asyncio.create_task(consumer())

#             await asyncio.gather(producer_task, consumer_task)

#         except asyncio.CancelledError:
#             print("🛑 TTS CANCELLED")
#             raise

#         except Exception as e:
#             print("❌ TTS ERROR:", e)

#         finally:
#             self.is_bot_speaking = False

#     # ================= DISCONNECT =================

#     async def disconnect(self, close_code):
#         print("🔌 DISCONNECTED:", close_code)
#         self.is_connected = False

#         if hasattr(self, "keepalive_task"):
#             self.keepalive_task.cancel()
#             try:
#                 await self.keepalive_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "final_consumer_task"):
#             self.final_consumer_task.cancel()
#             try:
#                 await self.final_consumer_task
#             except asyncio.CancelledError:
#                 pass

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "recognizer"):
#             try:
#                 self.recognizer.stop_continuous_recognition_async()
#             except Exception:
#                 pass

#         if hasattr(self, "push_stream"):
#             try:
#                 self.push_stream.close()
#             except Exception:
#                 pass

#         if hasattr(self, "conversation"):
#             await close_conversation(self.conversation)














# #a azure vado chhe je switch bi thay chhe






# from urllib.parse import parse_qs
# import audioop
# from asgiref.sync import sync_to_async
# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from conversations.services.core.dialogue_engine import process_message, prepare_streaming, finalize_streaming, get_agent_tts_language
# from conversations.services.azure_openai_service import generate_response_streaming
# from conversations.services.speech_service import create_speech_recognizer
# from conversations.services.translator_service import translate_text
# import asyncio
# import os
# import azure.cognitiveservices.speech as speechsdk
# import time
# import base64
# import uuid
# import numpy as np
# import re
# from django.utils import timezone

# from agents.models import VoiceAgent
# from conversations.models import Conversation, Message


# # ================= DATABASE =================

# @sync_to_async
# def create_conversation(agent_id, session_id, user_number):
#     return Conversation.objects.create(
#         agent_id=agent_id,
#         session_id=session_id,
#         user_number=user_number
#     )


# @sync_to_async
# def save_message(conversation, role, text):
#     last = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
#     if last and last.text.strip() == text.strip() and last.role == role:
#         return
#     Message.objects.create(conversation=conversation, role=role, text=text)


# @sync_to_async
# def update_user_number(conversation, number):
#     conversation.user_number = number
#     conversation.save()


# @sync_to_async
# def close_conversation(conversation):
#     conversation.ended_at = timezone.now()
#     conversation.save()


# # @sync_to_async
# # def get_agent_summary(agent_id):
# #     try:
# #         agent = VoiceAgent.objects.get(id=agent_id)
# #         company = agent.company_name or "our company"
# #         if agent.summary:
# #             summary = agent.summary.strip().rstrip(".")
# #             return f"Hello, me {agent.name} hu, {company} se hu. {summary}."
# #         return f"Hello, me {agent.name} hu, {company} se hu."
# #     except VoiceAgent.DoesNotExist:
# #         return "Hello, how can I assist you today?"




# @sync_to_async
# def get_agent_summary(agent_id, agent_tts_lang="en"):
#     try:
#         agent = VoiceAgent.objects.get(id=agent_id)
#         company = agent.company_name or "our company"
#         summary = agent.summary.strip().rstrip(".") if agent.summary else ""
 
#         if agent_tts_lang == "gu":
#             # Real estate — greeting directly in Gujarati, no translation needed
#             if summary:
#                 return f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. {summary}"
#             return f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. મિલકત ખરીદવી, વેચવી, ભાડે આપવી કે રોકાણ — કોઈ પણ બાબતમાં મદદ જોઈએ તો કહો!"
 
#         elif agent_tts_lang == "interview_en":
#             # Interview — clean English
#             if summary:
#                 return f"Hello, I am {agent.name} from {company}. {summary}."
#             return f"Hello, I am {agent.name}."
 
#         else:
#             # All other bots — Hinglish
#             if summary:
#                 return f"Hello, main {agent.name} hoon, {company} se. {summary}."
#             return f"Hello, main {agent.name} hoon, {company} se."
 
#     except VoiceAgent.DoesNotExist:
#         return "Hello, how can I assist you today?"


# @sync_to_async
# def mark_intro_shown(agent_id, session_id):
#     from conversations.models import ConversationSession
#     from agents.models import VoiceAgent
#     try:
#         agent = VoiceAgent.objects.get(id=agent_id)
#         session, _ = ConversationSession.objects.get_or_create(
#             agent=agent,
#             session_id=session_id
#         )
#         state = session.state or {}
#         state["intro_shown"] = True
#         session.state = state
#         session.save()
#     except Exception as e:
#         print("❌ mark_intro_shown error:", e)


# # ================= AUDIO =================

# def decode_g711(ulaw):
#     return audioop.ulaw2lin(ulaw, 2)


# def encode_g711(pcm):
#     return audioop.lin2ulaw(pcm, 2)


# def strip_wav_header(data: bytes) -> bytes:
#     if data[:4] != b'RIFF':
#         return data
#     offset = 12
#     while offset < len(data) - 8:
#         chunk_id = data[offset:offset + 4]
#         chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
#         if chunk_id == b'data':
#             return data[offset + 8:]
#         offset += 8 + chunk_size
#     return data[44:]  # safe fallback


# # G.711 u-law silence value is 0x7F
# SILENCE_FRAME = b'\x7f' * 160


# def split_into_sentences(text: str) -> list:
#     sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', text) if s.strip()]
#     return sentences if sentences else [text]


# def is_end_intent(text: str) -> bool:
#     text = text.lower().strip()
#     end_keywords = [
#         "bye", "goodbye", "ok bye", "okay bye",
#         "thank you", "thanks a lot",
#         "that's all", "no thanks", "call end",
#         "અلविदा",
#         "બાय", "આભાર"
#     ]
#     return any(keyword in text for keyword in end_keywords)


# # ================= SSML BUILDER =================

# TTS_VOICE_MAP = {
#     "en": "en-IN-AnanyaNeural",
#     "hi": "hi-IN-AnanyaNeural",
#     "gu": "gu-IN-DhwaniNeural",
# }

# SSML_STYLE_MAP = {
#     "en": None,
#     "hi": None,
#     "gu": None,
# }

# # SSML_PROSODY_MAP = {
# #     "en": {"rate": "-3%", "pitch": "+1Hz"},
# #     "hi": {"rate": "-3%", "pitch": "0Hz"},
# #     "gu": {"rate": "+10%", "pitch": "0Hz"},  # slightly slower for Gujarati clarity
# # }


# SSML_PROSODY_MAP = {
#     "en": {"rate": "+5%", "pitch": "+2Hz"},
#     "hi": {"rate": "+3%", "pitch": "+1Hz"},
#     "gu": {"rate": "+8%", "pitch": "+0.5Hz"},
# }

# # def _inject_english_lang_tags(text: str) -> str:
# #     """
# #     Wraps ALL English words (uppercase, lowercase, acronyms, mixed like B.Tech, MIS, HR)
# #     in <lang xml:lang="en-IN"> tags so Azure gu-IN-DhwaniNeural pronounces them
# #     correctly instead of skipping them silently.
# #     """
# #     import re

# #     # Escape any XML special chars in the text BEFORE injecting tags
# #     # (but don't escape our own injected tags)
# #     def escape_xml(s):
# #         return s.replace('&', '&amp;').replace('"', '&quot;')

# #     # Split text into Gujarati chunks and English chunks
# #     # English = any sequence containing A-Za-z (includes MIS, HR, B.Tech, v2, 10th etc.)
# #     pattern = re.compile(r'([A-Za-z][A-Za-z0-9.\-/]*)')

# #     result = []
# #     last_end = 0

# #     for match in pattern.finditer(text):
# #         start, end = match.start(), match.end()

# #         # Gujarati part before this English word — escape it
# #         gujarati_part = text[last_end:start]
# #         if gujarati_part:
# #             result.append(escape_xml(gujarati_part))

# #         # English word — wrap in lang tag
# #         english_word = match.group(1)
# #         result.append(f'<lang xml:lang="en-IN">{escape_xml(english_word)}</lang>')

# #         last_end = end

# #     # Remaining Gujarati text after last English word
# #     remaining = text[last_end:]
# #     if remaining:
# #         result.append(escape_xml(remaining))

# #     return ''.join(result)




# def _inject_english_lang_tags(text: str) -> str:
#     import re

#     def escape_xml(s):
#         return s.replace('&', '&amp;').replace('"', '&quot;')

#     def expand_if_acronym(word: str) -> str:
#         # Pure acronym: all caps only (MIS, HR, GST, TDS)
#         if re.match(r'^[A-Z][A-Z0-9]+$', word):
#             return ' '.join(word)           # "MIS" → "M I S"

#         # Complex technical codes: starts with 2+ caps, has digits/hyphens/slashes
#         # e.g. GSTR-2A → G S T R 2 A,  GSTR-2A/2B → G S T R 2 A 2 B
#         if re.match(r'^[A-Z]{2,}', word) and re.search(r'[-/0-9]', word):
#             # Strip hyphens/slashes → split alphanumeric segments → spell each out
#             parts = re.split(r'[-/]', word)      # ["GSTR", "2A"] or ["GSTR", "2A", "2B"]
#             spelled = []
#             for part in parts:
#                 if re.match(r'^[A-Z0-9]+$', part):
#                     spelled.append(' '.join(part))  # "GSTR" → "G S T R", "2A" → "2 A"
#                 else:
#                     spelled.append(part)            # mixed-case stays as-is
#             return ' '.join(spelled)               # "G S T R 2 A"

#         return word  # normal mixed-case words: B.Tech, prepare, report — untouched

#     pattern = re.compile(r'([A-Za-z][A-Za-z0-9.\-/]*)')

#     result = []
#     last_end = 0

#     for match in pattern.finditer(text):
#         start, end = match.start(), match.end()

#         gujarati_part = text[last_end:start]
#         if gujarati_part:
#             result.append(escape_xml(gujarati_part))

#         english_word = match.group(1)
#         expanded = expand_if_acronym(english_word)
#         result.append(f'<lang xml:lang="en-IN">{escape_xml(expanded)}</lang>')

#         last_end = end

#     remaining = text[last_end:]
#     if remaining:
#         result.append(escape_xml(remaining))

#     return ''.join(result)




# # def build_ssml(text: str, language: str) -> str:
# #     voice = TTS_VOICE_MAP.get(language, TTS_VOICE_MAP["en"])
# #     style = SSML_STYLE_MAP.get(language)
# #     prosody = SSML_PROSODY_MAP.get(language, SSML_PROSODY_MAP["en"])
# #     # lang_tag = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}.get(language, "en-IN")
# #     lang_tag = {"en": "en-IN"}.get(language, "en-IN")

# #     # For Gujarati: wrap English words in English lang tags before building SSML
# #     if language == "gu":
# #         text = _inject_english_lang_tags(text)
# #     else:
# #         # For non-Gujarati: just escape XML special chars
# #         text = text.replace('&', '&amp;')

# #     prosody_open = f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}">'
# #     prosody_close = '</prosody>'

# #     if style:
# #         inner = (
# #             f'<mstts:express-as style="{style}">'
# #             f'{prosody_open}{text}{prosody_close}'
# #             f'</mstts:express-as>'
# #         )
# #     else:
# #         inner = f'{prosody_open}{text}{prosody_close}'

# #     return (
# #         f'<speak version="1.0" '
# #         f'xmlns="http://www.w3.org/2001/10/synthesis" '
# #         f'xmlns:mstts="http://www.w3.org/2001/mstts" '
# #         f'xml:lang="{lang_tag}">'
# #         f'<voice name="{voice}">'
# #         f'{inner}'
# #         f'</voice>'
# #         f'</speak>'
# #     )




# def build_ssml(text: str, language: str) -> str:
#     voice = TTS_VOICE_MAP.get(language, TTS_VOICE_MAP["en"])
#     style = SSML_STYLE_MAP.get(language)
#     prosody = SSML_PROSODY_MAP.get(language, SSML_PROSODY_MAP["en"])
#     lang_tag = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}.get(language, "en-IN")
 
#     # For Gujarati: wrap English words in English lang tags before building SSML
#     if language == "gu":
#         text = _inject_english_lang_tags(text)
#     else:
#         # For non-Gujarati: just escape XML special chars
#         text = text.replace('&', '&amp;')
 
#     prosody_open = f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}">'
#     prosody_close = '</prosody>'
 
#     # if style:
#     #     inner = (
#     #         f'<mstts:express-as style="{style}">'
#     #         f'{prosody_open}{text}{prosody_close}'
#     #         f'</mstts:express-as>'
#     #     )
#     # else:
#     #     inner = f'{prosody_open}{text}{prosody_close}'
   
   
#     # if style:
#     #     inner = (
#     #         f'<mstts:express-as style="{style}" styledegree="0.8">'
#     #         f'{prosody_open}{text}{prosody_close}'
#     #         f'</mstts:express-as>'
#     #     )
#     # else:
#     #     inner = (
#     #         f'<mstts:express-as style="customerservice" styledegree="0.6">'
#     #         f'{prosody_open}{text}{prosody_close}'
#     #         f'</mstts:express-as>'
#     #     )
   
#     if language == "gu":
#         inner = f'{prosody_open}{text}{prosody_close}'
#     elif style:
#         inner = (
#             f'<mstts:express-as style="{style}" styledegree="0.8">'
#             f'{prosody_open}{text}{prosody_close}'
#             f'</mstts:express-as>'
#         )
#     else:
#         inner = (
#             f'<mstts:express-as style="customerservice" styledegree="0.6">'
#             f'{prosody_open}{text}{prosody_close}'
#             f'</mstts:express-as>'
#         )
 
#     return (
#         f'<speak version="1.0" '
#         f'xmlns="http://www.w3.org/2001/10/synthesis" '
#         f'xmlns:mstts="http://www.w3.org/2001/mstts" '
#         f'xml:lang="{lang_tag}">'
#         f'<voice name="{voice}">'
#         f'{inner}'
#         f'</voice>'
#         f'</speak>'
#     )

# # ================= CONSUMER =================

# class VoiceBotConsumer(AsyncWebsocketConsumer):

#     async def connect(self):
#         self.loop = asyncio.get_running_loop()

#         params = parse_qs(self.scope["query_string"].decode())
#         self.agent_id = params.get("agent_id", [None])[0]
#         self.user_number = params.get("from", ["unknown"])[0]
#         self.language = params.get("language", ["en"])[0]

#         if not self.agent_id:
#             await self.close()
#             return

#         self.session_id = str(uuid.uuid4())
#         self.conversation = await create_conversation(
#             self.agent_id, self.session_id, self.user_number
#         )

#         self.stream_sid = None

#         # ── STATE ──────────────────────────────────────────────
#         self.is_bot_speaking = False
#         self.is_connected = True
#         self.is_processing = False
#         self.partial_text = ""
#         self.final_text_queue = asyncio.Queue()

#         self.last_dispatched_text = ""
#         self.last_dispatch_time = 0.0

#         # ── LOCKS & TASKS ──────────────────────────────────────
#         self.processing_lock = asyncio.Lock()
#         self.tts_task = None

#         # ── AUDIO / VAD ────────────────────────────────────────
#         self.jitter_buffer = []
#         self.jitter_delay = 2

#         self.speech_active = False
#         self.silence_start_time = None

#         self.SPEECH_DETECT_RMS = 200
#         self.SILENCE_TRIGGER_SEC = 1.2
#         self.MIN_WORD_COUNT = 1

#         # Interrupt detection
#         self.interrupt_start_time = None
#         self.INTERRUPT_RMS = 300
#         self.INTERRUPT_HOLD_SEC = 0.3

#         # ── STT SETUP ──────────────────────────────────────────
#         self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
#         self._setup_stt_callbacks()
#         self.recognizer.start_continuous_recognition_async()

#         # ── TTS SYNTHESIZER (reused — avoids per-call connection overhead) ──
#         self._tts_synthesizer = self._build_tts_synthesizer()

#         await self.accept()

#         # Get TTS language FIRST so greeting is built in correct language
#         agent_tts_lang = await sync_to_async(get_agent_tts_language)(self.agent_id)
#         self.agent_tts_lang = agent_tts_lang
 
#         # Get greeting already in correct language
#         summary = await get_agent_summary(self.agent_id, agent_tts_lang)
 
#         if agent_tts_lang == "gu":
#             # Real estate — greeting already in Gujarati
#             print(f"🌐 Real estate greeting in Gujarati: {summary}")
#             asyncio.create_task(self.send_tts(summary, tts_language="gu"))
 
#         elif agent_tts_lang == "interview_en":
#             # Interview — greeting already in English
#             print(f"🌐 Interview greeting in English: {summary}")
#             asyncio.create_task(self.send_tts(summary, tts_language="en"))
 
#         else:
#             # All other bots — greeting already in Hinglish
#             print(f"🌐 Hinglish greeting: {summary}")
#             asyncio.create_task(self.send_tts(summary))
 
#         await mark_intro_shown(self.agent_id, self.session_id)
 
#         self.final_consumer_task = asyncio.create_task(self._final_text_consumer())
 
#         self.keepalive_task = asyncio.create_task(self._keepalive_loop())

#         # summary = await get_agent_summary(self.agent_id)

#         # # Get agent's required TTS language
#         # agent_tts_lang = await sync_to_async(get_agent_tts_language)(self.agent_id)

#         # if agent_tts_lang != "en":
#         #     # Interview bot — translate intro to Gujarati, play with Azure gu voice
#         #     summary = await sync_to_async(translate_text)(
#         #         summary, from_lang="en", to_lang=agent_tts_lang
#         #     )
#         #     print(f"🌐 Interview bot intro in {agent_tts_lang}: {summary}")
#         #     asyncio.create_task(self.send_tts(summary, tts_language=agent_tts_lang))
#         # else:
#         #     # All other bots
#         #     if self.language != "en":
#         #         summary = await sync_to_async(translate_text)(
#         #             summary, from_lang="en", to_lang=self.language
#         #         )
#         #     asyncio.create_task(self.send_tts(summary))

#         # await mark_intro_shown(self.agent_id, self.session_id)

#         # self.final_consumer_task = asyncio.create_task(self._final_text_consumer())

#         # self.keepalive_task = asyncio.create_task(self._keepalive_loop())

#     # ================= KEEPALIVE =================

#     async def _keepalive_loop(self):
#         while self.is_connected:
#             await asyncio.sleep(25)
#             if not self.is_connected:
#                 break
#             try:
#                 await self.send(text_data=json.dumps({"event": "ping"}))
#                 print("🏓 Keepalive ping sent")
#             except Exception as e:
#                 print(f"❌ Keepalive failed: {e}")
#                 break

#     def _setup_stt_callbacks(self):
#         def handle_recognizing(evt):
#             text = evt.result.text.strip() if evt.result.text else ""
#             self.loop.call_soon_threadsafe(self._set_partial, text)

#         def handle_recognized(evt):
#             text = evt.result.text.strip() if evt.result.text else ""
#             if text:
#                 detected_lang = evt.result.properties.get(
#                     speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
#                 )
#                 lang_code = detected_lang.split("-")[0] if detected_lang else "en"
#                 if lang_code in ["en","hi","gu"]:
#                     self.loop.call_soon_threadsafe(self._set_language, lang_code)

#                 print(f"✅ Azure FINAL [{detected_lang}]: {text}")
#                 self.loop.call_soon_threadsafe(
#                     lambda: self.final_text_queue.put_nowait(text)
#                 )

#         def handle_canceled(evt):
#             print("⚠️ STT Canceled:", evt.result.cancellation_details)

#         self.recognizer.recognizing.connect(handle_recognizing)
#         self.recognizer.recognized.connect(handle_recognized)
#         self.recognizer.canceled.connect(handle_canceled)

#     def _set_partial(self, text):
#         self.partial_text = text

#     def _set_language(self, lang_code):
#         if self.language != lang_code:
#             print(f"🌐 Language switched to: {lang_code}")
#             self.language = lang_code
#             # Rebuild synthesizer so next TTS call uses the correct voice
#             self._tts_synthesizer = self._build_tts_synthesizer()

#     async def _final_text_consumer(self):
#         while self.is_connected:
#             try:
#                 text = await asyncio.wait_for(self.final_text_queue.get(), timeout=1.0)
#             except asyncio.TimeoutError:
#                 continue
#             except Exception:
#                 break

#             if not text:
#                 continue

#             if self.is_bot_speaking or self.is_processing:
#                 print("⏭️ Skipped (bot busy):", text)
#                 continue

#             normalized = text.lower().strip()
#             if normalized == self.last_dispatched_text:
#                 print("⏭️ Duplicate skipped:", text)
#                 continue

#             if time.time() - self.last_dispatch_time < 0.5:  # ⚡ was 0.8 — faster turn-taking
#                 print("⏭️ Cooldown skip:", text)
#                 continue

#             if len(text.split()) < self.MIN_WORD_COUNT:
#                 print("⏭️ Too short:", text)
#                 continue

#             print("⚡ DISPATCHING TO AI:", text)
#             self.last_dispatched_text = normalized
#             self.last_dispatch_time = time.time()
#             self.partial_text = ""

#             self.is_processing = True
#             try:
#                 async with self.processing_lock:
#                     await self.handle_ai_reply(text)
#             finally:
#                 self.is_processing = False

#     # ================= RECEIVE =================

#     async def receive(self, text_data=None, bytes_data=None):
#         if not text_data:
#             return

#         try:
#             data = json.loads(text_data)

#             if data.get("event") == "start":
#                 self.stream_sid = data["start"].get("streamSid")
#                 print(f"📡 streamSid captured: {self.stream_sid}")
#                 try:
#                     number = data["start"]["customParameters"]["callerNumber"]
#                     self.user_number = number
#                     await update_user_number(self.conversation, number)
#                 except Exception:
#                     pass

#             if data.get("event") == "media":
#                 await self._handle_audio_chunk(data)

#         except Exception as e:
#             print("❌ RECEIVE ERROR:", e)

#     async def _handle_audio_chunk(self, data):
#         payload = base64.b64decode(data["media"]["payload"])
#         pcm = decode_g711(payload)

#         # Dynamic gain — boosts quiet/soft/slow voices automatically
#         pcm_np = np.frombuffer(pcm, dtype=np.int16).copy()
#         current_rms = audioop.rms(pcm, 2)
#         if current_rms > 50:
#             gain = min(1200 / current_rms, 6.0)
#             pcm_np = np.clip(pcm_np * gain, -32768, 32767).astype(np.int16)
#         pcm = pcm_np.tobytes()

#         if len(pcm) % 2 != 0:
#             pcm = pcm[:-1]

#         # Jitter buffer
#         self.jitter_buffer.append(pcm)
#         if len(self.jitter_buffer) < self.jitter_delay:
#             return

#         pcm = self.jitter_buffer.pop(0)
#         rms = audioop.rms(pcm, 2)

#         # Drop truly corrupt packets only
#         pcm_check = np.frombuffer(pcm, dtype=np.int16)
#         if int(np.abs(pcm_check).max()) == 32767 and rms > 28000:
#             return

#         # ── INTERRUPT DETECTION ────────────────────────────────
#         if self.is_bot_speaking:
#             return  # Do NOT feed audio to Azure STT while bot is speaking

#         # Feed to Azure STT only when bot is silent
#         self.push_stream.write(pcm)

#         # ── AGGRESSIVE PARTIAL-TEXT DISPATCH ───────────────────
#         if rms > self.SPEECH_DETECT_RMS:
#             self.speech_active = True
#             self.silence_start_time = None
#         else:
#             if self.speech_active:
#                 if self.silence_start_time is None:
#                     self.silence_start_time = time.time()
#                 elif time.time() - self.silence_start_time > self.SILENCE_TRIGGER_SEC:
#                     self.speech_active = False
#                     self.silence_start_time = None

#                     if (
#                         not self.is_bot_speaking
#                         and not self.is_processing
#                         and self.partial_text
#                     ):
#                         fallback_text = self.partial_text.strip()
#                         self.partial_text = ""

#                         if len(fallback_text.split()) >= self.MIN_WORD_COUNT:
#                             normalized = fallback_text.lower()
#                             if normalized != self.last_dispatched_text:
#                                 if time.time() - self.last_dispatch_time >= 0.5:
#                                     print("⚡ FAST DISPATCH (partial VAD):", fallback_text)
#                                     self.last_dispatched_text = normalized
#                                     self.last_dispatch_time = time.time()
#                                     self.is_processing = True
#                                     try:
#                                         async with self.processing_lock:
#                                             await self.handle_ai_reply(fallback_text)
#                                     finally:
#                                         self.is_processing = False

#     async def _check_interrupt(self, rms):
#         """Detect user barge-in while bot is speaking."""
#         if rms < self.INTERRUPT_RMS:
#             self.interrupt_start_time = None
#             return

#         if self.interrupt_start_time is None:
#             self.interrupt_start_time = time.time()
#             return

#         if time.time() - self.interrupt_start_time < self.INTERRUPT_HOLD_SEC:
#             return

#         print("🛑 INTERRUPT DETECTED — stopping bot, capturing user speech")

#         interrupted_partial = self.partial_text.strip()
#         interrupt_time = time.time()

#         self.is_bot_speaking = False
#         self.interrupt_start_time = None

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         await self._send_clear_event()

#         self.jitter_buffer.clear()

#         asyncio.create_task(
#             self._interruption_fallback(interrupted_partial, interrupt_time)
#         )

#     # ================= INTERRUPT HELPERS =================

#     async def _send_clear_event(self):
#         if self.stream_sid:
#             try:
#                 await self.send(text_data=json.dumps({
#                     "event": "clear",
#                     "streamSid": self.stream_sid
#                 }))
#                 print("📢 Twilio audio buffer cleared")
#             except Exception as e:
#                 print(f"❌ Clear event failed: {e}")

#     async def _interruption_fallback(self, partial_text, interrupt_time):
#         await asyncio.sleep(1.5)

#         if self.last_dispatch_time > interrupt_time:
#             print("✅ Interrupt speech already dispatched via normal path")
#             return

#         if self.is_bot_speaking or self.is_processing:
#             print("⏭️ Interrupt fallback skipped (pipeline busy)")
#             return

#         final_text = None
#         try:
#             final_text = self.final_text_queue.get_nowait()
#         except asyncio.QueueEmpty:
#             pass

#         text = final_text or self.partial_text.strip() or partial_text
#         self.partial_text = ""

#         if not text or len(text.split()) < self.MIN_WORD_COUNT:
#             print("⏭️ Interrupt text too short:", text)
#             return

#         normalized = text.lower().strip()
#         if normalized == self.last_dispatched_text:
#             print("⏭️ Interrupt duplicate skipped:", text)
#             return

#         print("⚡ INTERRUPT FALLBACK DISPATCH:", text)
#         self.last_dispatched_text = normalized
#         self.last_dispatch_time = time.time()

#         self.is_processing = True
#         try:
#             async with self.processing_lock:
#                 await self.handle_ai_reply(text)
#         finally:
#             self.is_processing = False

#     # ================= STREAMING LLM BRIDGE =================

#     async def _stream_llm(self, system_prompt, user_message):
#         queue = asyncio.Queue()
#         loop = asyncio.get_event_loop()

#         def _run_streaming():
#             try:
#                 for chunk in generate_response_streaming(system_prompt, user_message):
#                     loop.call_soon_threadsafe(queue.put_nowait, chunk)
#             except Exception as e:
#                 print(f"❌ LLM Streaming error: {e}")
#             loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

#         loop.run_in_executor(None, _run_streaming)

#         while True:
#             chunk = await queue.get()
#             if chunk is None:
#                 break
#             yield chunk

#     # ================= AI (STREAMING) =================

#     async def handle_ai_reply(self, text):
#         """
#         STREAMING PIPELINE — streams LLM tokens, synthesizes per sentence, plays audio.
#         Respects tts_language and skip_output_translation flags from strategy prep_result.
#         """
#         pipeline_start = time.time()
#         text = text.strip()
#         if not text:
#             return

#         normalized = text.lower().strip()

#         # ── END INTENT ────────────────────────────────────────
#         if is_end_intent(normalized):
#             print("📴 END INTENT DETECTED:", text)
 
#             await save_message(self.conversation, "user", text)
 
#             if self.agent_tts_lang == "gu":
#                 # Real estate — goodbye directly in Gujarati, no translation
#                 farewell = "આપનો ખૂબ ખૂબ આભાર! જ્યારે પણ મિલકત વિશે કોઈ પ્રશ્ન હોય, અમે હંમેશા ઉપલબ્ધ છીએ. ધ્યાન રાખજો!"
 
#             elif self.agent_tts_lang == "interview_en":
#                 # Interview — English goodbye
#                 farewell = "Thank you for your time. All the best for your preparation!"
 
#             else:
#                 # All other bots — Hinglish goodbye
#                 farewell = "Thank you for calling! Koi aur help chahiye toh zaroor call karna. Take care!"
 
#             await save_message(self.conversation, "bot", farewell)
 
#             if self.tts_task and not self.tts_task.done():
#                 self.tts_task.cancel()
#                 try:
#                     await self.tts_task
#                 except asyncio.CancelledError:
#                     pass
 
#             tts_lang_for_farewell = "gu" if self.agent_tts_lang == "gu" else "en"
#             await self.send_tts(farewell, tts_language=tts_lang_for_farewell)
#             await close_conversation(self.conversation)
 
#             await self.send(text_data=json.dumps({"event": "stop"}))
 
#             self.is_connected = False
#             await self.close()
#             return

#         # ── MAIN STREAMING PIPELINE ───────────────────────────
#         # ── MAIN STREAMING PIPELINE ───────────────────────────
#         print("🧠 AI INPUT:", text)

#         # ⚡ Run save_message + prepare_streaming concurrently (saves ~50-100ms)
#         t_prep = time.time()
#         _, prep_result = await asyncio.gather(
#             save_message(self.conversation, "user", text),
#             sync_to_async(prepare_streaming)(self.agent_id, text, self.session_id)
#         )
#         prep_ms = round((time.time() - t_prep) * 1000)

#         # Read language control flags
#         tts_language = prep_result.get("tts_language", self.language)
#         skip_output_translation = prep_result.get("skip_output_translation", False)
#         skip_input_translation = prep_result.get("skip_input_translation", False)

#         # Step 2: Translate input
#         t_translate_in = time.time()
#         message_for_ai = text
#         translate_input_to = prep_result.get("translate_input_to", None)  # None = normal bot

#         if translate_input_to == "gu":
#             # Interview bot only — translate to Gujarati
#             if self.language != "gu":
#                 message_for_ai = await sync_to_async(translate_text)(
#                     text, from_lang=self.language, to_lang="gu"
#                 )
#                 print(f"🌐 [{self.language}→gu]: {message_for_ai}")

#         elif translate_input_to is None and self.language != "en":
#             # Normal bots — translate to English as original behaviour
#             message_for_ai = await sync_to_async(translate_text)(
#                 text, from_lang=self.language, to_lang="en"
#             )
#             print(f"🌐 [{self.language}→en]: {message_for_ai}")

#         translate_in_ms = round((time.time() - t_translate_in) * 1000)

#         # Step 3a: Static reply — no LLM streaming needed
#         if "static_reply" in prep_result:
#             reply = prep_result["static_reply"]
#             if not reply:
#                 return

#             reply_for_user = reply
#             # Skip translation if strategy has already produced the correct output language
#             if not skip_output_translation and self.language != "en":
#                 reply_for_user = await sync_to_async(translate_text)(
#                     reply, from_lang="en", to_lang=self.language
#                 )

#             total_ms = round((time.time() - pipeline_start) * 1000)
#             print(f"⏱ PIPELINE (static): prep={prep_ms}ms | TOTAL={total_ms}ms")

#             await save_message(self.conversation, "bot", reply_for_user)
#             print("🤖 BOT REPLY:", reply_for_user)

#             if self.tts_task and not self.tts_task.done():
#                 self.tts_task.cancel()
#                 try:
#                     await self.tts_task
#                 except asyncio.CancelledError:
#                     pass

#             # Use tts_language for synthesis (may differ from self.language)
#             self.tts_task = asyncio.create_task(
#                 self.send_tts(reply_for_user, tts_language=tts_language)
#             )

#             # ⚡ AUTO-DISCONNECT for static replies (user confirmed booking)
#             if prep_result.get("auto_disconnect"):
#                 print("📴 AUTO-DISCONNECT (static reply): Booking confirmed by user — ending call")
#                 await self.tts_task  # Wait for farewell TTS to finish playing
#                 await close_conversation(self.conversation)
#                 await self.send(text_data=json.dumps({"event": "stop"}))
#                 self.is_connected = False
#                 await self.close()

#             return

#         # Step 3b: STREAMING LLM + PER-SENTENCE TTS
#         system_prompt = prep_result["system_prompt"]
#         user_message = prep_result["user_message"]

#         if not skip_input_translation and message_for_ai != text:
#             user_message = message_for_ai

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         self.is_bot_speaking = True
#         t_llm = time.time()

#         audio_queue = asyncio.Queue()
#         full_response = ""
#         first_sentence_time = None

#         # Helper to strip auto-disconnect tags from assembled sentences before TTS
#         def _strip_disconnect_tags(text):
#             for t in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]",
#                       "BOOKING_CONFIRMED", "NOT_INTERESTED", "LEAD_COMPLETE"]:
#                 text = text.replace(t, "")
#             return text.replace("[", "").replace("]", "").strip()

#         async def streaming_producer():
#             nonlocal full_response, first_sentence_time
#             sentence_buffer = ""
#             loop = asyncio.get_event_loop()

#             async for chunk in self._stream_llm(system_prompt, user_message):
#                 if not self.is_bot_speaking:
#                     break
#                 full_response += chunk
#                 # ⚡ Strip auto-disconnect tags so TTS never speaks them
#                 clean_chunk = chunk
#                 for _tag in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]"]:
#                     clean_chunk = clean_chunk.replace(_tag, "")
#                 # Also strip inner tag text (tags arrive split across chunks)
#                 for _inner in ["BOOKING_CONFIRMED", "NOT_INTERESTED", "LEAD_COMPLETE"]:
#                     clean_chunk = clean_chunk.replace(_inner, "")
#                 clean_chunk = clean_chunk.replace("[", "").replace("]", "")
#                 sentence_buffer += clean_chunk

#                 # ⚡ Split on commas/semicolons too for faster first-audio
#                 # boundary = re.search(r'[.!?।]\s|[,;]\s+(?=\S)', sentence_buffer)
#                 if tts_language == "gu":
#                     boundary = re.search(r'[!?।]\s|[.]\s+(?=[A-Z\u0A80-\u0AFF])', sentence_buffer)
#                 else:
#                     boundary = re.search(r'[.!?।]\s|[,;]\s+(?=\S)', sentence_buffer)
#                 if boundary:
#                     sentence = sentence_buffer[:boundary.start() + 1].strip()
#                     sentence_buffer = sentence_buffer[boundary.end():]
#                     if sentence:
#                         if first_sentence_time is None:
#                             first_sentence_time = time.time()
#                             print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

#                         sentence = _strip_disconnect_tags(sentence)
#                         if not sentence:
#                             continue
#                         tts_text = sentence
#                         # Only translate if strategy hasn't taken ownership of output language
#                         if not skip_output_translation and self.language != "en":
#                             tts_text = await sync_to_async(translate_text)(
#                                 sentence, from_lang="en", to_lang=self.language
#                             )

#                         try:
#                             ulaw = await asyncio.wait_for(
#                                 loop.run_in_executor(
#                                     None,
#                                     lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
#                                 ),
#                                 timeout=15
#                             )
#                             await audio_queue.put(ulaw)
#                         except asyncio.TimeoutError:
#                             print(f"❌ TTS timeout: {sentence[:40]}")

#             # Handle remaining text after stream ends
#             if sentence_buffer.strip() and self.is_bot_speaking:
#                 sentence = sentence_buffer.strip()
#                 if first_sentence_time is None:
#                     first_sentence_time = time.time()
#                     print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

#                 sentence = _strip_disconnect_tags(sentence)
#                 if not sentence:
#                     await audio_queue.put(None)
#                     return
#                 tts_text = sentence
#                 # Only translate if strategy hasn't taken ownership of output language
#                 if not skip_output_translation and self.language != "en":
#                     tts_text = await sync_to_async(translate_text)(
#                         sentence, from_lang="en", to_lang=self.language
#                     )
#                 try:
#                     ulaw = await asyncio.wait_for(
#                         loop.run_in_executor(
#                             None,
#                             lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
#                         ),
#                         timeout=15
#                     )
#                     await audio_queue.put(ulaw)
#                 except asyncio.TimeoutError:
#                     pass

#             await audio_queue.put(None)

#         async def streaming_consumer():
#             """Streams audio to Twilio as soon as each sentence's TTS is ready."""
#             while True:
#                 ulaw = await audio_queue.get()
#                 if ulaw is None:
#                     break
#                 if not self.is_bot_speaking:
#                     break
#                 await self._stream_ulaw(ulaw)

#         producer_task = asyncio.create_task(streaming_producer())
#         consumer_task = asyncio.create_task(streaming_consumer())
#         self.tts_task = consumer_task

#         try:
#             await asyncio.gather(producer_task, consumer_task)
#         except asyncio.CancelledError:
#             print("🛑 STREAMING TTS CANCELLED")
#         except Exception as e:
#             print("❌ STREAMING ERROR:", e)
#         finally:
#             self.is_bot_speaking = False

#         llm_ms = round((time.time() - t_llm) * 1000)
#         total_ms = round((time.time() - pipeline_start) * 1000)
#         print(f"⏱ STREAMING PIPELINE: translate_in={translate_in_ms}ms | prep={prep_ms}ms | LLM+TTS={llm_ms}ms | TOTAL={total_ms}ms")

#         # ⚡ Finalize FIRST (needs to see [BOOKING_CONFIRMED] tag if present)
#         if full_response:
#             await sync_to_async(finalize_streaming)(full_response, prep_result)

#         # Strip auto-disconnect tags before saving (user should never see them)
#         for _tag in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]"]:
#             full_response = full_response.replace(_tag, "")
#         full_response = full_response.strip()

#         # Save the full bot reply
#         reply_for_user = full_response
#         if not skip_output_translation and self.language != "en" and full_response:
#             reply_for_user = await sync_to_async(translate_text)(
#                 full_response, from_lang="en", to_lang=self.language
#             )
#         if reply_for_user:
#             await save_message(self.conversation, "bot", reply_for_user)
#         print("🤖 BOT REPLY:", reply_for_user)

#         # ⚡ AUTO-DISCONNECT: Triggered by [BOOKING_CONFIRMED], [NOT_INTERESTED], or [LEAD_COMPLETE]
#         if prep_result.get("auto_disconnect"):
#             # Insurance: disconnect immediately (no name collection needed)
#             if prep_result.get("skip_name_collection"):
#                 print("📴 AUTO-DISCONNECT (insurance): Ending call immediately")
#                 await asyncio.sleep(1.5)  # Wait for last TTS to finish
#                 await close_conversation(self.conversation)
#                 await self.send(text_data=json.dumps({"event": "stop"}))
#                 self.is_connected = False
#                 await self.close()
#                 return

#             # Education/Realestate: LLM asked for name, wait for user response
#             print("📴 BOOKING CONFIRMED — LLM asked for name, waiting for user response")
#             state = prep_result.get("state", {})
#             session_obj = prep_result.get("session")
#             if state is not None and session_obj:
#                 state["name_collection_pending"] = True
#                 from conversations.services.core.strategies import save_session
#                 await sync_to_async(save_session)(session_obj, state)
#             return

#     # ================= TTS HELPERS =================

#     def _build_tts_synthesizer(self, language: str = None):
#         """
#         Build and return a reusable SpeechSynthesizer.
#         language param allows building for a specific language (e.g. "gu" for interview bot).
#         Defaults to self.language if not specified.
#         """
#         lang = language or self.language
#         speech_config = speechsdk.SpeechConfig(
#             subscription=os.getenv("AZURE_SPEECH_KEY"),
#             region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
#         )
#         speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
#         speech_config.set_speech_synthesis_output_format(
#             speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#         )
#         return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)


#     def _synthesize_ulaw(self, text: str, language: str = None) -> bytes:
#         lang = language or self.language
#         # ── All languages (en / hi / gu) → Azure ─────────────
#         ssml = build_ssml(text, lang)

#         if lang != self.language:
#             speech_config = speechsdk.SpeechConfig(
#                 subscription=os.getenv("AZURE_SPEECH_KEY"),
#                 region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
#             )
#             speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
#             speech_config.set_speech_synthesis_output_format(
#                 speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#             )
#             synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
#             result = synthesizer.speak_ssml_async(ssml).get()
#         else:
#             result = self._tts_synthesizer.speak_ssml_async(ssml).get()

#         if result.reason == speechsdk.ResultReason.Canceled:
#             details = result.cancellation_details
#             print("❌ TTS Canceled:", details.reason, details.error_details)
#             return b""

#         pcm = result.audio_data
#         pcm = strip_wav_header(pcm)

#         if len(pcm) % 2 != 0:
#             pcm = pcm[:-1]

#         return encode_g711(pcm)

#     async def _stream_ulaw(self, ulaw: bytes):
#         """
#         Stream u-law audio frames to Twilio with clock-anchored timing.
#         Silence padding prevents clipping at start/end of each segment.
#         """
#         if not ulaw:
#             return

#         loop = asyncio.get_event_loop()

#         # 3 silence frames before audio (~60ms) to prevent leading clip
#         for _ in range(2):
#             if not self.is_bot_speaking:
#                 return
#             await self._send_media_frame(SILENCE_FRAME)
#             await asyncio.sleep(0.020)

#         # Main audio — clock-anchored so timing never drifts
#         start_time = loop.time()
#         for idx, i in enumerate(range(0, len(ulaw), 160)):
#             if not self.is_bot_speaking:
#                 print("🛑 TTS stopped mid-stream")
#                 return

#             chunk = ulaw[i:i + 160].ljust(160, b'\x7f')
#             await self._send_media_frame(chunk)

#             target_time = start_time + (idx + 1) * 0.020
#             sleep_duration = target_time - loop.time()
#             if sleep_duration > 0:
#                 await asyncio.sleep(sleep_duration)

#         # 3 silence frames after audio (~60ms) to prevent trailing click/pop
#         for _ in range(2):
#             if not self.is_bot_speaking:
#                 return
#             await self._send_media_frame(SILENCE_FRAME)
#             await asyncio.sleep(0.020)

#     async def _send_media_frame(self, chunk: bytes):
#         """Centralised send helper that always includes streamSid."""
#         payload = base64.b64encode(chunk).decode()
#         msg = {
#             "event": "media",
#             "media": {"payload": payload}
#         }
#         if self.stream_sid:
#             msg["streamSid"] = self.stream_sid
#         await self.send(text_data=json.dumps(msg))

#     # ================= TTS (kept for static replies / intro) =================

#     async def send_tts(self, text, tts_language: str = None):
#         """
#         Synthesize and stream a full text reply.
#         tts_language overrides self.language for synthesis — used by interview bot
#         to force Gujarati voice on static replies and intro.
#         """
#         self.is_bot_speaking = True
#         loop = asyncio.get_event_loop()
#         lang = tts_language or self.language

#         try:
#             sentences = split_into_sentences(text)
#             audio_queue = asyncio.Queue()

#             async def producer():
#                 for sentence in sentences:
#                     if not self.is_bot_speaking:
#                         break
#                     try:
#                         ulaw = await asyncio.wait_for(
#                             loop.run_in_executor(
#                                 None,
#                                 lambda s=sentence, l=lang: self._synthesize_ulaw(s, l)
#                             ),
#                             timeout=15
#                         )
#                     except asyncio.TimeoutError:
#                         print(f"❌ TTS TIMEOUT for sentence: {sentence[:40]}")
#                         ulaw = b""
#                     await audio_queue.put(ulaw)
#                 await audio_queue.put(None)

#             async def consumer():
#                 while True:
#                     ulaw = await audio_queue.get()
#                     if ulaw is None:
#                         break
#                     if not self.is_bot_speaking:
#                         break
#                     await self._stream_ulaw(ulaw)

#             producer_task = asyncio.create_task(producer())
#             consumer_task = asyncio.create_task(consumer())

#             await asyncio.gather(producer_task, consumer_task)

#         except asyncio.CancelledError:
#             print("🛑 TTS CANCELLED")
#             raise

#         except Exception as e:
#             print("❌ TTS ERROR:", e)

#         finally:
#             self.is_bot_speaking = False

#     # ================= DISCONNECT =================

#     async def disconnect(self, close_code):
#         print("🔌 DISCONNECTED:", close_code)
#         self.is_connected = False

#         if hasattr(self, "keepalive_task"):
#             self.keepalive_task.cancel()
#             try:
#                 await self.keepalive_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "final_consumer_task"):
#             self.final_consumer_task.cancel()
#             try:
#                 await self.final_consumer_task
#             except asyncio.CancelledError:
#                 pass

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "recognizer"):
#             try:
#                 self.recognizer.stop_continuous_recognition_async()
#             except Exception:
#                 pass

#         if hasattr(self, "push_stream"):
#             try:
#                 self.push_stream.close()
#             except Exception:
#                 pass

#         if hasattr(self, "conversation"):
#             await close_conversation(self.conversation)

#             # ⚡ Post-call lead analysis — run in background thread
#             conv_id = self.conversation.id
#             import threading
#             def _run_lead_analysis():
#                 try:
#                     from conversations.services.lead_analyzer import analyze_lead
#                     analyze_lead(conv_id)
#                 except Exception as e:
#                     print(f"❌ Lead analysis background error: {e}")
#             threading.Thread(target=_run_lead_analysis, daemon=True).start()
#             print("📊 Lead analysis started in background...")





















# # # new code (where double speech is prevented).


# from urllib.parse import parse_qs
# import audioop
# from asgiref.sync import sync_to_async
# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from conversations.services.core.dialogue_engine import process_message, prepare_streaming, finalize_streaming, get_agent_tts_language
# from conversations.services.azure_openai_service import generate_response_streaming
# from conversations.services.speech_service import create_speech_recognizer
# from conversations.services.translator_service import translate_text
# import asyncio
# import os
# import azure.cognitiveservices.speech as speechsdk
# import time
# import base64
# import uuid
# import numpy as np
# import re
# from django.utils import timezone

# from agents.models import VoiceAgent
# from conversations.models import Conversation, Message, LeadAnalysis


# # ================= DATABASE =================

# @sync_to_async
# def create_conversation(agent_id, session_id, user_number):
#     conv = Conversation.objects.create(
#         agent_id=agent_id,
#         session_id=session_id,
#         user_number=user_number
#     )
#     # Create immediate LeadAnalysis record so it shows on dashboard instantly
#     LeadAnalysis.objects.create(
#         conversation=conv,
#         agent_id=agent_id,
#         lead_level="cold",  # Default level for new/short calls
#         summary="Call started..."
#     )
#     return conv


# @sync_to_async
# def save_message(conversation, role, text):
#     last = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
#     if last and last.text.strip() == text.strip() and last.role == role:
#         return
#     Message.objects.create(conversation=conversation, role=role, text=text)


# @sync_to_async
# def update_user_number(conversation, number):
#     conversation.user_number = number
#     conversation.save()


# @sync_to_async
# def save_stream_sid(conversation, stream_sid):
#     """Save the telecom's streamSid to the conversation for CDR matching."""
#     conversation.stream_sid = stream_sid
#     conversation.save(update_fields=["stream_sid"])


# @sync_to_async
# def close_conversation(conversation):
#     conversation.ended_at = timezone.now()
#     conversation.save()


# @sync_to_async
# def get_agent_summary(agent_id, agent_tts_lang="en"):
#     try:
#         agent = VoiceAgent.objects.get(id=agent_id)
#         company = agent.company_name or "our company"
#         summary = agent.summary.strip().rstrip(".") if agent.summary else ""

#         if agent_tts_lang == "gu":
#             if summary:
#                 return f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. {summary}"
#             return f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. મિલકત ખરીદવી, વેચવી, ભાડે આપવી કે રોકાણ — કોઈ પણ બાબતમાં મદદ જોઈએ તો કહો!"

#         elif agent_tts_lang == "interview_en":
#             if summary:
#                 return f"Hello, I am {agent.name} from {company}. {summary}."
#             return f"Hello, I am {agent.name}."

#         else:
#             if summary:
#                 return f"Hello, main {agent.name} hoon, {company} se. {summary}."
#             return f"Hello, main {agent.name} hoon, {company} se."

#     except VoiceAgent.DoesNotExist:
#         return "Hello, how can I assist you today?"


# @sync_to_async
# def mark_intro_shown(agent_id, session_id):
#     from conversations.models import ConversationSession
#     from agents.models import VoiceAgent
#     try:
#         agent = VoiceAgent.objects.get(id=agent_id)
#         session, _ = ConversationSession.objects.get_or_create(
#             agent=agent,
#             session_id=session_id
#         )
#         state = session.state or {}
#         state["intro_shown"] = True
#         session.state = state
#         session.save()
#     except Exception as e:
#         print("❌ mark_intro_shown error:", e)


# # ================= AUDIO =================

# def decode_g711(ulaw):
#     return audioop.ulaw2lin(ulaw, 2)


# def encode_g711(pcm):
#     return audioop.lin2ulaw(pcm, 2)


# def strip_wav_header(data: bytes) -> bytes:
#     if data[:4] != b'RIFF':
#         return data
#     offset = 12
#     while offset < len(data) - 8:
#         chunk_id = data[offset:offset + 4]
#         chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
#         if chunk_id == b'data':
#             return data[offset + 8:]
#         offset += 8 + chunk_size
#     return data[44:]


# SILENCE_FRAME = b'\x7f' * 160


# def split_into_sentences(text: str) -> list:
#     sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', text) if s.strip()]
#     return sentences if sentences else [text]


# def is_end_intent(text: str) -> bool:
#     text = text.lower().strip()
#     end_keywords = [
#         "bye", "goodbye", "ok bye", "okay bye",
#         "thank you", "thanks a lot",
#         "that's all", "no thanks", "call end",
#         "અلविदा",
#         "બાય", "આભાર"
#     ]
#     return any(keyword in text for keyword in end_keywords)


# def _normalize(text: str) -> str:
#     """Normalize text for deduplication: lowercase, strip punctuation/spaces."""
#     return re.sub(r'[^\w\s]', '', text.lower()).strip()


# def _is_duplicate_utterance(text_a: str, text_b: str) -> bool:
#     """
#     Returns True if two utterances are effectively the same.
#     Handles cases where Azure final adds punctuation/casing vs raw partial.
#     Also catches substring cases: partial 'haan bhai' vs final 'haan bhai karo'.
#     """
#     a = _normalize(text_a)
#     b = _normalize(text_b)
#     if not a or not b:
#         return False
#     # Exact match
#     if a == b:
#         return True
#     # One is a prefix/suffix of the other (partial vs final)
#     shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
#     if longer.startswith(shorter) or longer.endswith(shorter):
#         return True
#     # Word overlap > 80%
#     words_a = set(a.split())
#     words_b = set(b.split())
#     if not words_a or not words_b:
#         return False
#     overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
#     return overlap >= 0.8


# # ================= SSML BUILDER =================

# TTS_VOICE_MAP = {
#     "en": "en-IN-AnanyaNeural",
#     "hi": "hi-IN-AnanyaNeural",
#     "gu": "gu-IN-DhwaniNeural",
# }

# SSML_STYLE_MAP = {
#     "en": None,
#     "hi": None,
#     "gu": None,
# }

# SSML_PROSODY_MAP = {
#     "en": {"rate": "+5%", "pitch": "+2Hz", "volume": "0%"},
#     "hi": {"rate": "+3%", "pitch": "+1Hz", "volume": "0%"},
#     "gu": {"rate": "+25%", "pitch": "-2Hz", "volume": "+20%"},
# }   


# def _inject_english_lang_tags(text: str) -> str:
#     import re

#     def escape_xml(s):
#         return s.replace('&', '&amp;').replace('"', '&quot;')

#     def expand_if_acronym(word: str) -> str:
#         if re.match(r'^[A-Z][A-Z0-9]+$', word):
#             return ' '.join(word)
#         if re.match(r'^[A-Z]{2,}', word) and re.search(r'[-/0-9]', word):
#             parts = re.split(r'[-/]', word)
#             spelled = []
#             for part in parts:
#                 if re.match(r'^[A-Z0-9]+$', part):
#                     spelled.append(' '.join(part))
#                 else:
#                     spelled.append(part)
#             return ' '.join(spelled)
#         return word

#     pattern = re.compile(r'([A-Za-z][A-Za-z0-9.\-/]*)')
#     result = []
#     last_end = 0

#     for match in pattern.finditer(text):
#         start, end = match.start(), match.end()
#         gujarati_part = text[last_end:start]
#         if gujarati_part:
#             result.append(escape_xml(gujarati_part))
#         english_word = match.group(1)
#         expanded = expand_if_acronym(english_word)
#         result.append(f'<lang xml:lang="en-IN">{escape_xml(expanded)}</lang>')
#         last_end = end

#     remaining = text[last_end:]
#     if remaining:
#         result.append(escape_xml(remaining))

#     return ''.join(result)


# def build_ssml(text: str, language: str) -> str:
#     voice = TTS_VOICE_MAP.get(language, TTS_VOICE_MAP["en"])
#     style = SSML_STYLE_MAP.get(language)
#     prosody = SSML_PROSODY_MAP.get(language, SSML_PROSODY_MAP["en"])
#     lang_tag = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}.get(language, "en-IN")

#     if language == "gu":
#         text = _inject_english_lang_tags(text)
#     else:
#         text = text.replace('&', '&amp;')

#     prosody_open = f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}" volume="{prosody.get("volume", "0%")}">'
#     prosody_close = '</prosody>'

#     if language == "gu":
#         inner = f'{prosody_open}{text}{prosody_close}'
#     elif style:
#         inner = (
#             f'<mstts:express-as style="{style}" styledegree="0.8">'
#             f'{prosody_open}{text}{prosody_close}'
#             f'</mstts:express-as>'
#         )
#     else:
#         inner = (
#             f'<mstts:express-as style="customerservice" styledegree="0.6">'
#             f'{prosody_open}{text}{prosody_close}'
#             f'</mstts:express-as>'
#         )

#     return (
#         f'<speak version="1.0" '
#         f'xmlns="http://www.w3.org/2001/10/synthesis" '
#         f'xmlns:mstts="http://www.w3.org/2001/mstts" '
#         f'xml:lang="{lang_tag}">'
#         f'<voice name="{voice}">'
#         f'{inner}'
#         f'</voice>'
#         f'</speak>'
#     )


# # ================= CONSUMER =================

# class VoiceBotConsumer(AsyncWebsocketConsumer):

#     async def connect(self):
#         self.loop = asyncio.get_running_loop()

#         params = parse_qs(self.scope["query_string"].decode())
#         self.agent_id = params.get("agent_id", [None])[0]
#         # Prioritize 'phone' param (outbound auto-dialer) over 'from' header
#         self.user_number = params.get("phone", [None])[0] or params.get("from", ["unknown"])[0]
#         self.language = params.get("language", ["en"])[0]

#         if not self.agent_id:
#             await self.close()
#             return

#         self.session_id = str(uuid.uuid4())
#         self.conversation = await create_conversation(
#             self.agent_id, self.session_id, self.user_number
#         )

#         self.stream_sid = None

#         # ── STATE ──────────────────────────────────────────────
#         self.is_bot_speaking = False
#         self.is_connected = True
#         self.is_processing = False
#         self.partial_text = ""
#         self.final_text_queue = asyncio.Queue()

#         self.last_dispatched_text = ""
#         self.last_dispatch_time = 0.0

#         # ── BOT SPEECH TIMING ──────────────────────────────────
#         # Timestamps for when bot speech started and ended.
#         # Any Azure STT result recognised DURING bot speech is discarded —
#         # it means the user spoke over the bot and we don't want to process it.
#         self._bot_speaking_started_at = 0.0   # set every time is_bot_speaking → True
#         self._bot_speaking_ended_at = 0.0     # set every time is_bot_speaking → False
#         # Grace period (seconds) after bot stops speaking during which STT results
#         # are still treated as "spoken during bot turn" and discarded.
#         self._post_speech_grace = 0.8

#         # ── DUPLICATE PREVENTION ───────────────────────────────
#         # Tracks whether VAD partial-dispatch already fired for current utterance.
#         # When Azure final arrives, it checks this to avoid double-processing.
#         self._vad_dispatched_text = ""       # normalized text that VAD already sent to AI
#         self._vad_dispatched_time = 0.0      # when VAD dispatched it
#         self._azure_final_received_time = 0.0  # when Azure last fired recognized

#         # ── LOCKS & TASKS ──────────────────────────────────────
#         self.processing_lock = asyncio.Lock()
#         self.tts_task = None
#         self._tts_synthesizers = {}  # Cache synthesizers by language code

#         # ── AUDIO / VAD ────────────────────────────────────────
#         self.jitter_buffer = []
#         self.jitter_delay = 2

#         self.speech_active = False
#         self.silence_start_time = None

#         self.SPEECH_DETECT_RMS = 200
#         self.SILENCE_TRIGGER_SEC = 1.2
#         self.MIN_WORD_COUNT = 1

#         # Interrupt detection
#         self.interrupt_start_time = None
#         self.INTERRUPT_RMS = 300
#         self.INTERRUPT_HOLD_SEC = 0.3

#         # ── STT SETUP ──────────────────────────────────────────
#         self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
#         self._setup_stt_callbacks()
#         self.recognizer.start_continuous_recognition_async()

#         # ── TTS SYNTHESIZER ───────────────────────────────────
#         self._tts_synthesizer = self._build_tts_synthesizer()

#         await self.accept()

#         agent_tts_lang = await sync_to_async(get_agent_tts_language)(self.agent_id)
#         self.agent_tts_lang = agent_tts_lang

#         summary = await get_agent_summary(self.agent_id, agent_tts_lang)

#         if agent_tts_lang == "gu":
#             print(f"🌐 Real estate greeting in Gujarati: {summary}")
#             asyncio.create_task(self.send_tts(summary, tts_language="gu"))
#         elif agent_tts_lang == "interview_en":
#             print(f"🌐 Interview greeting in English: {summary}")
#             asyncio.create_task(self.send_tts(summary, tts_language="en"))
#         else:
#             print(f"🌐 Hinglish greeting: {summary}")
#             asyncio.create_task(self.send_tts(summary))

#         await mark_intro_shown(self.agent_id, self.session_id)

#         self.final_consumer_task = asyncio.create_task(self._final_text_consumer())
#         self.keepalive_task = asyncio.create_task(self._keepalive_loop())

#     # ================= KEEPALIVE =================

#     async def _keepalive_loop(self):
#         while self.is_connected:
#             await asyncio.sleep(25)
#             if not self.is_connected:
#                 break
#             try:
#                 await self.send(text_data=json.dumps({"event": "ping"}))
#                 print("🏓 Keepalive ping sent")
#             except Exception as e:
#                 print(f"❌ Keepalive failed: {e}")
#                 break

#     # ================= STT CALLBACKS =================

#     def _setup_stt_callbacks(self):
#         def handle_recognizing(evt):
#             text = evt.result.text.strip() if evt.result.text else ""
#             self.loop.call_soon_threadsafe(self._set_partial, text)

#         def handle_recognized(evt):
#             # Capture recognition time immediately — used for bot-speech gating
#             recognised_at = time.time()

#             text = evt.result.text.strip() if evt.result.text else ""
#             if not text:
#                 return

#             detected_lang = evt.result.properties.get(
#                 speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
#             )
#             lang_code = detected_lang.split("-")[0] if detected_lang else "en"
#             if lang_code in ["en", "hi", "gu"]:
#                 self.loop.call_soon_threadsafe(self._set_language, lang_code)

#             print(f"✅ Azure FINAL [{detected_lang}]: {text}")

#             # ── GATE 1: Discard if recognised while bot was speaking ───────
#             # Azure STT keeps running even when we stop feeding audio — its
#             # internal buffer can still produce a result after bot speech ends.
#             # Any result timestamped inside [bot_started … bot_ended + grace]
#             # is the user talking OVER the bot; we must not process it.
#             if self._recognised_during_bot_speech(recognised_at):
#                 print(f"🚫 Azure FINAL discarded (recognised during bot speech): {text!r}")
#                 return

#             # Record when Azure fired so VAD path can check recency
#             self._azure_final_received_time = recognised_at

#             # ── GATE 2: Did VAD already dispatch this utterance? ───────────
#             if (
#                 self._vad_dispatched_text
#                 and (recognised_at - self._vad_dispatched_time) < 3.0
#                 and _is_duplicate_utterance(text, self._vad_dispatched_text)
#             ):
#                 print(f"⏭️ Azure FINAL suppressed (VAD already dispatched): {text!r}")
#                 self.loop.call_soon_threadsafe(self._clear_vad_dispatch)
#                 return

#             self.loop.call_soon_threadsafe(
#                 lambda: self.final_text_queue.put_nowait(text)
#             )

#         def handle_canceled(evt):
#             print("⚠️ STT Canceled:", evt.result.cancellation_details)

#         self.recognizer.recognizing.connect(handle_recognizing)
#         self.recognizer.recognized.connect(handle_recognized)
#         self.recognizer.canceled.connect(handle_canceled)

#     def _set_partial(self, text):
#         self.partial_text = text

#     def _set_language(self, lang_code):
#         if self.language != lang_code:
#             print(f"🌐 Language switched to: {lang_code}")
#             self.language = lang_code
#             self._tts_synthesizer = self._build_tts_synthesizer()

#     def _clear_vad_dispatch(self):
#         self._vad_dispatched_text = ""
#         self._vad_dispatched_time = 0.0

#     def _mark_bot_speaking_start(self):
#         """Call immediately before bot audio begins playing."""
#         self._bot_speaking_started_at = time.time()
#         self._bot_speaking_ended_at = 0.0
#         # Wipe any STT partial that was building before bot started — it's stale
#         self.partial_text = ""

#     def _mark_bot_speaking_end(self):
#         """Call immediately after bot audio finishes or is cancelled."""
#         self._bot_speaking_ended_at = time.time()
#         # Drain every STT result that arrived while bot was speaking — all stale
#         drained = 0
#         while not self.final_text_queue.empty():
#             try:
#                 self.final_text_queue.get_nowait()
#                 drained += 1
#             except asyncio.QueueEmpty:
#                 break
#         if drained:
#             print(f"🧹 Drained {drained} stale STT result(s) after bot speech")
#         # Clear partial too — Azure was hearing bot audio, not user
#         self.partial_text = ""

#     def _recognised_during_bot_speech(self, recognised_at: float) -> bool:
#         """
#         True if an Azure recognition arrived while the bot was speaking OR
#         within the post-speech grace window (self._post_speech_grace seconds).
#         recognised_at = time.time() captured inside handle_recognized callback.
#         """
#         if self._bot_speaking_started_at == 0.0:
#             return False
#         bot_finished = self._bot_speaking_ended_at if self._bot_speaking_ended_at else time.time()
#         grace_end = bot_finished + self._post_speech_grace
#         return self._bot_speaking_started_at <= recognised_at <= grace_end

#     # ================= FINAL TEXT CONSUMER =================

#     async def _final_text_consumer(self):
#         while self.is_connected:
#             try:
#                 text = await asyncio.wait_for(self.final_text_queue.get(), timeout=1.0)
#             except asyncio.TimeoutError:
#                 continue
#             except Exception:
#                 break

#             if not text:
#                 continue

#             if self.is_bot_speaking or self.is_processing:
#                 print("⏭️ Skipped (bot busy):", text)
#                 continue

#             normalized = _normalize(text)

#             # Check against last dispatched using fuzzy match
#             if self.last_dispatched_text and _is_duplicate_utterance(text, self.last_dispatched_text):
#                 # Only skip if dispatch was recent (within 4 seconds)
#                 if time.time() - self.last_dispatch_time < 4.0:
#                     print("⏭️ Duplicate skipped (final consumer):", text)
#                     continue

#             if time.time() - self.last_dispatch_time < 0.5:
#                 print("⏭️ Cooldown skip:", text)
#                 continue

#             if len(text.split()) < self.MIN_WORD_COUNT:
#                 print("⏭️ Too short:", text)
#                 continue

#             print("⚡ DISPATCHING TO AI (Azure final):", text)
#             self.last_dispatched_text = normalized
#             self.last_dispatch_time = time.time()
#             # Clear any stale VAD dispatch record since Azure final now owns this utterance
#             self._clear_vad_dispatch()
#             self.partial_text = ""

#             self.is_processing = True
#             try:
#                 async with self.processing_lock:
#                     await self.handle_ai_reply(text)
#             finally:
#                 self.is_processing = False

#     # ================= RECEIVE =================

#     async def receive(self, text_data=None, bytes_data=None):
#         if not text_data:
#             return

#         try:
#             data = json.loads(text_data)

#             if data.get("event") == "start":
#                 self.stream_sid = data["start"].get("streamSid")
#                 print(f"📡 streamSid captured: {self.stream_sid}")
#                 # Save stream_sid to DB for CDR matching
#                 if self.stream_sid:
#                     await save_stream_sid(self.conversation, self.stream_sid)
#                     print(f"💾 streamSid saved to DB for conversation {self.conversation.id}")
#                 try:
#                     # For outbound calls, 'calledNumber' is the customer.
#                     # 'callerNumber' is often the bot's DID.
#                     custom = data["start"].get("customParameters", {})
#                     number = custom.get("calledNumber") or custom.get("callerNumber")
                    
#                     # Only update if we don't have a valid number yet (like from URL params)
#                     if number and (self.user_number == "unknown" or not self.user_number):
#                         self.user_number = number
#                         await update_user_number(self.conversation, number)
#                 except Exception:
#                     pass

#             if data.get("event") == "media":
#                 await self._handle_audio_chunk(data)

#         except Exception as e:
#             print("❌ RECEIVE ERROR:", e)

#     async def _handle_audio_chunk(self, data):
#         payload = base64.b64decode(data["media"]["payload"])
#         pcm = decode_g711(payload)

#         # Dynamic gain
#         pcm_np = np.frombuffer(pcm, dtype=np.int16).copy()
#         current_rms = audioop.rms(pcm, 2)
#         if current_rms > 50:
#             gain = min(1200 / current_rms, 6.0)
#             pcm_np = np.clip(pcm_np * gain, -32768, 32767).astype(np.int16)
#         pcm = pcm_np.tobytes()

#         if len(pcm) % 2 != 0:
#             pcm = pcm[:-1]

#         # Jitter buffer
#         self.jitter_buffer.append(pcm)
#         if len(self.jitter_buffer) < self.jitter_delay:
#             return

#         pcm = self.jitter_buffer.pop(0)
#         rms = audioop.rms(pcm, 2)

#         # Drop corrupt packets
#         pcm_check = np.frombuffer(pcm, dtype=np.int16)
#         if int(np.abs(pcm_check).max()) == 32767 and rms > 28000:
#             return

#         # ── INTERRUPT DETECTION ────────────────────────────────
#         if self.is_bot_speaking:
#             return  # Do NOT feed audio to Azure STT while bot is speaking

#         # Feed to Azure STT only when bot is silent
#         self.push_stream.write(pcm)

#         # ── VAD PARTIAL-TEXT DISPATCH ──────────────────────────
#         if rms > self.SPEECH_DETECT_RMS:
#             self.speech_active = True
#             self.silence_start_time = None
#         else:
#             if self.speech_active:
#                 if self.silence_start_time is None:
#                     self.silence_start_time = time.time()
#                 elif time.time() - self.silence_start_time > self.SILENCE_TRIGGER_SEC:
#                     self.speech_active = False
#                     self.silence_start_time = None

#                     if (
#                         not self.is_bot_speaking
#                         and not self.is_processing
#                         and self.partial_text
#                     ):
#                         fallback_text = self.partial_text.strip()
#                         self.partial_text = ""

#                         if len(fallback_text.split()) < self.MIN_WORD_COUNT:
#                             return

#                         normalized = _normalize(fallback_text)

#                         # ── DEDUP: skip if already dispatched recently ─────
#                         if self.last_dispatched_text and _is_duplicate_utterance(fallback_text, self.last_dispatched_text):
#                             if time.time() - self.last_dispatch_time < 4.0:
#                                 print("⏭️ VAD duplicate skipped:", fallback_text)
#                                 return

#                         if time.time() - self.last_dispatch_time < 0.5:
#                             return

#                         # ── DEDUP: if Azure final arrived very recently for
#                         #    the same content, let Azure final handle it ─────
#                         if (time.time() - self._azure_final_received_time) < 0.5:
#                             print("⏭️ VAD skipped — Azure final just fired, letting it handle:", fallback_text)
#                             return

#                         print("⚡ FAST DISPATCH (partial VAD):", fallback_text)

#                         # Record that VAD dispatched this so Azure final can skip it
#                         self._vad_dispatched_text = normalized
#                         self._vad_dispatched_time = time.time()

#                         self.last_dispatched_text = normalized
#                         self.last_dispatch_time = time.time()
#                         self.is_processing = True
#                         try:
#                             async with self.processing_lock:
#                                 await self.handle_ai_reply(fallback_text)
#                         finally:
#                             self.is_processing = False

#     async def _check_interrupt(self, rms):
#         """Detect user barge-in while bot is speaking."""
#         if rms < self.INTERRUPT_RMS:
#             self.interrupt_start_time = None
#             return

#         if self.interrupt_start_time is None:
#             self.interrupt_start_time = time.time()
#             return

#         if time.time() - self.interrupt_start_time < self.INTERRUPT_HOLD_SEC:
#             return

#         print("🛑 INTERRUPT DETECTED — stopping bot, capturing user speech")

#         interrupted_partial = self.partial_text.strip()
#         interrupt_time = time.time()

#         self.is_bot_speaking = False
#         self.interrupt_start_time = None

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         await self._send_clear_event()
#         self.jitter_buffer.clear()

#         asyncio.create_task(
#             self._interruption_fallback(interrupted_partial, interrupt_time)
#         )

#     # ================= INTERRUPT HELPERS =================

#     async def _send_clear_event(self):
#         if self.stream_sid:
#             try:
#                 await self.send(text_data=json.dumps({
#                     "event": "clear",
#                     "streamSid": self.stream_sid
#                 }))
#                 print("📢 Twilio audio buffer cleared")
#             except Exception as e:
#                 print(f"❌ Clear event failed: {e}")

#     async def _interruption_fallback(self, partial_text, interrupt_time):
#         await asyncio.sleep(1.5)

#         if self.last_dispatch_time > interrupt_time:
#             print("✅ Interrupt speech already dispatched via normal path")
#             return

#         if self.is_bot_speaking or self.is_processing:
#             print("⏭️ Interrupt fallback skipped (pipeline busy)")
#             return

#         final_text = None
#         try:
#             final_text = self.final_text_queue.get_nowait()
#         except asyncio.QueueEmpty:
#             pass

#         text = final_text or self.partial_text.strip() or partial_text
#         self.partial_text = ""

#         if not text or len(text.split()) < self.MIN_WORD_COUNT:
#             print("⏭️ Interrupt text too short:", text)
#             return

#         normalized = _normalize(text)
#         if self.last_dispatched_text and _is_duplicate_utterance(text, self.last_dispatched_text):
#             if time.time() - self.last_dispatch_time < 4.0:
#                 print("⏭️ Interrupt duplicate skipped:", text)
#                 return

#         print("⚡ INTERRUPT FALLBACK DISPATCH:", text)
#         self.last_dispatched_text = normalized
#         self.last_dispatch_time = time.time()

#         self.is_processing = True
#         try:
#             async with self.processing_lock:
#                 await self.handle_ai_reply(text)
#         finally:
#             self.is_processing = False

#     # ================= STREAMING LLM BRIDGE =================

#     async def _stream_llm(self, system_prompt, user_message):
#         queue = asyncio.Queue()
#         loop = asyncio.get_event_loop()

#         def _run_streaming():
#             try:
#                 for chunk in generate_response_streaming(system_prompt, user_message):
#                     loop.call_soon_threadsafe(queue.put_nowait, chunk)
#             except Exception as e:
#                 print(f"❌ LLM Streaming error: {e}")
#             loop.call_soon_threadsafe(queue.put_nowait, None)

#         loop.run_in_executor(None, _run_streaming)

#         while True:
#             chunk = await queue.get()
#             if chunk is None:
#                 break
#             yield chunk

#     # ================= AI (STREAMING) =================

#     async def handle_ai_reply(self, text):
#         pipeline_start = time.time()
#         text = text.strip()
#         if not text:
#             return

#         normalized = text.lower().strip()

#         # ── END INTENT ────────────────────────────────────────
#         if is_end_intent(normalized):
#             print("📴 END INTENT DETECTED:", text)

#             await save_message(self.conversation, "user", text)

#             if self.agent_tts_lang == "gu":
#                 farewell = "આપનો ખૂબ ખૂબ આભાર! જ્યારે પણ મિલકત વિશે કોઈ પ્રશ્ન હોય, અમે હંમેશા ઉપલબ્ધ છીએ. ધ્યાન રાખજો!"
#             elif self.agent_tts_lang == "interview_en":
#                 farewell = "Thank you for your time. All the best for your preparation!"
#             else:
#                 farewell = "Thank you for calling! Koi aur help chahiye toh zaroor call karna. Take care!"

#             await save_message(self.conversation, "bot", farewell)

#             if self.tts_task and not self.tts_task.done():
#                 self.tts_task.cancel()
#                 try:
#                     await self.tts_task
#                 except asyncio.CancelledError:
#                     pass

#             tts_lang_for_farewell = "gu" if self.agent_tts_lang == "gu" else "en"
#             await self.send_tts(farewell, tts_language=tts_lang_for_farewell)
#             await close_conversation(self.conversation)

#             await self.send(text_data=json.dumps({"event": "stop"}))

#             self.is_connected = False
#             await self.close()
#             return

#         # ── MAIN STREAMING PIPELINE ───────────────────────────
#         print("🧠 AI INPUT:", text)

#         t_prep = time.time()
#         _, prep_result = await asyncio.gather(
#             save_message(self.conversation, "user", text),
#             sync_to_async(prepare_streaming)(self.agent_id, text, self.session_id)
#         )
#         prep_ms = round((time.time() - t_prep) * 1000)

#         tts_language = prep_result.get("tts_language", self.language)
#         skip_output_translation = prep_result.get("skip_output_translation", False)
#         skip_input_translation = prep_result.get("skip_input_translation", False)

#         t_translate_in = time.time()
#         message_for_ai = text
#         translate_input_to = prep_result.get("translate_input_to", None)

#         if translate_input_to == "gu":
#             if self.language != "gu":
#                 message_for_ai = await sync_to_async(translate_text)(
#                     text, from_lang=self.language, to_lang="gu"
#                 )
#                 print(f"🌐 [{self.language}→gu]: {message_for_ai}")
#         elif translate_input_to is None and self.language != "en":
#             message_for_ai = await sync_to_async(translate_text)(
#                 text, from_lang=self.language, to_lang="en"
#             )
#             print(f"🌐 [{self.language}→en]: {message_for_ai}")

#         translate_in_ms = round((time.time() - t_translate_in) * 1000)

#         # Step 3a: Static reply
#         if "static_reply" in prep_result:
#             reply = prep_result["static_reply"]
#             if not reply:
#                 return

#             reply_for_user = reply
#             if not skip_output_translation and self.language != "en":
#                 reply_for_user = await sync_to_async(translate_text)(
#                     reply, from_lang="en", to_lang=self.language
#                 )

#             total_ms = round((time.time() - pipeline_start) * 1000)
#             print(f"⏱ PIPELINE (static): prep={prep_ms}ms | TOTAL={total_ms}ms")

#             await save_message(self.conversation, "bot", reply_for_user)
#             print("🤖 BOT REPLY:", reply_for_user)

#             if self.tts_task and not self.tts_task.done():
#                 self.tts_task.cancel()
#                 try:
#                     await self.tts_task
#                 except asyncio.CancelledError:
#                     pass

#             self.tts_task = asyncio.create_task(
#                 self.send_tts(reply_for_user, tts_language=tts_language)
#             )

#             if prep_result.get("auto_disconnect"):
#                 print("📴 AUTO-DISCONNECT (static reply): Booking confirmed by user — ending call")
#                 await self.tts_task
#                 await close_conversation(self.conversation)
#                 await self.send(text_data=json.dumps({"event": "stop"}))
#                 self.is_connected = False
#                 await self.close()

#             return

#         # Step 3b: STREAMING LLM + PER-SENTENCE TTS
#         system_prompt = prep_result["system_prompt"]
#         user_message = prep_result["user_message"]

#         if not skip_input_translation and message_for_ai != text:
#             user_message = message_for_ai

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         self.is_bot_speaking = True
#         self._mark_bot_speaking_start()
#         t_llm = time.time()

#         audio_queue = asyncio.Queue()
#         full_response = ""
#         first_sentence_time = None

#         def _strip_disconnect_tags(text):
#             for t in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]",
#                       "BOOKING_CONFIRMED", "NOT_INTERESTED", "LEAD_COMPLETE"]:
#                 text = text.replace(t, "")
#             return text.replace("[", "").replace("]", "").strip()

#         async def streaming_producer():
#             nonlocal full_response, first_sentence_time
#             sentence_buffer = ""
#             loop = asyncio.get_event_loop()

#             async for chunk in self._stream_llm(system_prompt, user_message):
#                 if not self.is_bot_speaking:
#                     break
#                 full_response += chunk
#                 clean_chunk = chunk
#                 for _tag in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]"]:
#                     clean_chunk = clean_chunk.replace(_tag, "")
#                 for _inner in ["BOOKING_CONFIRMED", "NOT_INTERESTED", "LEAD_COMPLETE"]:
#                     clean_chunk = clean_chunk.replace(_inner, "")
#                 clean_chunk = clean_chunk.replace("[", "").replace("]", "")
#                 sentence_buffer += clean_chunk

#                 # if tts_language == "gu":
#                 #     boundary = re.search(r'[!?।]\s|[.]\s+(?=[A-Z\u0A80-\u0AFF])', sentence_buffer)
#                 # else:
#                 #     boundary = re.search(r'[.!?।]\s|[,;]\s+(?=\S)', sentence_buffer)

#                 if first_sentence_time is None:
#                     boundary = re.search(r'[,;।!?]|\.\s+', sentence_buffer)
#                 elif tts_language == "gu":
#                     boundary = re.search(r'[!?।]\s|[.]\s+(?=[A-Z\u0A80-\u0AFF])', sentence_buffer)
#                 else:
#                     boundary = re.search(r'[.!?।]\s|[,;]\s+(?=\S)', sentence_buffer)

#                 if boundary:
#                     sentence = sentence_buffer[:boundary.start() + 1].strip()
#                     sentence_buffer = sentence_buffer[boundary.end():]
#                     if sentence:
#                         if first_sentence_time is None:
#                             first_sentence_time = time.time()
#                             print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

#                         sentence = _strip_disconnect_tags(sentence)
#                         if not sentence:
#                             continue
#                         tts_text = sentence
#                         if not skip_output_translation and self.language != "en":
#                             tts_text = await sync_to_async(translate_text)(
#                                 sentence, from_lang="en", to_lang=self.language
#                             )

#                         try:
#                             ulaw = await asyncio.wait_for(
#                                 loop.run_in_executor(
#                                     None,
#                                     lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
#                                 ),
#                                 timeout=15
#                             )
#                             await audio_queue.put(ulaw)
#                         except asyncio.TimeoutError:
#                             print(f"❌ TTS timeout: {sentence[:40]}")

#             if sentence_buffer.strip() and self.is_bot_speaking:
#                 sentence = sentence_buffer.strip()
#                 if first_sentence_time is None:
#                     first_sentence_time = time.time()
#                     print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

#                 sentence = _strip_disconnect_tags(sentence)
#                 if not sentence:
#                     await audio_queue.put(None)
#                     return
#                 tts_text = sentence
#                 if not skip_output_translation and self.language != "en":
#                     tts_text = await sync_to_async(translate_text)(
#                         sentence, from_lang="en", to_lang=self.language
#                     )
#                 try:
#                     ulaw = await asyncio.wait_for(
#                         loop.run_in_executor(
#                             None,
#                             lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
#                         ),
#                         timeout=15
#                     )
#                     await audio_queue.put(ulaw)
#                 except asyncio.TimeoutError:
#                     pass

#             await audio_queue.put(None)

#         async def streaming_consumer():
#             while True:
#                 ulaw = await audio_queue.get()
#                 if ulaw is None:
#                     break
#                 if not self.is_bot_speaking:
#                     break
#                 await self._stream_ulaw(ulaw)

#         producer_task = asyncio.create_task(streaming_producer())
#         consumer_task = asyncio.create_task(streaming_consumer())
#         self.tts_task = consumer_task

#         try:
#             await asyncio.gather(producer_task, consumer_task)
#         except asyncio.CancelledError:
#             print("🛑 STREAMING TTS CANCELLED")
#         except Exception as e:
#             print("❌ STREAMING ERROR:", e)
#         finally:
#             self.is_bot_speaking = False
#             self._mark_bot_speaking_end()

#         llm_ms = round((time.time() - t_llm) * 1000)
#         total_ms = round((time.time() - pipeline_start) * 1000)
#         print(f"⏱ STREAMING PIPELINE: translate_in={translate_in_ms}ms | prep={prep_ms}ms | LLM+TTS={llm_ms}ms | TOTAL={total_ms}ms")

#         if full_response:
#             await sync_to_async(finalize_streaming)(full_response, prep_result)

#         for _tag in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]"]:
#             full_response = full_response.replace(_tag, "")
#         full_response = full_response.strip()

#         reply_for_user = full_response
#         if not skip_output_translation and self.language != "en" and full_response:
#             reply_for_user = await sync_to_async(translate_text)(
#                 full_response, from_lang="en", to_lang=self.language
#             )
#         if reply_for_user:
#             await save_message(self.conversation, "bot", reply_for_user)
#         print("🤖 BOT REPLY:", reply_for_user)

#         if prep_result.get("auto_disconnect"):
#             if prep_result.get("skip_name_collection"):
#                 print("📴 AUTO-DISCONNECT (insurance): Ending call immediately")
#                 await asyncio.sleep(1.5)
#                 await close_conversation(self.conversation)
#                 await self.send(text_data=json.dumps({"event": "stop"}))
#                 self.is_connected = False
#                 await self.close()
#                 return

#             print("📴 BOOKING CONFIRMED — LLM asked for name, waiting for user response")
#             state = prep_result.get("state", {})
#             session_obj = prep_result.get("session")
#             if state is not None and session_obj:
#                 state["name_collection_pending"] = True
#                 from conversations.services.core.strategies import save_session
#                 await sync_to_async(save_session)(session_obj, state)
#             return

#     # ================= TTS HELPERS =================


#     def _get_synthesizer(self, language: str):
#         """Reuses cached synthesizer or builds a new one if needed."""
#         if language in self._tts_synthesizers:
#             return self._tts_synthesizers[language]
            
#         synthesizer = self._build_tts_synthesizer(language)
#         self._tts_synthesizers[language] = synthesizer
#         return synthesizer

#     def _build_tts_synthesizer(self, language: str = None):
#         lang = language or self.language
#         speech_config = speechsdk.SpeechConfig(
#             subscription=os.getenv("AZURE_SPEECH_KEY"),
#             region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
#         )
#         speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
#         speech_config.set_speech_synthesis_output_format(
#             speechsdk.SpeechSynthesisOutputFormat.Riff8Khz16BitMonoPcm
#         )
#         return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

#     def _synthesize_ulaw(self, text: str, language: str = None) -> bytes:
#         lang = language or self.language
#         ssml = build_ssml(text, lang)

#         # if lang != self.language:
#         #     speech_config = speechsdk.SpeechConfig(
#         #         subscription=os.getenv("AZURE_SPEECH_KEY"),
#         #         region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
#         #     )
#         #     speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
#         #     speech_config.set_speech_synthesis_output_format(
#         #         speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#         #     )
#         #     synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
#         #     result = synthesizer.speak_ssml_async(ssml).get()
#         # else:
#         #     result = self._tts_synthesizer.speak_ssml_async(ssml).get()

#         # Use cached synthesizer
#         synthesizer = self._get_synthesizer(lang)
#         result = synthesizer.speak_ssml_async(ssml).get()

#         if result.reason == speechsdk.ResultReason.Canceled:
#             details = result.cancellation_details
#             print("❌ TTS Canceled:", details.reason, details.error_details)
#             return b""

#         pcm = result.audio_data
#         pcm = strip_wav_header(pcm)

#         if len(pcm) % 2 != 0:
#             pcm = pcm[:-1]

#         return encode_g711(pcm)

#     async def _stream_ulaw(self, ulaw: bytes):
#         if not ulaw:
#             return

#         loop = asyncio.get_event_loop()

#         # for _ in range(2):
#         #     if not self.is_bot_speaking:
#         #         return
#         #     await self._send_media_frame(SILENCE_FRAME)
#         #     await asyncio.sleep(0.020)

#         start_time = loop.time()
#         for idx, i in enumerate(range(0, len(ulaw), 160)):
#             if not self.is_bot_speaking:
#                 print("🛑 TTS stopped mid-stream")
#                 return

#             chunk = ulaw[i:i + 160].ljust(160, b'\x7f')
#             await self._send_media_frame(chunk)

#             target_time = start_time + (idx + 1) * 0.020
#             sleep_duration = target_time - loop.time()
#             if sleep_duration > 0:
#                 await asyncio.sleep(sleep_duration)

#         # for _ in range(2):
#         #     if not self.is_bot_speaking:
#         #         return
#         #     await self._send_media_frame(SILENCE_FRAME)
#         #     await asyncio.sleep(0.020)

#     async def _send_media_frame(self, chunk: bytes):
#         payload = base64.b64encode(chunk).decode()
#         msg = {
#             "event": "media",
#             "media": {"payload": payload}
#         }
#         if self.stream_sid:
#             msg["streamSid"] = self.stream_sid
#         await self.send(text_data=json.dumps(msg))

#     # ================= TTS (static replies / intro) =================

#     async def send_tts(self, text, tts_language: str = None):
#         self.is_bot_speaking = True
#         self._mark_bot_speaking_start()
#         loop = asyncio.get_event_loop()
#         lang = tts_language or self.language

#         try:
#             sentences = split_into_sentences(text)
#             audio_queue = asyncio.Queue()

#             async def producer():
#                 for sentence in sentences:
#                     if not self.is_bot_speaking:
#                         break
#                     try:
#                         ulaw = await asyncio.wait_for(
#                             loop.run_in_executor(
#                                 None,
#                                 lambda s=sentence, l=lang: self._synthesize_ulaw(s, l)
#                             ),
#                             timeout=15
#                         )
#                     except asyncio.TimeoutError:
#                         print(f"❌ TTS TIMEOUT for sentence: {sentence[:40]}")
#                         ulaw = b""
#                     await audio_queue.put(ulaw)
#                 await audio_queue.put(None)

#             async def consumer():
#                 while True:
#                     ulaw = await audio_queue.get()
#                     if ulaw is None:
#                         break
#                     if not self.is_bot_speaking:
#                         break
#                     await self._stream_ulaw(ulaw)

#             producer_task = asyncio.create_task(producer())
#             consumer_task = asyncio.create_task(consumer())

#             await asyncio.gather(producer_task, consumer_task)

#         except asyncio.CancelledError:
#             print("🛑 TTS CANCELLED")
#             raise
#         except Exception as e:
#             print("❌ TTS ERROR:", e)
#         finally:
#             self.is_bot_speaking = False
#             self._mark_bot_speaking_end()

#     # ================= DISCONNECT =================

#     async def disconnect(self, close_code):
#         print("🔌 DISCONNECTED:", close_code)
#         self.is_connected = False

#         if hasattr(self, "keepalive_task"):
#             self.keepalive_task.cancel()
#             try:
#                 await self.keepalive_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "final_consumer_task"):
#             self.final_consumer_task.cancel()
#             try:
#                 await self.final_consumer_task
#             except asyncio.CancelledError:
#                 pass

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "recognizer"):
#             try:
#                 self.recognizer.stop_continuous_recognition_async()
#             except Exception:
#                 pass

#         if hasattr(self, "push_stream"):
#             try:
#                 self.push_stream.close()
#             except Exception:
#                 pass

#         if hasattr(self, "conversation"):
#             await close_conversation(self.conversation)

#             conv_id = self.conversation.id
#             user_phone = self.user_number  # Capture phone for auto-dialer
            
#             import threading
#             def _run_lead_analysis():
#                 try:
#                     from conversations.services.lead_analyzer import analyze_lead
#                     analyze_lead(conv_id)
#                 except Exception as e:
#                     print(f"❌ Lead analysis background error: {e}")
                
#                 # 🔄 AUTO-DIALER FALLBACK: Trigger next call if campaign is active
#                 try:
#                     from bot.views import on_call_ended, _campaign_active
#                     if _campaign_active:
#                         print(f"🔄 AUTO-DIALER (disconnect fallback): Triggering next call for {user_phone}")
#                         on_call_ended(user_phone)
#                 except Exception as e:
#                     print(f"⚠️ Auto-dialer fallback error: {e}")

#             threading.Thread(target=_run_lead_analysis, daemon=True).start()
#             print("📊 Lead analysis started in background...")





































# # # 27/04/2026 5:10 ee update karelu cousumer je RAG mate kamm kre chhe..........................................................................

# # """
# # consumers.py — full fixed version
# # All three bugs patched inline. Diff-friendly: search for "# ✅ FIX" comments.
# # """

# # from urllib.parse import parse_qs
# # import audioop
# # from asgiref.sync import sync_to_async
# # import json
# # from channels.generic.websocket import AsyncWebsocketConsumer
# # from conversations.services.core.dialogue_engine import process_message, prepare_streaming, finalize_streaming, get_agent_tts_language
# # from conversations.services.azure_openai_service import generate_response_streaming
# # from conversations.services.speech_service import create_speech_recognizer
# # from conversations.services.translator_service import translate_text
# # import asyncio
# # import os
# # import azure.cognitiveservices.speech as speechsdk
# # import time
# # import base64
# # import uuid
# # import numpy as np
# # import re
# # from django.utils import timezone

# # from agents.models import VoiceAgent
# # from conversations.models import Conversation, Message


# # # ================= DATABASE =================

# # @sync_to_async
# # def create_conversation(agent_id, session_id, user_number):
# #     return Conversation.objects.create(
# #         agent_id=agent_id,
# #         session_id=session_id,
# #         user_number=user_number
# #     )


# # @sync_to_async
# # def save_message(conversation, role, text):
# #     last = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
# #     if last and last.text.strip() == text.strip() and last.role == role:
# #         return
# #     Message.objects.create(conversation=conversation, role=role, text=text)


# # @sync_to_async
# # def update_user_number(conversation, number):
# #     conversation.user_number = number
# #     conversation.save()


# # @sync_to_async
# # def close_conversation(conversation):
# #     conversation.ended_at = timezone.now()
# #     conversation.save()


# # @sync_to_async
# # def get_agent_summary(agent_id):
# #     try:
# #         agent = VoiceAgent.objects.get(id=agent_id)
# #         company = agent.company_name or "our company"
# #         if agent.summary:
# #             summary = agent.summary.strip().rstrip(".")
# #             return f"Hello, I am {agent.name} from {company}. {summary}."
# #         return f"Hello, I am {agent.name} from {company}."
# #     except VoiceAgent.DoesNotExist:
# #         return "Hello, how can I assist you today?"


# # @sync_to_async
# # def mark_intro_shown(agent_id, session_id):
# #     from conversations.models import ConversationSession
# #     from agents.models import VoiceAgent
# #     try:
# #         agent = VoiceAgent.objects.get(id=agent_id)
# #         session, _ = ConversationSession.objects.get_or_create(
# #             agent=agent,
# #             session_id=session_id
# #         )
# #         state = session.state or {}
# #         state["intro_shown"] = True
# #         session.state = state
# #         session.save()
# #     except Exception as e:
# #         print("❌ mark_intro_shown error:", e)


# # # ================= AUDIO =================

# # def decode_g711(ulaw):
# #     return audioop.ulaw2lin(ulaw, 2)


# # def encode_g711(pcm):
# #     return audioop.lin2ulaw(pcm, 2)


# # def strip_wav_header(data: bytes) -> bytes:
# #     if data[:4] != b'RIFF':
# #         return data
# #     offset = 12
# #     while offset < len(data) - 8:
# #         chunk_id = data[offset:offset + 4]
# #         chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
# #         if chunk_id == b'data':
# #             return data[offset + 8:]
# #         offset += 8 + chunk_size
# #     return data[44:]


# # SILENCE_FRAME = b'\x7f' * 160


# # def split_into_sentences(text: str) -> list:
# #     sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', text) if s.strip()]
# #     return sentences if sentences else [text]


# # def is_end_intent(text: str) -> bool:
# #     text = text.lower().strip()
# #     end_keywords = [
# #         "bye", "goodbye", "ok bye", "okay bye",
# #         "thank you", "thanks a lot",
# #         "that's all", "no thanks", "call end",
# #         "અلविदा", "બાय", "આભાર"
# #     ]
# #     return any(keyword in text for keyword in end_keywords)


# # # ================= SSML BUILDER =================

# # TTS_VOICE_MAP = {
# #     "en": "en-IN-AnanyaNeural",
# #     "hi": "hi-IN-AnanyaNeural",
# #     "gu": "gu-IN-DhwaniNeural",
# # }

# # SSML_STYLE_MAP = {
# #     "en": None,
# #     "hi": None,
# #     "gu": None,
# # }

# # SSML_PROSODY_MAP = {
# #     "en": {"rate": "-3%", "pitch": "+1Hz"},
# #     "hi": {"rate": "-3%", "pitch": "0Hz"},
# #     "gu": {"rate": "+10%", "pitch": "0Hz"},
# # }


# # def _inject_english_lang_tags(text: str) -> str:
# #     import re

# #     def escape_xml(s):
# #         return s.replace('&', '&amp;').replace('"', '&quot;')

# #     def expand_if_acronym(word: str) -> str:
# #         if re.match(r'^[A-Z][A-Z0-9]+$', word):
# #             return ' '.join(word)
# #         if re.match(r'^[A-Z]{2,}', word) and re.search(r'[-/0-9]', word):
# #             parts = re.split(r'[-/]', word)
# #             spelled = []
# #             for part in parts:
# #                 if re.match(r'^[A-Z0-9]+$', part):
# #                     spelled.append(' '.join(part))
# #                 else:
# #                     spelled.append(part)
# #             return ' '.join(spelled)
# #         return word

# #     pattern = re.compile(r'([A-Za-z][A-Za-z0-9.\-/]*)')
# #     result = []
# #     last_end = 0

# #     for match in pattern.finditer(text):
# #         start, end = match.start(), match.end()
# #         gujarati_part = text[last_end:start]
# #         if gujarati_part:
# #             result.append(escape_xml(gujarati_part))
# #         english_word = match.group(1)
# #         expanded = expand_if_acronym(english_word)
# #         result.append(f'<lang xml:lang="en-IN">{escape_xml(expanded)}</lang>')
# #         last_end = end

# #     remaining = text[last_end:]
# #     if remaining:
# #         result.append(escape_xml(remaining))

# #     return ''.join(result)


# # def build_ssml(text: str, language: str) -> str:
# #     voice = TTS_VOICE_MAP.get(language, TTS_VOICE_MAP["en"])
# #     style = SSML_STYLE_MAP.get(language)
# #     prosody = SSML_PROSODY_MAP.get(language, SSML_PROSODY_MAP["en"])
# #     lang_tag = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}.get(language, "en-IN")

# #     if language == "gu":
# #         text = _inject_english_lang_tags(text)
# #     else:
# #         text = text.replace('&', '&amp;')

# #     prosody_open = f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}">'
# #     prosody_close = '</prosody>'

# #     if style:
# #         inner = (
# #             f'<mstts:express-as style="{style}">'
# #             f'{prosody_open}{text}{prosody_close}'
# #             f'</mstts:express-as>'
# #         )
# #     else:
# #         inner = f'{prosody_open}{text}{prosody_close}'

# #     return (
# #         f'<speak version="1.0" '
# #         f'xmlns="http://www.w3.org/2001/10/synthesis" '
# #         f'xmlns:mstts="http://www.w3.org/2001/mstts" '
# #         f'xml:lang="{lang_tag}">'
# #         f'<voice name="{voice}">'
# #         f'{inner}'
# #         f'</voice>'
# #         f'</speak>'
# #     )


# # # ================= CONSUMER =================

# # class VoiceBotConsumer(AsyncWebsocketConsumer):

# #     async def connect(self):
# #         self.loop = asyncio.get_running_loop()

# #         params = parse_qs(self.scope["query_string"].decode())
# #         self.agent_id = params.get("agent_id", [None])[0]
# #         self.user_number = params.get("from", ["unknown"])[0]
# #         self.language = params.get("language", ["en"])[0]

# #         if not self.agent_id:
# #             await self.close()
# #             return

# #         self.session_id = str(uuid.uuid4())
# #         self.conversation = await create_conversation(
# #             self.agent_id, self.session_id, self.user_number
# #         )

# #         self.stream_sid = None

# #         self.is_bot_speaking = False
# #         self.is_connected = True
# #         self.is_processing = False
# #         self.partial_text = ""
# #         self.final_text_queue = asyncio.Queue()

# #         self.last_dispatched_text = ""
# #         self.last_dispatch_time = 0.0

# #         self.processing_lock = asyncio.Lock()
# #         self.tts_task = None

# #         self.jitter_buffer = []
# #         self.jitter_delay = 2

# #         self.speech_active = False
# #         self.silence_start_time = None

# #         self.SPEECH_DETECT_RMS = 200
# #         self.SILENCE_TRIGGER_SEC = 1.2
# #         self.MIN_WORD_COUNT = 1

# #         self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
# #         self._setup_stt_callbacks()
# #         self.recognizer.start_continuous_recognition_async()

# #         self._tts_synthesizer = self._build_tts_synthesizer()

# #         await self.accept()

# #         summary = await get_agent_summary(self.agent_id)
# #         agent_tts_lang = await sync_to_async(get_agent_tts_language)(self.agent_id)

# #         if agent_tts_lang != "en":
# #             summary = await sync_to_async(translate_text)(
# #                 summary, from_lang="en", to_lang=agent_tts_lang
# #             )
# #             asyncio.create_task(self.send_tts(summary, tts_language=agent_tts_lang))
# #         else:
# #             if self.language != "en":
# #                 summary = await sync_to_async(translate_text)(
# #                     summary, from_lang="en", to_lang=self.language
# #                 )
# #             asyncio.create_task(self.send_tts(summary))

# #         await mark_intro_shown(self.agent_id, self.session_id)

# #         self.final_consumer_task = asyncio.create_task(self._final_text_consumer())
# #         self.keepalive_task = asyncio.create_task(self._keepalive_loop())

# #     # ================= KEEPALIVE =================

# #     async def _keepalive_loop(self):
# #         while self.is_connected:
# #             await asyncio.sleep(25)
# #             if not self.is_connected:
# #                 break
# #             try:
# #                 await self.send(text_data=json.dumps({"event": "ping"}))
# #             except Exception as e:
# #                 print(f"❌ Keepalive failed: {e}")
# #                 break

# #     def _setup_stt_callbacks(self):
# #         def handle_recognizing(evt):
# #             text = evt.result.text.strip() if evt.result.text else ""
# #             self.loop.call_soon_threadsafe(self._set_partial, text)

# #         def handle_recognized(evt):
# #             text = evt.result.text.strip() if evt.result.text else ""
# #             if text:
# #                 detected_lang = evt.result.properties.get(
# #                     speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
# #                 )
# #                 lang_code = detected_lang.split("-")[0] if detected_lang else "en"
# #                 if lang_code in ["en", "hi", "gu"]:
# #                     self.loop.call_soon_threadsafe(self._set_language, lang_code)
# #                 print(f"✅ Azure FINAL [{detected_lang}]: {text}")
# #                 self.loop.call_soon_threadsafe(
# #                     lambda: self.final_text_queue.put_nowait(text)
# #                 )

# #         def handle_canceled(evt):
# #             print("⚠️ STT Canceled:", evt.result.cancellation_details)

# #         self.recognizer.recognizing.connect(handle_recognizing)
# #         self.recognizer.recognized.connect(handle_recognized)
# #         self.recognizer.canceled.connect(handle_canceled)

# #     def _set_partial(self, text):
# #         self.partial_text = text

# #     def _set_language(self, lang_code):
# #         if self.language != lang_code:
# #             print(f"🌐 Language switched to: {lang_code}")
# #             self.language = lang_code
# #             self._tts_synthesizer = self._build_tts_synthesizer()

# #     # ✅ FIX 1: _final_text_consumer — all error paths reset is_processing
# #     async def _final_text_consumer(self):
# #         while self.is_connected:
# #             try:
# #                 text = await asyncio.wait_for(self.final_text_queue.get(), timeout=1.0)
# #             except asyncio.TimeoutError:
# #                 continue
# #             except asyncio.CancelledError:
# #                 break
# #             except Exception as e:
# #                 print(f"❌ final_text_consumer queue error: {e}")
# #                 continue

# #             if not text:
# #                 continue

# #             if self.is_bot_speaking or self.is_processing:
# #                 print("⏭️ Skipped (bot busy):", text)
# #                 continue

# #             normalized = text.lower().strip()
# #             if normalized == self.last_dispatched_text:
# #                 print("⏭️ Duplicate skipped:", text)
# #                 continue

# #             if time.time() - self.last_dispatch_time < 0.8:
# #                 print("⏭️ Cooldown skip:", text)
# #                 continue

# #             if len(text.split()) < self.MIN_WORD_COUNT:
# #                 print("⏭️ Too short:", text)
# #                 continue

# #             # ✅ FIX: detect and reset a stuck lock instead of deadlocking
# #             if self.processing_lock.locked():
# #                 print("⚠️ processing_lock stuck — resetting")
# #                 self.processing_lock = asyncio.Lock()
# #                 self.is_processing = False
# #                 self.is_bot_speaking = False

# #             print("⚡ DISPATCHING TO AI:", text)
# #             self.last_dispatched_text = normalized
# #             self.last_dispatch_time = time.time()
# #             self.partial_text = ""
# #             self.is_processing = True

# #             try:
# #                 async with self.processing_lock:
# #                     await self.handle_ai_reply(text)

# #             except asyncio.CancelledError:
# #                 print("🛑 handle_ai_reply cancelled — resetting state")
# #                 self.is_bot_speaking = False

# #             except Exception as e:
# #                 print(f"❌ handle_ai_reply error: {e}")
# #                 self.is_bot_speaking = False

# #             finally:
# #                 # ✅ FIX: ALWAYS reset, even if handle_ai_reply threw
# #                 self.is_processing = False

# #     # ================= RECEIVE =================

# #     async def receive(self, text_data=None, bytes_data=None):
# #         if not text_data:
# #             return
# #         try:
# #             data = json.loads(text_data)

# #             if data.get("event") == "start":
# #                 self.stream_sid = data["start"].get("streamSid")
# #                 print(f"📡 streamSid captured: {self.stream_sid}")
# #                 try:
# #                     number = data["start"]["customParameters"]["callerNumber"]
# #                     self.user_number = number
# #                     await update_user_number(self.conversation, number)
# #                 except Exception:
# #                     pass

# #             if data.get("event") == "media":
# #                 await self._handle_audio_chunk(data)

# #         except Exception as e:
# #             print("❌ RECEIVE ERROR:", e)

# #     async def _handle_audio_chunk(self, data):
# #         payload = base64.b64decode(data["media"]["payload"])
# #         pcm = decode_g711(payload)

# #         pcm_np = np.frombuffer(pcm, dtype=np.int16).copy()
# #         current_rms = audioop.rms(pcm, 2)
# #         if current_rms > 50:
# #             gain = min(1200 / current_rms, 6.0)
# #             pcm_np = np.clip(pcm_np * gain, -32768, 32767).astype(np.int16)
# #         pcm = pcm_np.tobytes()

# #         if len(pcm) % 2 != 0:
# #             pcm = pcm[:-1]

# #         self.jitter_buffer.append(pcm)
# #         if len(self.jitter_buffer) < self.jitter_delay:
# #             return

# #         pcm = self.jitter_buffer.pop(0)
# #         rms = audioop.rms(pcm, 2)

# #         pcm_check = np.frombuffer(pcm, dtype=np.int16)
# #         if int(np.abs(pcm_check).max()) == 32767 and rms > 28000:
# #             return

# #         if self.is_bot_speaking:
# #             return

# #         self.push_stream.write(pcm)

# #         if rms > self.SPEECH_DETECT_RMS:
# #             self.speech_active = True
# #             self.silence_start_time = None
# #         else:
# #             if self.speech_active:
# #                 if self.silence_start_time is None:
# #                     self.silence_start_time = time.time()
# #                 elif time.time() - self.silence_start_time > self.SILENCE_TRIGGER_SEC:
# #                     self.speech_active = False
# #                     self.silence_start_time = None

# #                     if (
# #                         not self.is_bot_speaking
# #                         and not self.is_processing
# #                         and self.partial_text
# #                     ):
# #                         fallback_text = self.partial_text.strip()
# #                         self.partial_text = ""

# #                         if len(fallback_text.split()) >= self.MIN_WORD_COUNT:
# #                             normalized = fallback_text.lower()
# #                             if normalized != self.last_dispatched_text:
# #                                 if time.time() - self.last_dispatch_time >= 0.8:
# #                                     print("⚡ FAST DISPATCH (partial VAD):", fallback_text)
# #                                     self.last_dispatched_text = normalized
# #                                     self.last_dispatch_time = time.time()
# #                                     self.is_processing = True
# #                                     # ✅ FIX 3: try/finally in VAD path too
# #                                     try:
# #                                         async with self.processing_lock:
# #                                             await self.handle_ai_reply(fallback_text)
# #                                     except asyncio.CancelledError:
# #                                         print("🛑 VAD dispatch cancelled")
# #                                         self.is_bot_speaking = False
# #                                     except Exception as e:
# #                                         print(f"❌ VAD dispatch error: {e}")
# #                                         self.is_bot_speaking = False
# #                                     finally:
# #                                         self.is_processing = False


# #     # ================= STREAMING LLM BRIDGE =================

# #     async def _stream_llm(self, system_prompt, user_message):
# #         queue = asyncio.Queue()
# #         loop = asyncio.get_event_loop()

# #         def _run_streaming():
# #             try:
# #                 for chunk in generate_response_streaming(system_prompt, user_message):
# #                     loop.call_soon_threadsafe(queue.put_nowait, chunk)
# #             except Exception as e:
# #                 print(f"❌ LLM Streaming error: {e}")
# #             loop.call_soon_threadsafe(queue.put_nowait, None)

# #         loop.run_in_executor(None, _run_streaming)

# #         while True:
# #             chunk = await queue.get()
# #             if chunk is None:
# #                 break
# #             yield chunk

# #     # ================= AI (STREAMING) =================

# #     async def handle_ai_reply(self, text):
# #         pipeline_start = time.time()
# #         text = text.strip()
# #         if not text:
# #             return

# #         normalized = text.lower().strip()

# #         if is_end_intent(normalized):
# #             print("📴 END INTENT:", text)
# #             await save_message(self.conversation, "user", text)

# #             farewell_en = "Thank you for calling. Have a great day!"
# #             farewell = farewell_en
# #             if self.language != "en":
# #                 farewell = await sync_to_async(translate_text)(
# #                     farewell_en, from_lang="en", to_lang=self.language
# #                 )

# #             await save_message(self.conversation, "bot", farewell)

# #             if self.tts_task and not self.tts_task.done():
# #                 self.tts_task.cancel()
# #                 try:
# #                     await self.tts_task
# #                 except asyncio.CancelledError:
# #                     pass

# #             await self.send_tts(farewell)
# #             await close_conversation(self.conversation)
# #             await self.send(text_data=json.dumps({"event": "stop"}))
# #             self.is_connected = False
# #             await self.close()
# #             return

# #         print("🧠 AI INPUT:", text)
# #         await save_message(self.conversation, "user", text)

# #         t_prep = time.time()
# #         prep_result = await sync_to_async(prepare_streaming)(
# #             self.agent_id, text, self.session_id
# #         )
# #         prep_ms = round((time.time() - t_prep) * 1000)

# #         tts_language = prep_result.get("tts_language", self.language)
# #         skip_output_translation = prep_result.get("skip_output_translation", False)
# #         skip_input_translation = prep_result.get("skip_input_translation", False)

# #         t_translate_in = time.time()
# #         message_for_ai = text
# #         translate_input_to = prep_result.get("translate_input_to", None)

# #         if translate_input_to == "gu":
# #             if self.language != "gu":
# #                 message_for_ai = await sync_to_async(translate_text)(
# #                     text, from_lang=self.language, to_lang="gu"
# #                 )
# #         elif translate_input_to is None and self.language != "en":
# #             message_for_ai = await sync_to_async(translate_text)(
# #                 text, from_lang=self.language, to_lang="en"
# #             )

# #         translate_in_ms = round((time.time() - t_translate_in) * 1000)

# #         if "static_reply" in prep_result:
# #             reply = prep_result["static_reply"]
# #             if not reply:
# #                 return

# #             reply_for_user = reply
# #             if not skip_output_translation and self.language != "en":
# #                 reply_for_user = await sync_to_async(translate_text)(
# #                     reply, from_lang="en", to_lang=self.language
# #                 )

# #             total_ms = round((time.time() - pipeline_start) * 1000)
# #             print(f"⏱ PIPELINE (static): prep={prep_ms}ms | TOTAL={total_ms}ms")

# #             await save_message(self.conversation, "bot", reply_for_user)
# #             print("🤖 BOT REPLY:", reply_for_user)

# #             if self.tts_task and not self.tts_task.done():
# #                 self.tts_task.cancel()
# #                 try:
# #                     await self.tts_task
# #                 except asyncio.CancelledError:
# #                     pass

# #             self.tts_task = asyncio.create_task(
# #                 self.send_tts(reply_for_user, tts_language=tts_language)
# #             )
# #             return

# #         system_prompt = prep_result["system_prompt"]
# #         user_message = prep_result["user_message"]

# #         if not skip_input_translation and message_for_ai != text:
# #             user_message = message_for_ai

# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         self.is_bot_speaking = True
# #         t_llm = time.time()

# #         audio_queue = asyncio.Queue()
# #         full_response = ""
# #         first_sentence_time = None

# #         async def streaming_producer():
# #             nonlocal full_response, first_sentence_time
# #             sentence_buffer = ""
# #             loop = asyncio.get_event_loop()

# #             async for chunk in self._stream_llm(system_prompt, user_message):
# #                 if not self.is_bot_speaking:
# #                     break
# #                 full_response += chunk
# #                 sentence_buffer += chunk

# #                 boundary = re.search(r'[.!?।]\s', sentence_buffer)
# #                 if boundary:
# #                     sentence = sentence_buffer[:boundary.start() + 1].strip()
# #                     sentence_buffer = sentence_buffer[boundary.end():]
# #                     if sentence:
# #                         if first_sentence_time is None:
# #                             first_sentence_time = time.time()
# #                             print(f"⚡ First sentence in {round((first_sentence_time - t_llm)*1000)}ms: {sentence[:60]}")

# #                         tts_text = sentence
# #                         if not skip_output_translation and self.language != "en":
# #                             tts_text = await sync_to_async(translate_text)(
# #                                 sentence, from_lang="en", to_lang=self.language
# #                             )

# #                         try:
# #                             ulaw = await asyncio.wait_for(
# #                                 loop.run_in_executor(
# #                                     None,
# #                                     lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
# #                                 ),
# #                                 timeout=15
# #                             )
# #                             await audio_queue.put(ulaw)
# #                         except asyncio.TimeoutError:
# #                             print(f"❌ TTS timeout: {sentence[:40]}")

# #             if sentence_buffer.strip() and self.is_bot_speaking:
# #                 sentence = sentence_buffer.strip()
# #                 tts_text = sentence
# #                 if not skip_output_translation and self.language != "en":
# #                     tts_text = await sync_to_async(translate_text)(
# #                         sentence, from_lang="en", to_lang=self.language
# #                     )
# #                 try:
# #                     ulaw = await asyncio.wait_for(
# #                         loop.run_in_executor(
# #                             None,
# #                             lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
# #                         ),
# #                         timeout=15
# #                     )
# #                     await audio_queue.put(ulaw)
# #                 except asyncio.TimeoutError:
# #                     pass

# #             await audio_queue.put(None)

# #         async def streaming_consumer():
# #             while True:
# #                 ulaw = await audio_queue.get()
# #                 if ulaw is None:
# #                     break
# #                 if not self.is_bot_speaking:
# #                     break
# #                 await self._stream_ulaw(ulaw)

# #         producer_task = asyncio.create_task(streaming_producer())
# #         consumer_task = asyncio.create_task(streaming_consumer())
# #         self.tts_task = consumer_task

# #         # ✅ FIX 2: cancel both sub-tasks on any exception, always reset flags
# #         try:
# #             await asyncio.gather(producer_task, consumer_task)

# #         except asyncio.CancelledError:
# #             print("🛑 STREAMING TTS CANCELLED")
# #             for t in (producer_task, consumer_task):
# #                 if not t.done():
# #                     t.cancel()
# #             await asyncio.gather(producer_task, consumer_task, return_exceptions=True)

# #         except Exception as e:
# #             print(f"❌ STREAMING ERROR: {e}")
# #             for t in (producer_task, consumer_task):
# #                 if not t.done():
# #                     t.cancel()
# #             await asyncio.gather(producer_task, consumer_task, return_exceptions=True)

# #         finally:
# #             # ✅ FIX: reset BOTH flags here — is_processing reset happens in caller
# #             self.is_bot_speaking = False
# #             self.tts_task = None

# #         llm_ms = round((time.time() - t_llm) * 1000)
# #         total_ms = round((time.time() - pipeline_start) * 1000)
# #         print(f"⏱ STREAMING: translate_in={translate_in_ms}ms | prep={prep_ms}ms | LLM+TTS={llm_ms}ms | TOTAL={total_ms}ms")

# #         reply_for_user = full_response
# #         if not skip_output_translation and self.language != "en" and full_response:
# #             reply_for_user = await sync_to_async(translate_text)(
# #                 full_response, from_lang="en", to_lang=self.language
# #             )
# #         if reply_for_user:
# #             await save_message(self.conversation, "bot", reply_for_user)
# #         print("🤖 BOT REPLY:", reply_for_user)

# #         if full_response:
# #             await sync_to_async(finalize_streaming)(full_response, prep_result)

# #     # ================= TTS HELPERS =================

# #     def _build_tts_synthesizer(self, language: str = None):
# #         lang = language or self.language
# #         speech_config = speechsdk.SpeechConfig(
# #             subscription=os.getenv("AZURE_SPEECH_KEY"),
# #             region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
# #         )
# #         speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
# #         speech_config.set_speech_synthesis_output_format(
# #             speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
# #         )
# #         return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

# #     def _synthesize_ulaw(self, text: str, language: str = None) -> bytes:
# #         lang = language or self.language
# #         ssml = build_ssml(text, lang)

# #         if lang != self.language:
# #             speech_config = speechsdk.SpeechConfig(
# #                 subscription=os.getenv("AZURE_SPEECH_KEY"),
# #                 region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
# #             )
# #             speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
# #             speech_config.set_speech_synthesis_output_format(
# #                 speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
# #             )
# #             synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
# #             result = synthesizer.speak_ssml_async(ssml).get()
# #         else:
# #             result = self._tts_synthesizer.speak_ssml_async(ssml).get()

# #         if result.reason == speechsdk.ResultReason.Canceled:
# #             details = result.cancellation_details
# #             print("❌ TTS Canceled:", details.reason, details.error_details)
# #             return b""

# #         pcm = result.audio_data
# #         pcm = strip_wav_header(pcm)

# #         if len(pcm) % 2 != 0:
# #             pcm = pcm[:-1]

# #         return encode_g711(pcm)

# #     async def _stream_ulaw(self, ulaw: bytes):
# #         if not ulaw:
# #             return

# #         loop = asyncio.get_event_loop()

# #         for _ in range(3):
# #             if not self.is_bot_speaking:
# #                 return
# #             await self._send_media_frame(SILENCE_FRAME)
# #             await asyncio.sleep(0.020)

# #         start_time = loop.time()
# #         for idx, i in enumerate(range(0, len(ulaw), 160)):
# #             if not self.is_bot_speaking:
# #                 print("🛑 TTS stopped mid-stream")
# #                 return

# #             chunk = ulaw[i:i + 160].ljust(160, b'\x7f')
# #             await self._send_media_frame(chunk)

# #             target_time = start_time + (idx + 1) * 0.020
# #             sleep_duration = target_time - loop.time()
# #             if sleep_duration > 0:
# #                 await asyncio.sleep(sleep_duration)

# #         for _ in range(3):
# #             if not self.is_bot_speaking:
# #                 return
# #             await self._send_media_frame(SILENCE_FRAME)
# #             await asyncio.sleep(0.020)

# #     async def _send_media_frame(self, chunk: bytes):
# #         payload = base64.b64encode(chunk).decode()
# #         msg = {"event": "media", "media": {"payload": payload}}
# #         if self.stream_sid:
# #             msg["streamSid"] = self.stream_sid
# #         await self.send(text_data=json.dumps(msg))

# #     async def send_tts(self, text, tts_language: str = None):
# #         self.is_bot_speaking = True
# #         loop = asyncio.get_event_loop()
# #         lang = tts_language or self.language

# #         try:
# #             sentences = split_into_sentences(text)
# #             audio_queue = asyncio.Queue()

# #             async def producer():
# #                 for sentence in sentences:
# #                     if not self.is_bot_speaking:
# #                         break
# #                     try:
# #                         ulaw = await asyncio.wait_for(
# #                             loop.run_in_executor(
# #                                 None,
# #                                 lambda s=sentence, l=lang: self._synthesize_ulaw(s, l)
# #                             ),
# #                             timeout=15
# #                         )
# #                     except asyncio.TimeoutError:
# #                         print(f"❌ TTS TIMEOUT: {sentence[:40]}")
# #                         ulaw = b""
# #                     await audio_queue.put(ulaw)
# #                 await audio_queue.put(None)

# #             async def consumer():
# #                 while True:
# #                     ulaw = await audio_queue.get()
# #                     if ulaw is None:
# #                         break
# #                     if not self.is_bot_speaking:
# #                         break
# #                     await self._stream_ulaw(ulaw)

# #             producer_task = asyncio.create_task(producer())
# #             consumer_task = asyncio.create_task(consumer())
# #             await asyncio.gather(producer_task, consumer_task)

# #         except asyncio.CancelledError:
# #             print("🛑 TTS CANCELLED")
# #             raise

# #         except Exception as e:
# #             print("❌ TTS ERROR:", e)

# #         finally:
# #             self.is_bot_speaking = False

# #     # ================= DISCONNECT =================

# #     async def disconnect(self, close_code):
# #         print("🔌 DISCONNECTED:", close_code)
# #         self.is_connected = False

# #         if hasattr(self, "keepalive_task"):
# #             self.keepalive_task.cancel()
# #             try:
# #                 await self.keepalive_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if hasattr(self, "final_consumer_task"):
# #             self.final_consumer_task.cancel()
# #             try:
# #                 await self.final_consumer_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if self.tts_task and not self.tts_task.done():
# #             self.tts_task.cancel()
# #             try:
# #                 await self.tts_task
# #             except asyncio.CancelledError:
# #                 pass

# #         if hasattr(self, "recognizer"):
# #             try:
# #                 self.recognizer.stop_continuous_recognition_async()
# #             except Exception:
# #                 pass

# #         if hasattr(self, "push_stream"):
# #             try:
# #                 self.push_stream.close()
# #             except Exception:
# #                 pass

# #         if hasattr(self, "conversation"):
# #             await close_conversation(self.conversation)
























# from urllib.parse import parse_qs
# import audioop
# from asgiref.sync import sync_to_async
# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from conversations.services.core.dialogue_engine import process_message, prepare_streaming, finalize_streaming, get_agent_tts_language
# from conversations.services.azure_openai_service import generate_response_streaming
# from conversations.services.speech_service import create_speech_recognizer
# from conversations.services.translator_service import translate_text
# import asyncio
# import os
# import azure.cognitiveservices.speech as speechsdk
# import time
# import base64
# import uuid
# import numpy as np
# import re
# from django.utils import timezone

# from agents.models import VoiceAgent
# from conversations.models import Conversation, Message, LeadAnalysis





# _GREETING_AUDIO_CACHE: dict = {}  # agent_id → bytes





# # ================= DATABASE =================

# @sync_to_async
# def create_conversation(agent_id, session_id, user_number):
#     conv = Conversation.objects.create(
#         agent_id=agent_id,
#         session_id=session_id,
#         user_number=user_number
#     )
#     # Create immediate LeadAnalysis record so it shows on dashboard instantly
#     LeadAnalysis.objects.create(
#         conversation=conv,
#         agent_id=agent_id,
#         lead_level="cold",  # Default level for new/short calls
#         summary="Call started..."
#     )
#     return conv


# @sync_to_async
# def save_message(conversation, role, text):
#     last = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
#     if last and last.text.strip() == text.strip() and last.role == role:
#         return
#     Message.objects.create(conversation=conversation, role=role, text=text)


# @sync_to_async
# def update_user_number(conversation, number):
#     conversation.user_number = number
#     conversation.save()


# @sync_to_async
# def save_stream_sid(conversation, stream_sid):
#     """Save the telecom's streamSid to the conversation for CDR matching."""
#     conversation.stream_sid = stream_sid
#     conversation.save(update_fields=["stream_sid"])


# @sync_to_async
# def close_conversation(conversation):
#     conversation.ended_at = timezone.now()
#     conversation.save()


# @sync_to_async
# def get_agent_summary(agent_id, agent_tts_lang="en"):
#     try:
#         agent = VoiceAgent.objects.get(id=agent_id)
#         company = agent.company_name or "our company"
#         summary = agent.summary.strip().rstrip(".") if agent.summary else ""

#         if agent_tts_lang == "gu":
#             if summary:
#                 return f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. {summary}"
#             return f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. મિલકત ખરીદવી, વેચવી, ભાડે આપવી કે રોકાણ — કોઈ પણ બાબતમાં મદદ જોઈએ તો કહો!"

#         elif agent_tts_lang == "interview_en":
#             if summary:
#                 return f"Hello, I am {agent.name} from {company}. {summary}."
#             return f"Hello, I am {agent.name}."

#         else:
#             if summary:
#                 return f"Hello! Main {agent.name} bol rahi hoon {company} se. {summary}."
#             return f"Hello, Main {agent.name} bol rahi hoon {company} se. Aapne thode din pehle KIYA Seltos ke liye enquiry ki thi. kya aap abhi baat kar sakte hain?"

#     except VoiceAgent.DoesNotExist:
#         return "Hello, how can I assist you today?"


# @sync_to_async
# def mark_intro_shown(agent_id, session_id, language="hi"):
#     from conversations.models import ConversationSession
#     from agents.models import VoiceAgent
#     try:
#         agent = VoiceAgent.objects.get(id=agent_id)
#         session, _ = ConversationSession.objects.get_or_create(
#             agent=agent,
#             session_id=session_id
#         )
#         state = session.state or {}
#         state["intro_shown"] = True
#         state["detected_language"] = language
#         session.state = state
#         session.save()
#     except Exception as e:
#         print("❌ mark_intro_shown error:", e)


# # ================= AUDIO =================

# def decode_g711(ulaw):
#     return audioop.ulaw2lin(ulaw, 2)


# def encode_g711(pcm):
#     return audioop.lin2ulaw(pcm, 2)

# def _amplify_pcm(pcm: bytes, gain: float = 1.8) -> bytes:
#     """Amplify 16-bit PCM audio by gain factor with clipping protection."""
#     samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
#     samples = samples * gain
#     samples = np.clip(samples, -32768, 32767)
#     return samples.astype(np.int16).tobytes()


# def strip_wav_header(data: bytes) -> bytes:
#     if data[:4] != b'RIFF':
#         return data
#     offset = 12
#     while offset < len(data) - 8:
#         chunk_id = data[offset:offset + 4]
#         chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
#         if chunk_id == b'data':
#             return data[offset + 8:]
#         offset += 8 + chunk_size
#     return data[44:]


# SILENCE_FRAME = b'\x7f' * 160


# def split_into_sentences(text: str) -> list:
#     sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', text) if s.strip()]
#     return sentences if sentences else [text]


# def is_end_intent(text: str) -> bool:
#     text = text.lower().strip()
#     end_keywords = [
#         "bye", "goodbye", "ok bye", "okay bye",
#         "thank you", "thanks a lot",
#         "that's all", "no thanks", "call end",
#         "અلविदा",
#         "બાય", "આભાર"
#     ]
#     return any(keyword in text for keyword in end_keywords)


# def _normalize(text: str) -> str:
#     """Normalize text for deduplication: lowercase, strip punctuation/spaces."""
#     return re.sub(r'[^\w\s]', '', text.lower()).strip()


# def _is_duplicate_utterance(text_a: str, text_b: str) -> bool:
#     """
#     Returns True if two utterances are effectively the same.
#     Handles cases where Azure final adds punctuation/casing vs raw partial.
#     Also catches substring cases: partial 'haan bhai' vs final 'haan bhai karo'.
#     """
#     a = _normalize(text_a)
#     b = _normalize(text_b)
#     if not a or not b:
#         return False
#     # Exact match
#     if a == b:
#         return True
#     # One is a prefix/suffix of the other (partial vs final)
#     shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
#     if longer.startswith(shorter) or longer.endswith(shorter):
#         return True
#     # Word overlap > 80%
#     words_a = set(a.split())
#     words_b = set(b.split())
#     if not words_a or not words_b:
#         return False
#     overlap_longer = len(words_a & words_b) / max(len(words_a), len(words_b))
#     overlap_shorter = len(words_a & words_b) / min(len(words_a), len(words_b))
#     # If it's a 70% match of the longer one OR a 90% match of the shorter one (subset)
#     return overlap_longer >= 0.7 or overlap_shorter >= 0.9


# # ================= SSML BUILDER =================

# TTS_VOICE_MAP = {
#     "en": "en-IN-AartiNeural",
#     "hi": "hi-IN-AartiNeural",
#     "gu": "gu-IN-DhwaniNeural",
# }

# SSML_STYLE_MAP = {
#     "en": None,
#     "hi": None,
#     "gu": None,
# }

# SSML_PROSODY_MAP = {
#     "en": {"rate": "0%", "pitch": "0%", "volume": "0%"},
#     "hi": {"rate": "0%", "pitch": "0%", "volume": "0%"},
#     "gu": {"rate": "+10%", "pitch": "0%", "volume": "0%"},
# }   


# def _inject_english_lang_tags(text: str) -> str:
#     import re

#     def escape_xml(s):
#         return s.replace('&', '&amp;').replace('"', '&quot;')

#     def expand_if_acronym(word: str) -> str:
#         if re.match(r'^[A-Z][A-Z0-9]+$', word):
#             return ' '.join(word)
#         if re.match(r'^[A-Z]{2,}', word) and re.search(r'[-/0-9]', word):
#             parts = re.split(r'[-/]', word)
#             spelled = []
#             for part in parts:
#                 if re.match(r'^[A-Z0-9]+$', part):
#                     spelled.append(' '.join(part))
#                 else:
#                     spelled.append(part)
#             return ' '.join(spelled)
#         return word

#     pattern = re.compile(r'([A-Za-z][A-Za-z0-9.\-/]*)')
#     result = []
#     last_end = 0

#     for match in pattern.finditer(text):
#         start, end = match.start(), match.end()
#         gujarati_part = text[last_end:start]
#         if gujarati_part:
#             result.append(escape_xml(gujarati_part))
#         english_word = match.group(1)
#         expanded = expand_if_acronym(english_word)
#         result.append(f'<lang xml:lang="en-IN">{escape_xml(expanded)}</lang>')
#         last_end = end

#     remaining = text[last_end:]
#     if remaining:
#         result.append(escape_xml(remaining))

#     return ''.join(result)


# def build_ssml(text: str, language: str) -> str:
#     voice = TTS_VOICE_MAP.get(language, TTS_VOICE_MAP["en"])
#     style = SSML_STYLE_MAP.get(language)
#     prosody = SSML_PROSODY_MAP.get(language, SSML_PROSODY_MAP["en"])
#     lang_tag = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}.get(language, "en-IN")

#     if language == "gu":
#         text = text.replace('&', '&amp;')
#     else:
#         text = text.replace('&', '&amp;')
#         # Add natural pauses at punctuation
#         # text = re.sub(r'([।])', r'\1<break time="400ms"/>', text)
#         # text = re.sub(r'([?!])\s', r'\1<break time="350ms"/> ', text)

#     prosody_open = f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}" volume="{prosody.get("volume", "0%")}">'
#     prosody_close = '</prosody>'

#     if language != "gu":
#         # text = re.sub(
#         #     r'^(Hello|Hi|Namaste|Ji|Acha|Haan|Okay|Suniye|Bilkul),',
#         #     r'\1,<break time="300ms"/>',
#         #     text, flags=re.I
#         # )
#         # # Comma pauses — natural breath points
#         # text = re.sub(r',\s*(?!<break)', ', <break time="180ms"/>', text)
#         # # Question — slight pitch lift
#         # if text.rstrip().endswith("?"):
#         #     text = f'<prosody pitch="+2%">{text}</prosody>'
#         pass

#     if language == "gu":
#         inner = f'{prosody_open}{text}{prosody_close}'
#     # elif style:
#     #     inner = (
#     #         f'<mstts:express-as style="{style}" styledegree="1.2">'
#     #         f'{prosody_open}{text}{prosody_close}'
#     #         f'</mstts:express-as>'
#     #     )
#     # else:
#     #     inner = (
#     #         f'<mstts:express-as style="customerservice" styledegree="1.0">'
#     #         f'{prosody_open}{text}{prosody_close}'
#     #         f'</mstts:express-as>'
#     #     )
#     else:
#         inner = f'{prosody_open}{text}{prosody_close}'

#     return (
#         f'<speak version="1.0" '
#         f'xmlns="http://www.w3.org/2001/10/synthesis" '
#         f'xmlns:mstts="http://www.w3.org/2001/mstts" '
#         f'xml:lang="{lang_tag}">'
#         f'<voice name="{voice}">'
#         f'{inner}'
#         f'</voice>'
#         f'</speak>'
#     )


# # ================= CONSUMER =================

# class VoiceBotConsumer(AsyncWebsocketConsumer):

#     async def connect(self):
#         self.loop = asyncio.get_running_loop()

#         params = parse_qs(self.scope["query_string"].decode())
#         self.agent_id = params.get("agent_id", [None])[0]
#         # Prioritize 'phone' param (outbound auto-dialer) over 'from' header
#         self.user_number = params.get("phone", [None])[0] or params.get("from", ["unknown"])[0]
#         self.language = params.get("language", ["en"])[0]

#         if not self.agent_id:
#             await self.close()
#             return

#         self.session_id = str(uuid.uuid4())
#         self.conversation = await create_conversation(
#             self.agent_id, self.session_id, self.user_number
#         )

#         self.stream_sid = None

#         # ── STATE ──────────────────────────────────────────────
#         self.is_bot_speaking = False
#         self.is_connected = True
#         self.is_processing = False
#         self.partial_text = ""
#         self.final_text_queue = asyncio.Queue()

#         self.last_dispatched_text = ""
#         self.last_dispatch_time = 0.0

#         # ── BOT SPEECH TIMING ──────────────────────────────────
#         # Timestamps for when bot speech started and ended.
#         # Any Azure STT result recognised DURING bot speech is discarded —
#         # it means the user spoke over the bot and we don't want to process it.
#         self._bot_speaking_started_at = 0.0   # set every time is_bot_speaking → True
#         self._bot_speaking_ended_at = 0.0     # set every time is_bot_speaking → False
#         # Grace period (seconds) after bot stops speaking during which STT results
#         # are still treated as "spoken during bot turn" and discarded.
#         self._post_speech_grace = 0.05  # 50ms — tight enough since we gate silence not real audio
#         self.current_phase = "GREETING_REPLY"

#         # ── DUPLICATE PREVENTION ───────────────────────────────
#         # Tracks whether VAD partial-dispatch already fired for current utterance.
#         # When Azure final arrives, it checks this to avoid double-processing.
#         self._vad_dispatched_text = ""       # normalized text that VAD already sent to AI
#         self._vad_dispatched_time = 0.0      # when VAD dispatched it
#         self._azure_final_received_time = 0.0  # when Azure last fired recognized

#         # ── LOCKS & TASKS ──────────────────────────────────────
#         self.processing_lock = asyncio.Lock()
#         self.tts_task = None
#         self._tts_synthesizers = {}  # Cache synthesizers by language code

#         # ── AUDIO / VAD ────────────────────────────────────────
#         # self.jitter_buffer = []
#         # self.jitter_delay = 2

#         self.speech_active = False
#         self.silence_start_time = None

#         self.SPEECH_DETECT_RMS = 300   # 300 = catches quiet speech; VAD fires faster
#         self.SILENCE_TRIGGER_SEC = 0.2   # 200ms — fires VAD dispatch instantly after user stops talking
#         self.MIN_WORD_COUNT = 1

#         # Interrupt detection removed — user speech during bot speech is silently dropped

#         # ── STT SETUP ──────────────────────────────────────────
#         self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
#         self._setup_stt_callbacks()
#         self.recognizer.start_continuous_recognition_async()

#         # ── PRIME AZURE STT ────────────────────────────────────
#         # Write ~1 second of silence (50 frames × 20ms) immediately after
#         # starting the recognizer. This forces Azure to fully negotiate its
#         # internal WebSocket + model session NOW, so the first user utterance
#         # gets recognized instantly instead of paying a cold-start penalty.
#         _prime_frames = SILENCE_FRAME * 50
#         self.push_stream.write(_prime_frames)
#         # print("🔥 Azure STT session primed (50 silence frames)")

#         # ── TTS SYNTHESIZER ───────────────────────────────────
#         self._tts_synthesizer = self._build_tts_synthesizer()

#         await self.accept()

#         # Optimized startup: Single DB call for language, greeting, and state
#         @sync_to_async
#         def get_initial_call_data(agent_id, session_id, language):
#             from agents.models import VoiceAgent
#             from conversations.models import ConversationSession
#             from conversations.services.core.behavior_router import get_role_strategy
            
#             agent = VoiceAgent.objects.select_related('role_template').get(id=agent_id)
#             company = agent.company_name or "our company"
#             role_name = agent.role_template.role_name if agent.role_template else ""
#             strategy_key = get_role_strategy(role_name)
            
#             # 1. Determine TTS Lang
#             if strategy_key == "real_estate":
#                 tts_lang = "gu"
#             elif strategy_key == "interview_bot":
#                 tts_lang = "interview_en"
#             else:
#                 tts_lang = "en"
                
#             # 2. Get Opening Message
#             summary_txt = agent.summary.strip().rstrip(".") if agent.summary else ""
#             if tts_lang == "gu":
#                 greeting = f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. {summary_txt}" if summary_txt else f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. મિલકત ખરીદવી, વેચવી, ભાડે આપવી કે રોકાણ — કોઈ પણ બાબતમાં મદદ જોઈએ તો કહો!"
#             elif tts_lang == "interview_en":
#                 greeting = f"Hello, I am {agent.name}."
#             else:
#                 greeting = f"Hello! Main {agent.name} bol rahi hoon {company} se. {summary_txt}." if summary_txt else f"Hello, Main {agent.name} bol rahi hoon {company} se. Aapne thode din pehle, KIYA Seltos ke liye enquiry ki thi,  kya aap abhi baat kar sakte hain?"
            
#             # 3. Mark intro shown
#             session, _ = ConversationSession.objects.get_or_create(agent=agent, session_id=session_id)
#             state = session.state or {}
#             state["intro_shown"] = True
#             state["detected_language"] = language
#             session.state = state
#             session.save()
            
#             return tts_lang, greeting

#         # self.agent_tts_lang, greeting = await get_initial_call_data(self.agent_id, self.session_id, self.language)

#         # if self.agent_tts_lang == "gu":
#         #     asyncio.create_task(self.send_tts(greeting, tts_language="gu"))
#         # elif self.agent_tts_lang == "interview_en":
#         #     asyncio.create_task(self.send_tts(greeting, tts_language="en"))
#         # else:
#         #     asyncio.create_task(self.send_tts(greeting))

#         # self.final_consumer_task = asyncio.create_task(self._final_text_consumer())
#         # self.keepalive_task = asyncio.create_task(self._keepalive_loop())


#         # Kick off DB fetch and TTS cache-check IN PARALLEL
#         db_task = asyncio.create_task(get_initial_call_data(self.agent_id, self.session_id, self.language))

#         # While DB is running, check if we already have cached audio for this agent
#         cached_audio = _GREETING_AUDIO_CACHE.get(self.agent_id)

#         self.agent_tts_lang, greeting = await db_task

#         if cached_audio:
#             # ⚡ INSTANT: stream pre-synthesized bytes directly — zero TTS latency
#             print("⚡ Greeting served from audio cache (0ms TTS)")
#             self.tts_task = asyncio.create_task(self._stream_cached_greeting(cached_audio))
#         else:
#             # First call for this agent: synthesize and cache for future calls
#             tts_task_lang = "gu" if self.agent_tts_lang == "gu" else ("en" if self.agent_tts_lang == "interview_en" else None)
#             self.tts_task = asyncio.create_task(self._synthesize_and_cache_greeting(greeting, tts_task_lang))

#         self.final_consumer_task = asyncio.create_task(self._final_text_consumer())
#         self.keepalive_task = asyncio.create_task(self._keepalive_loop())

#     # ================= KEEPALIVE =================

#     async def _keepalive_loop(self):
#         while self.is_connected:
#             await asyncio.sleep(25)
#             if not self.is_connected:
#                 break
#             try:
#                 await self.send(text_data=json.dumps({"event": "ping"}))
#                 print("🏓 Keepalive ping sent")
#             except Exception as e:
#                 print(f"❌ Keepalive failed: {e}")
#                 break

#     # ================= STT CALLBACKS =================

#     def _setup_stt_callbacks(self):
#         def handle_recognizing(evt):
#             if self.is_bot_speaking:
#                 return
#             text = evt.result.text.strip() if evt.result.text else ""
#             if text:
#                 detected_lang = evt.result.properties.get(
#                     speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult
#                 )
#                 if detected_lang:
#                     lang_code = detected_lang.split("-")[0]
#                     if lang_code in ["en", "hi", "gu"] and not self.is_bot_speaking:
#                         # 🚨 Do NOT switch language while bot speaks — echo causes mis-detection
#                         self.loop.call_soon_threadsafe(self._set_language, lang_code)
            
#             self.loop.call_soon_threadsafe(self._set_partial, text)

#         def handle_recognized(evt):
#             # Capture recognition time immediately — used for bot-speech gating
#             recognised_at = time.time()

#             text = evt.result.text.strip() if evt.result.text else ""
#             if not text:
#                 return

#             self.partial_text = ""  # Clear any stale partial VAD text from this turn

#             detected_lang = evt.result.properties.get(
#                 speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
#             )
#             lang_code = detected_lang.split("-")[0] if detected_lang else "en"
#             # 🚨 BLOCK language switching while bot is speaking or within 600ms after it ends
#             # (bot audio echo can arrive late and falsely trigger a language switch)
#             post_speech_grace = 0.6
#             in_post_speech = (
#                 self._bot_speaking_ended_at > 0
#                 and (recognised_at - self._bot_speaking_ended_at) < post_speech_grace
#             )
#             if lang_code in ["en", "hi", "gu"] and not self.is_bot_speaking and not in_post_speech:
#                 self.loop.call_soon_threadsafe(self._set_language, lang_code)

#             print(f"✅ Azure FINAL [{detected_lang}]: {text}")

#             # ── GATE 1: Discard if recognised while bot was speaking ───────
#             # Azure STT keeps running even when we stop feeding audio — its
#             # internal buffer can still produce a result after bot speech ends.
#             # Any result timestamped inside [bot_started … bot_ended + grace]
#             # is the user talking OVER the bot; we must not process it.
#             if self._recognised_during_bot_speech(recognised_at):
#                 print(f"🚫 Azure FINAL discarded (recognised during bot speech): {text!r}")
#                 return

#             # Record when Azure fired so VAD path can check recency
#             self._azure_final_received_time = recognised_at

#             # ── GATE 2: Did VAD already dispatch this utterance? ───────────
#             if (
#                 self._vad_dispatched_text
#                 and (recognised_at - self._vad_dispatched_time) < 30.0
#                 and _is_duplicate_utterance(text, self._vad_dispatched_text)
#             ):
#                 print(f"⏭️ Azure FINAL suppressed (VAD already dispatched): {text!r}")
#                 self.loop.call_soon_threadsafe(self._clear_vad_dispatch)
#                 return

#             self.loop.call_soon_threadsafe(
#                 lambda: self.final_text_queue.put_nowait(text)
#             )

#         def handle_canceled(evt):
#             print("⚠️ STT Canceled:", evt.result.cancellation_details)

#         self.recognizer.recognizing.connect(handle_recognizing)
#         self.recognizer.recognized.connect(handle_recognized)
#         self.recognizer.canceled.connect(handle_canceled)

#     def _set_partial(self, text):
#         self.partial_text = text

#     def _set_language(self, lang_code):
#         # ⚡ STICKY REGIONAL LANGUAGE: Once the conversation has entered a regional language (Hindi or Gujarati),
#         # do NOT automatically switch back to English ('en'). Users frequently use English loanwords 
#         # (Hinglish/Gujlish) like "City mein", "Automatic car", which Azure STT detects as 'en-IN',
#         # but they still want the conversation to continue in their regional language.
#         if self.language in ["hi", "gu"] and lang_code == "en":
#             return

#         if self.language != lang_code:
#             # Only switch if we are NOT in the middle of processing (to avoid state corruption)
#             if not self.is_processing:
#                 print(f"🌐 Language switched to: {lang_code}")
#                 self.language = lang_code
#                 self._tts_synthesizer = self._build_tts_synthesizer()
#                 asyncio.ensure_future(self._save_detected_language(lang_code))

#     async def _save_detected_language(self, lang_code):
#         """Persist detected language to session state for prompt adaptation."""
#         try:
#             from conversations.models import ConversationSession
#             from agents.models import VoiceAgent
#             agent = await sync_to_async(VoiceAgent.objects.get)(id=self.agent_id)
#             session = await sync_to_async(
#                 lambda: ConversationSession.objects.filter(
#                     agent=agent, session_id=self.session_id
#                 ).first()
#             )()
#             if session:
#                 state = session.state or {}
#                 state["detected_language"] = lang_code
#                 session.state = state
#                 await sync_to_async(session.save)()
#                 print(f"💾 Language '{lang_code}' saved to session state")
#         except Exception as e:
#             print(f"❌ Save detected language error: {e}")

#     def _clear_vad_dispatch(self):
#         self._vad_dispatched_text = ""
#         self._vad_dispatched_time = 0.0

#     def _mark_bot_speaking_start(self):
#         """Call immediately before bot audio begins playing."""
#         self._bot_speaking_started_at = time.time()
#         self._bot_speaking_ended_at = 0.0
#         # Wipe any STT partial that was building before bot started — it's stale
#         self.partial_text = ""

#     def _mark_bot_speaking_end(self):
#         """Call immediately after bot audio finishes or is cancelled."""
#         self._bot_speaking_ended_at = time.time()
#         self.partial_text = ""  # ⚡ Clear partial text again to avoid stale dispatch
#         # Drain every STT result that arrived while bot was speaking — all stale
#         drained = 0
#         while not self.final_text_queue.empty():
#             try:
#                 self.final_text_queue.get_nowait()
#                 drained += 1
#             except asyncio.QueueEmpty:
#                 break
#         if drained:
#             print(f"🧹 Drained {drained} stale STT result(s) after bot speech")
#         # Clear partial too — Azure was hearing bot audio, not user
#         self.partial_text = ""

#     def _recognised_during_bot_speech(self, recognised_at: float) -> bool:
#         """
#         True if an Azure recognition arrived while the bot was speaking OR
#         within the post-speech grace window (self._post_speech_grace seconds).
#         recognised_at = time.time() captured inside handle_recognized callback.
#         """
#         if self._bot_speaking_started_at == 0.0:
#             return False
#         bot_finished = self._bot_speaking_ended_at if self._bot_speaking_ended_at else time.time()
#         grace_end = bot_finished + self._post_speech_grace
#         return self._bot_speaking_started_at <= recognised_at <= grace_end

#     # ================= FINAL TEXT CONSUMER =================

#     async def _final_text_consumer(self):
#         while self.is_connected:
#             try:
#                 text = await asyncio.wait_for(self.final_text_queue.get(), timeout=1.0)
#             except asyncio.TimeoutError:
#                 continue
#             except Exception:
#                 break

#             if not text:
#                 continue

#             if self.is_bot_speaking or self.is_processing:
#                 print("⏭️ Skipped (bot busy):", text)
#                 continue

#             normalized = _normalize(text)

#             # Check against last dispatched using fuzzy match
#             if self.last_dispatched_text and _is_duplicate_utterance(text, self.last_dispatched_text):
#                 # Only skip if dispatch was recent (within 4 seconds)
#                 if time.time() - self.last_dispatch_time < 4.0:
#                     print("⏭️ Duplicate skipped (final consumer):", text)
#                     continue

#             if time.time() - self.last_dispatch_time < 0.5:
#                 print("⏭️ Cooldown skip:", text)
#                 continue

#             if len(text.split()) < self.MIN_WORD_COUNT:
#                 print("⏭️ Too short:", text)
#                 continue

#             print("⚡ DISPATCHING TO AI (Azure final):", text)
#             self.last_dispatched_text = normalized
#             self.last_dispatch_time = time.time()
#             # Clear any stale VAD dispatch record since Azure final now owns this utterance
#             self._clear_vad_dispatch()
#             self.partial_text = ""

#             self.is_processing = True
#             try:
#                 async with self.processing_lock:
#                     await self.handle_ai_reply(text)
#             finally:
#                 self.is_processing = False

#     # ================= RECEIVE =================

#     async def receive(self, text_data=None, bytes_data=None):
#         if not text_data:
#             return

#         try:
#             data = json.loads(text_data)

#             if data.get("event") == "start":
#                 self.stream_sid = data["start"].get("streamSid")
#                 print(f"📡 streamSid captured: {self.stream_sid}")
#                 # Save stream_sid to DB for CDR matching
#                 if self.stream_sid:
#                     await save_stream_sid(self.conversation, self.stream_sid)
#                     print(f"💾 streamSid saved to DB for conversation {self.conversation.id}")
            
#             # --- TEST BACKDOOR ---
#             elif data.get("event") == "test_text":
#                 text = data.get("text", "")
#                 print(f"🧪 [TEST-MESSAGE]: {text}")
#                 await self.handle_ai_reply(text)
#                 try:
#                     # For outbound calls, 'calledNumber' is the customer.
#                     # 'callerNumber' is often the bot's DID.
#                     custom = data["start"].get("customParameters", {})
#                     number = custom.get("calledNumber") or custom.get("callerNumber")
                    
#                     # Only update if we don't have a valid number yet (like from URL params)
#                     if number and (self.user_number == "unknown" or not self.user_number):
#                         self.user_number = number
#                         await update_user_number(self.conversation, number)
#                 except Exception:
#                     pass

#             if data.get("event") == "media":
#                 await self._handle_audio_chunk(data)

#         except Exception as e:
#             print("❌ RECEIVE ERROR:", e)

#     async def _handle_audio_chunk(self, data):
#         payload = base64.b64decode(data["media"]["payload"])
#         pcm = decode_g711(payload)

#         # ── BOT SPEAKING GUARD ─────────────────────────────────
#         # While the bot is speaking, drop real user audio so we never
#         # dispatch or run VAD on it. However, we still write SILENCE
#         # frames to the Azure STT push stream so the session stays warm.
#         # Without this, Azure's recognition engine goes "cold" during the
#         # greeting and the first user utterance suffers a noticeable delay.
#         if self.is_bot_speaking:
#             self.push_stream.write(SILENCE_FRAME)
#             return

#         rms = audioop.rms(pcm, 2)

#         # Feed real audio to Azure STT (bot is silent)
#         self.push_stream.write(pcm)

#         # ── VAD PARTIAL-TEXT DISPATCH ──────────────────────────
#         if rms > self.SPEECH_DETECT_RMS:
#             self.speech_active = True
#             self.silence_start_time = None
#         else:
#             if self.speech_active:
#                 if self.silence_start_time is None:
#                     self.silence_start_time = time.time()
#                 elif time.time() - self.silence_start_time > self.SILENCE_TRIGGER_SEC:
#                     self.speech_active = False
#                     self.silence_start_time = None

#                     if (
#                         not self.is_bot_speaking
#                         and not self.is_processing
#                         and self.partial_text
#                     ):
#                         fallback_text = self.partial_text.strip()
#                         self.partial_text = ""

#                         if len(fallback_text.split()) < self.MIN_WORD_COUNT:
#                             return

#                         normalized = _normalize(fallback_text)

#                         # ── DEDUP: skip if already dispatched recently ─────
#                         if self.last_dispatched_text and _is_duplicate_utterance(fallback_text, self.last_dispatched_text):
#                             if time.time() - self.last_dispatch_time < 4.0:
#                                 print("⏭️ VAD duplicate skipped:", fallback_text)
#                                 return

#                         if time.time() - self.last_dispatch_time < 0.5:
#                             return

#                         # ── DEDUP: if Azure final arrived very recently for
#                         #    the same content, let Azure final handle it ─────
#                         if (time.time() - self._azure_final_received_time) < 0.5:
#                             print("⏭️ VAD skipped — Azure final just fired, letting it handle:", fallback_text)
#                             return

#                         print("⚡ FAST DISPATCH (partial VAD):", fallback_text)

#                         # Record that VAD dispatched this so Azure final can skip it
#                         self._vad_dispatched_text = normalized
#                         self._vad_dispatched_time = time.time()

#                         self.last_dispatched_text = normalized
#                         self.last_dispatch_time = time.time()
#                         self.is_processing = True
#                         try:
#                             async with self.processing_lock:
#                                 self.partial_text = "" # ⚡ Clear immediately after dispatch
#                                 await self.handle_ai_reply(fallback_text)
#                         finally:
#                             self.is_processing = False

#     # ================= (INTERRUPT DETECTION REMOVED) =================
#     # Barge-in / interruption detection has been intentionally removed.
#     # When the bot is speaking, all user audio is dropped at _handle_audio_chunk.
#     # After the bot finishes its full response, user speech is accepted normally.

#     # ================= STREAMING LLM BRIDGE =================

#     async def _stream_llm(self, system_prompt, user_message):
#         queue = asyncio.Queue()
#         loop = asyncio.get_event_loop()

#         def _run_streaming():
#             try:
#                 for chunk in generate_response_streaming(system_prompt, user_message):
#                     loop.call_soon_threadsafe(queue.put_nowait, chunk)
#             except Exception as e:
#                 print(f"❌ LLM Streaming error: {e}")
#             loop.call_soon_threadsafe(queue.put_nowait, None)

#         loop.run_in_executor(None, _run_streaming)

#         while True:
#             chunk = await queue.get()
#             if chunk is None:
#                 break
#             yield chunk

#     # ================= AI (STREAMING) =================

#     async def _stream_local_audio_file(self, filename):
#         """Read a local .raw audio file and stream it to the WebSocket."""
#         filename = filename.replace(".mp3", ".raw")
        
#         # Determine current language prefix (e.g., 'hi_', 'en_', 'gu_')
#         lang_prefix = f"{self.language}_"
#         if not filename.startswith(lang_prefix):
#             filename = f"{lang_prefix}{filename}"
            
#         file_path = os.path.join("mp3_responses", filename)
#         if not os.path.exists(file_path):
#             print(f"⚠️ Audio file not found: {file_path}")
#             return

#         print(f"🔊 [PLAYBACK]: Streaming {filename}...")
#         self.is_bot_speaking = True
#         self._bot_speaking_started_at = time.time()
        
#         try:
#             start_time = time.time()
#             bytes_sent = 0
#             with open(file_path, "rb") as f:
#                 while self.is_connected:
#                     # Read 160 bytes (20ms of u-law audio)
#                     chunk = f.read(160)
#                     if not chunk:
#                         break
                    
#                     # Encode to base64 for Twilio/Daphne
#                     payload = base64.b64encode(chunk).decode("utf-8")
#                     try:
#                         await self.send(json.dumps({
#                             "event": "media",
#                             "streamSid": self.stream_sid,
#                             "media": {"payload": payload}
#                         }))
#                     except Exception:
#                         break  # Stop streaming immediately if client disconnected
                    
#                     bytes_sent += len(chunk)
                    
#                     # Precise throttling based on clock (fixes Windows 20ms jitter)
#                     expected_time = bytes_sent / 8000.0
#                     actual_time = time.time() - start_time
#                     if expected_time > actual_time:
#                         await asyncio.sleep(expected_time - actual_time)
#         finally:
#             self.is_bot_speaking = False
#             self._bot_speaking_ended_at = time.time()
#             print(f"✅ [PLAYBACK]: Finished {filename}")

#     async def handle_ai_reply(self, text):
#         # ── STRICT BARGE-IN PREVENTION ──
#         # Completely ignore any user input received while the bot is speaking
#         if self.is_bot_speaking:
#             print(f"🔇 [BARGE-IN DISABLED]: Ignoring user input '{text}' because bot is speaking.")
#             return

#         pipeline_start = time.time()
#         text = text.strip()
#         if not text:
#             return

#         normalized = text.lower().strip()

#         # ── AUTOMOBILE INTENT ROUTER (FAST-PATH) ──────────────────
#         if AUTOMOBILE_MATCHER:
#             try:
#                 # 1. Initialize/Load current phase (Safe attribute check)
#                 current_phase = "GREETING_REPLY"
#                 try:
#                     # Try to get state from the conversation session
#                     from conversations.models import ConversationSession
#                     session = await sync_to_async(
#                         lambda: ConversationSession.objects.filter(session_id=self.session_id).first()
#                     )()
#                     if session and session.state:
#                         current_phase = session.state.get("current_phase", "GREETING_REPLY")
#                         self.current_phase = current_phase
#                 except:
#                     pass

#                 # 2. Check for semantic match (Fast-Path)
#                 match_result = AUTOMOBILE_MATCHER.find_match(text, current_phase=current_phase, threshold=0.70)

#                 if match_result["match_type"] != "NONE":
#                     intent_name = match_result['intent']['intent_name']
#                     print(f"⚡ [FAST-PATH]: Matched {intent_name} (Source: {match_result['match_type']})")
                    
#                     # 3. Handle State Transition (Persist to DB)
#                     next_phase = match_result.get("next_phase")
#                     if next_phase:
#                         try:
#                             session = await sync_to_async(
#                                 lambda: ConversationSession.objects.filter(session_id=self.session_id).first()
#                             )()
#                             if session:
#                                 state = session.state or {}
#                                 state["current_phase"] = next_phase
#                                 session.state = state
#                                 await sync_to_async(session.save)()
#                                 self.current_phase = next_phase
#                                 print(f"🔄 [PHASE UPDATE]: {current_phase} -> {next_phase}")
#                         except Exception as state_err:
#                             print(f"⚠️ State save failed: {state_err}")

#                     # 4. Record the turn in database
#                     await save_message(self.conversation, "user", text)
                    
#                     # 5. Play MP3/Raw Audio instantly
#                     mp3_filename = match_result["mp3"]
#                     raw_filename = mp3_filename.replace(".mp3", ".raw")
#                     await self._stream_local_audio_file(raw_filename)
                    
#                     # SUCCESS: Fast-Path handled the turn, we are done!
#                     return 

#                 else:
#                     print(f"🧠 [ROUTER]: No match for '{text}'. Falling back to original code behaviour (LLM/RAG).")

#             except Exception as e:
#                 print(f"❌ [ROUTER ERROR]: {e}. Continuing with original logic.")

#         # ── END INTENT ────────────────────────────────────────
#         if is_end_intent(normalized):
#             print("📴 END INTENT DETECTED:", text)

#             await save_message(self.conversation, "user", text)

#             if self.agent_tts_lang == "gu":
#                 farewell = "આપનો ખૂબ ખૂબ આભાર! જ્યારે પણ મિલકત વિશે કોઈ પ્રશ્ન હોય, અમે હંમેશા ઉપલબ્ધ છીએ. ધ્યાન રાખજો!"
#             elif self.agent_tts_lang == "interview_en":
#                 farewell = "Thank you for your time. All the best for your preparation!"
#             else:
#                 farewell = "Thank you for calling! Koi aur help chahiye toh zaroor call karna. Take care!"

#             await save_message(self.conversation, "bot", farewell)

#             if self.tts_task and not self.tts_task.done():
#                 self.tts_task.cancel()
#                 try:
#                     await self.tts_task
#                 except asyncio.CancelledError:
#                     pass

#             tts_lang_for_farewell = "gu" if self.agent_tts_lang == "gu" else "en"
#             await self.send_tts(farewell, tts_language=tts_lang_for_farewell)
#             await close_conversation(self.conversation)

#             await self.send(text_data=json.dumps({"event": "stop"}))

#             self.is_connected = False
#             await self.close()
#             return

#         # ── MAIN STREAMING PIPELINE ───────────────────────────
#         print("🧠 AI INPUT:", text)

#         t_prep = time.time()
#         _, prep_result = await asyncio.gather(
#             save_message(self.conversation, "user", text),
#             sync_to_async(prepare_streaming)(self.agent_id, text, self.session_id, detected_language=self.language, current_phase=self.current_phase)
#         )
#         prep_ms = round((time.time() - t_prep) * 1000)

#         tts_language = prep_result.get("tts_language", self.language)
#         skip_output_translation = prep_result.get("skip_output_translation", False)
#         skip_input_translation = prep_result.get("skip_input_translation", False)

#         t_translate_in = time.time()
#         message_for_ai = text
#         translate_input_to = prep_result.get("translate_input_to", None)

#         if skip_input_translation or translate_input_to == "original":
#             message_for_ai = text
#             print(f"⏩ Skipping input translation (using original: {self.language})")
#         elif translate_input_to == "gu":
#             if self.language != "gu":
#                 message_for_ai = await sync_to_async(translate_text)(
#                     text, from_lang=self.language, to_lang="gu"
#                 )
#                 print(f"🌐 [{self.language}→gu]: {message_for_ai}")
#         elif translate_input_to is None and self.language != "en":
#             message_for_ai = await sync_to_async(translate_text)(
#                 text, from_lang=self.language, to_lang="en"
#             )
#             print(f"🌐 [{self.language}→en]: {message_for_ai}")

#         translate_in_ms = round((time.time() - t_translate_in) * 1000)

#         # Step 3a: Static reply
#         if "static_reply" in prep_result:
#             reply = prep_result["static_reply"]
#             if not reply:
#                 return

#             reply_for_user = reply
#             if not skip_output_translation and self.language != "en":
#                 reply_for_user = await sync_to_async(translate_text)(
#                     reply, from_lang="en", to_lang=self.language
#                 )

#             total_ms = round((time.time() - pipeline_start) * 1000)
#             print(f"⏱ PIPELINE (static): prep={prep_ms}ms | TOTAL={total_ms}ms")

#             await save_message(self.conversation, "bot", reply_for_user)
#             print("🤖 BOT REPLY:", reply_for_user)

#             if self.tts_task and not self.tts_task.done():
#                 self.tts_task.cancel()
#                 try:
#                     await self.tts_task
#                 except asyncio.CancelledError:
#                     pass

#             self.tts_task = asyncio.create_task(
#                 self.send_tts(reply_for_user, tts_language=tts_language)
#             )

#             if prep_result.get("auto_disconnect"):
#                 print("📴 AUTO-DISCONNECT (static reply): Booking confirmed by user — ending call")
#                 await self.tts_task
#                 await close_conversation(self.conversation)
#                 await self.send(text_data=json.dumps({"event": "stop"}))
#                 self.is_connected = False
#                 await self.close()

#             return

#         # Step 3b: STREAMING LLM + PER-SENTENCE TTS
#         system_prompt = prep_result["system_prompt"]
#         user_message = prep_result["user_message"]

#         if not skip_input_translation and message_for_ai != text:
#             user_message = message_for_ai

#         if self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         self.is_bot_speaking = True
#         self._mark_bot_speaking_start()
#         t_llm = time.time()

#         audio_queue = asyncio.Queue()
#         full_response = ""
#         first_sentence_time = None

#         def _strip_disconnect_tags(text):
#             for t in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]", "[END_CALL]",
#                       "BOOKING_CONFIRMED", "NOT_INTERESTED", "LEAD_COMPLETE", "END_CALL"]:
#                 text = text.replace(t, "")
#             return text.replace("[", "").replace("]", "").strip()

#         async def streaming_producer():
#             nonlocal full_response, first_sentence_time
#             sentence_buffer = ""
#             loop = asyncio.get_event_loop()

#             async for chunk in self._stream_llm(system_prompt, user_message):
#                 if not self.is_bot_speaking:
#                     break
#                 full_response += chunk
#                 clean_chunk = chunk
#                 for _tag in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]", "[END_CALL]"]:
#                     clean_chunk = clean_chunk.replace(_tag, "")
#                 for _inner in ["BOOKING_CONFIRMED", "NOT_INTERESTED", "LEAD_COMPLETE", "END_CALL"]:
#                     clean_chunk = clean_chunk.replace(_inner, "")
#                 clean_chunk = clean_chunk.replace("[", "").replace("]", "")
#                 sentence_buffer += clean_chunk

#                 # if tts_language == "gu":
#                 #     boundary = re.search(r'[!?।]\s|[.]\s+(?=[A-Z\u0A80-\u0AFF])', sentence_buffer)
#                 # else:
#                 #     boundary = re.search(r'[.!?।]\s|[,;]\s+(?=\S)', sentence_buffer)

#                 if first_sentence_time is None:
#                     boundary = re.search(r'[,;।!?]|\.\s+', sentence_buffer)
#                 elif tts_language == "gu":
#                     boundary = re.search(r'[!?।]\s|[.]\s+(?=[A-Z\u0A80-\u0AFF])', sentence_buffer)
#                 else:
#                     boundary = re.search(r'[.!?।]\s|[,;]\s+(?=\S)', sentence_buffer)

#                 if boundary:
#                     sentence = sentence_buffer[:boundary.start() + 1].strip()
#                     sentence_buffer = sentence_buffer[boundary.end():]
#                     if sentence:
#                         if first_sentence_time is None:
#                             first_sentence_time = time.time()
#                             print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

#                         sentence = _strip_disconnect_tags(sentence)
#                         if not sentence:
#                             continue
                        
#                         # --- HUMAN RHYTHM LOGIC ---
#                         if self.language != "gu":
#                             # 1. Add a natural "thinking" pause after initial greetings or filler words
#                             tts_text = re.sub(r'^(Hello|Hi|Namaste|Ji|Acha|Haan|Okay|Suniye),', r'\1, <break time="250ms"/>', sentence, flags=re.I)
#                             # 2. Add subtle 'thinking' breaks at commas so Arjun doesn't rush like a robot
#                             tts_text = tts_text.replace(",", ", <break time='200ms'/>")
#                             # 3. Add a slight lift in pitch for questions
#                             if tts_text.endswith("?"):
#                                 tts_text = f"<prosody pitch='+3%'>{tts_text}</prosody>"
#                         else:
#                             # Keep Gujarati fast and direct as per existing settings
#                             tts_text = sentence

#                         try:
#                             ulaw = await asyncio.wait_for(
#                                 loop.run_in_executor(
#                                     None,
#                                     lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
#                                 ),
#                                 timeout=15
#                             )
#                             await audio_queue.put(ulaw)
#                         except asyncio.TimeoutError:
#                             print(f"❌ TTS timeout: {sentence[:40]}")

#             if sentence_buffer.strip() and self.is_bot_speaking:
#                 sentence = sentence_buffer.strip()
#                 if first_sentence_time is None:
#                     first_sentence_time = time.time()
#                     print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

#                 sentence = _strip_disconnect_tags(sentence)
#                 if not sentence:
#                     await audio_queue.put(None)
#                     return
                
#                 # --- HUMAN RHYTHM LOGIC ---
#                 if self.language != "gu":
#                     tts_text = re.sub(r'^(Hello|Hi|Namaste|Ji|Acha|Haan|Okay|Suniye),', r'\1, <break time="250ms"/>', sentence, flags=re.I)
#                     tts_text = tts_text.replace(",", ", <break time='200ms'/>")
#                     if tts_text.endswith("?"):
#                         tts_text = f"<prosody pitch='+3%'>{tts_text}</prosody>"
#                 else:
#                     tts_text = sentence

#                 try:
#                     ulaw = await asyncio.wait_for(
#                         loop.run_in_executor(
#                             None,
#                             lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
#                         ),
#                         timeout=15
#                     )
#                     await audio_queue.put(ulaw)
#                 except asyncio.TimeoutError:
#                     pass

#             await audio_queue.put(None)

#         async def streaming_consumer():
#             while True:
#                 ulaw = await audio_queue.get()
#                 if ulaw is None:
#                     break
#                 if not self.is_bot_speaking:
#                     break
#                 await self._stream_ulaw(ulaw)

#         producer_task = asyncio.create_task(streaming_producer())
#         consumer_task = asyncio.create_task(streaming_consumer())
#         self.tts_task = consumer_task

#         try:
#             await asyncio.gather(producer_task, consumer_task)
#         except asyncio.CancelledError:
#             print("🛑 STREAMING TTS CANCELLED")
#         except Exception as e:
#             print("❌ STREAMING ERROR:", e)
#         finally:
#             self.is_bot_speaking = False
#             self._mark_bot_speaking_end()

#         llm_ms = round((time.time() - t_llm) * 1000)
#         total_ms = round((time.time() - pipeline_start) * 1000)
#         print(f"⏱ STREAMING PIPELINE: translate_in={translate_in_ms}ms | prep={prep_ms}ms | LLM+TTS={llm_ms}ms | TOTAL={total_ms}ms")

#         if full_response:
#             await sync_to_async(finalize_streaming)(full_response, prep_result)

#         for _tag in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]", "[END_CALL]"]:
#             full_response = full_response.replace(_tag, "")
#         full_response = full_response.strip()

#         reply_for_user = full_response
#         if not skip_output_translation and self.language != "en" and full_response:
#             reply_for_user = await sync_to_async(translate_text)(
#                 full_response, from_lang="en", to_lang=self.language
#             )
#         if reply_for_user:
#             await save_message(self.conversation, "bot", reply_for_user)
#         print("🤖 BOT REPLY:", reply_for_user)

#         if prep_result.get("auto_disconnect"):
#             if prep_result.get("skip_name_collection"):
#                 print("📴 AUTO-DISCONNECT (insurance): Ending call immediately")
#                 await asyncio.sleep(1.5)
#                 await close_conversation(self.conversation)
#                 await self.send(text_data=json.dumps({"event": "stop"}))
#                 self.is_connected = False
#                 await self.close()
#                 return

#             print("📴 BOOKING CONFIRMED — LLM asked for name, waiting for user response")
#             state = prep_result.get("state", {})
#             session_obj = prep_result.get("session")
#             if state is not None and session_obj:
#                 state["name_collection_pending"] = True
#                 from conversations.services.core.strategies import save_session
#                 await sync_to_async(save_session)(session_obj, state)
#             return

#     # ================= TTS HELPERS =================


#     def _get_synthesizer(self, language: str):
#         """Reuses cached synthesizer or builds a new one if needed."""
#         if language in self._tts_synthesizers:
#             return self._tts_synthesizers[language]
            
#         synthesizer = self._build_tts_synthesizer(language)
#         # Pre-heat the connection to avoid handshake delay on first speak
#         try:
#             conn = speechsdk.Connection.from_speech_synthesizer(synthesizer)
#             conn.open(True)
#         except Exception as e:
#             print(f"⚠️ TTS Connection pre-heat failed: {e}")
            
#         self._tts_synthesizers[language] = synthesizer
#         return synthesizer

#     def _build_tts_synthesizer(self, language: str = None):
#         lang = language or self.language
#         speech_config = speechsdk.SpeechConfig(
#             subscription=os.getenv("AZURE_SPEECH_KEY"),
#             region=os.getenv("AZURE_SPEECH_REGION")
#         )
#         speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
#         speech_config.set_speech_synthesis_output_format(
#             speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#         )
#         # Latency optimization for TTS
#         speech_config.set_property_by_name("SpeechServiceResponse_RequestStreamingResponse", "true")
#         return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

#     def _synthesize_ulaw(self, text: str, language: str = None) -> bytes:
#         lang = language or self.language
#         ssml = build_ssml(text, lang)

#         # if lang != self.language:
#         #     speech_config = speechsdk.SpeechConfig(
#         #         subscription=os.getenv("AZURE_SPEECH_KEY"),
#         #         region=os.getenv("AZURE_SPEECH_REGION", "centralindia")
#         #     )
#         #     speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
#         #     speech_config.set_speech_synthesis_output_format(
#         #         speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#         #     )
#         #     synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
#         #     result = synthesizer.speak_ssml_async(ssml).get()
#         # else:
#         #     result = self._tts_synthesizer.speak_ssml_async(ssml).get()

#         # Use cached synthesizer
#         synthesizer = self._get_synthesizer(lang)
#         result = synthesizer.speak_ssml_async(ssml).get()

#         if result.reason == speechsdk.ResultReason.Canceled:
#             details = result.cancellation_details
#             print("❌ TTS Canceled:", details.reason, details.error_details)
#             return b""

#         pcm = result.audio_data
#         pcm = strip_wav_header(pcm)

#         if len(pcm) % 2 != 0:
#             pcm = pcm[:-1]

#         pcm = _amplify_pcm(pcm, gain=2.0)

#         return encode_g711(pcm)

#     async def _stream_ulaw(self, ulaw: bytes):
#         if not ulaw:
#             return

#         loop = asyncio.get_event_loop()

#         # for _ in range(2):
#         #     if not self.is_bot_speaking:
#         #         return
#         #     await self._send_media_frame(SILENCE_FRAME)
#         #     await asyncio.sleep(0.020)

#         start_time = loop.time()
#         for idx, i in enumerate(range(0, len(ulaw), 160)):
#             if not self.is_bot_speaking:
#                 print("🛑 TTS stopped mid-stream")
#                 return

#             chunk = ulaw[i:i + 160].ljust(160, b'\x7f')
#             await self._send_media_frame(chunk)

#             target_time = start_time + (idx + 1) * 0.020
#             sleep_duration = target_time - loop.time()
#             if sleep_duration > 0:
#                 await asyncio.sleep(sleep_duration)

#         # for _ in range(2):
#         #     if not self.is_bot_speaking:
#         #         return
#         #     await self._send_media_frame(SILENCE_FRAME)
#         #     await asyncio.sleep(0.020)

#     async def _send_media_frame(self, chunk: bytes):
#         payload = base64.b64encode(chunk).decode()
#         msg = {
#             "event": "media",
#             "media": {"payload": payload}
#         }
#         if self.stream_sid:
#             msg["streamSid"] = self.stream_sid
#         try:
#             await self.send(text_data=json.dumps(msg))
#         except Exception:
#             # Cleanly ignore disconnected protocol exceptions on user hangup
#             pass

#     # ================= TTS (static replies / intro) =================

#     async def _synthesize_and_cache_greeting(self, text: str, tts_language: str = None):
#         """
#         Check for a local 'greeting.raw' first. 
#         If it exists, play it instantly. Otherwise, synthesize and cache.
#         """
#         import os
#         local_greeting = os.path.join("mp3_responses", "greeting.raw")
#         if os.path.exists(local_greeting):
#             print(f"🚀 INSTANT GREETING: Found local file {local_greeting}")
#             with open(local_greeting, "rb") as f:
#                 ulaw = f.read()
#             await self._stream_cached_greeting(ulaw)
#             return

#         lang = tts_language or self.language
#         loop = asyncio.get_event_loop()
#         try:
#             ulaw = await asyncio.wait_for(
#                 loop.run_in_executor(None, lambda: self._synthesize_ulaw(text, lang)),
#                 timeout=15
#             )
#         except Exception as e:
#             print(f"❌ Greeting synthesis error: {e}")
#             ulaw = b""

#         if ulaw:
#             _GREETING_AUDIO_CACHE[self.agent_id] = ulaw
#             print(f"💾 Greeting audio cached for agent {self.agent_id} ({len(ulaw)} bytes)")

#         await self._stream_cached_greeting(ulaw)

#     async def _stream_cached_greeting(self, ulaw: bytes, **_):
#         """Stream pre-synthesized greeting bytes — zero Azure TTS round-trip."""
#         if not ulaw:
#             return
#         self.is_bot_speaking = True
#         self._mark_bot_speaking_start()
#         try:
#             await self._stream_ulaw(ulaw)
#         finally:
#             self.is_bot_speaking = False
#             self._mark_bot_speaking_end()















#     async def send_tts(self, text, tts_language: str = None):
#         self.is_bot_speaking = True
#         self._mark_bot_speaking_start()
#         loop = asyncio.get_event_loop()
#         lang = tts_language or self.language

#         try:
#             sentences = split_into_sentences(text)
#             audio_queue = asyncio.Queue()

#             async def producer():
#                 for i, sentence in enumerate(sentences):
#                     if not self.is_bot_speaking:
#                         break
#                     try:
#                         ulaw = await asyncio.wait_for(
#                             loop.run_in_executor(
#                                 None,
#                                 lambda s=sentence, l=lang: self._synthesize_ulaw(s, l)
#                             ),
#                             timeout=15
#                         )
#                     except asyncio.TimeoutError:
#                         print(f"❌ TTS TIMEOUT for sentence: {sentence[:40]}")
#                         ulaw = b""
#                     await audio_queue.put(ulaw)
#                     # Natural inter-sentence pause (skip after last sentence)
#                     if i < len(sentences) - 1 and ulaw:
#                         pause_frames = SILENCE_FRAME * 6  # ~120ms natural gap
#                         await audio_queue.put(pause_frames)
#                 await audio_queue.put(None)

#             async def consumer():
#                 while True:
#                     ulaw = await audio_queue.get()
#                     if ulaw is None:
#                         break
#                     if not self.is_bot_speaking:
#                         break
#                     await self._stream_ulaw(ulaw)

#             producer_task = asyncio.create_task(producer())
#             consumer_task = asyncio.create_task(consumer())

#             await asyncio.gather(producer_task, consumer_task)

#         except asyncio.CancelledError:
#             print("🛑 TTS CANCELLED")
#             raise
#         except Exception as e:
#             print("❌ TTS ERROR:", e)
#         finally:
#             self.is_bot_speaking = False
#             self._mark_bot_speaking_end()

#     # ================= DISCONNECT =================

#     async def disconnect(self, close_code):
#         print("🔌 DISCONNECTED:", close_code)
#         self.is_connected = False

#         if hasattr(self, "keepalive_task") and self.keepalive_task:
#             self.keepalive_task.cancel()
#             try:
#                 await self.keepalive_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "final_consumer_task") and self.final_consumer_task:
#             self.final_consumer_task.cancel()
#             try:
#                 await self.final_consumer_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "tts_task") and self.tts_task and not self.tts_task.done():
#             self.tts_task.cancel()
#             try:
#                 await self.tts_task
#             except asyncio.CancelledError:
#                 pass

#         if hasattr(self, "recognizer"):
#             try:
#                 self.recognizer.stop_continuous_recognition_async()
#             except Exception:
#                 pass

#         if hasattr(self, "push_stream"):
#             try:
#                 self.push_stream.close()
#             except Exception:
#                 pass

#         if hasattr(self, "conversation"):
#             await close_conversation(self.conversation)

#             conv_id = self.conversation.id
#             user_phone = self.user_number  # Capture phone for auto-dialer
            
#             import threading
#             def _run_lead_analysis():
#                 try:
#                     from conversations.services.lead_analyzer import analyze_lead
#                     analyze_lead(conv_id)
#                 except Exception as e:
#                     print(f"❌ Lead analysis background error: {e}")
                
#                 # 🔄 AUTO-DIALER FALLBACK: Trigger next call if campaign is active
#                 try:
#                     from bot.views import on_call_ended, _campaign_active
#                     if _campaign_active:
#                         print(f"🔄 AUTO-DIALER (disconnect fallback): Triggering next call for {user_phone}")
#                         on_call_ended(user_phone)
#                 except Exception as e:
#                     print(f"⚠️ Auto-dialer fallback error: {e}")

#             threading.Thread(target=_run_lead_analysis, daemon=True).start()
#             print("📊 Lead analysis started in background...")

            
            
            
            
            
            
            
            
            








from urllib.parse import parse_qs
import audioop
from asgiref.sync import sync_to_async
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from conversations.services.core.dialogue_engine import process_message, prepare_streaming, finalize_streaming, get_agent_tts_language
from conversations.services.azure_openai_service import generate_response_streaming
from conversations.services.speech_service import create_speech_recognizer
from conversations.services.translator_service import translate_text
import asyncio
import os
import azure.cognitiveservices.speech as speechsdk
import time
import base64
import uuid
import numpy as np
import re
from django.utils import timezone

from agents.models import VoiceAgent
from conversations.models import Conversation, Message, LeadAnalysis

# ================= ELEVENLABS IMPORTS =================
from elevenlabs.client import ElevenLabs
from elevenlabs.types.voice_settings import VoiceSettings
# import io
# from pydub import AudioSegment


_GREETING_AUDIO_CACHE: dict = {}  # agent_id → bytes


# ================= DATABASE =================

@sync_to_async
def create_conversation(agent_id, session_id, user_number):
    conv = Conversation.objects.create(
        agent_id=agent_id,
        session_id=session_id,
        user_number=user_number
    )
    # Create immediate LeadAnalysis record so it shows on dashboard instantly
    LeadAnalysis.objects.create(
        conversation=conv,
        agent_id=agent_id,
        lead_level="cold",  # Default level for new/short calls
        summary="Call started..."
    )
    return conv


@sync_to_async
def save_message(conversation, role, text):
    last = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
    if last and last.text.strip() == text.strip() and last.role == role:
        return
    Message.objects.create(conversation=conversation, role=role, text=text)


@sync_to_async
def update_user_number(conversation, number):
    conversation.user_number = number
    conversation.save()


@sync_to_async
def save_stream_sid(conversation, stream_sid):
    """Save the telecom's streamSid to the conversation for CDR matching."""
    conversation.stream_sid = stream_sid
    conversation.save(update_fields=["stream_sid"])


@sync_to_async
def close_conversation(conversation):
    conversation.ended_at = timezone.now()
    conversation.save()


@sync_to_async
def get_agent_summary(agent_id, agent_tts_lang="en"):
    try:
        agent = VoiceAgent.objects.get(id=agent_id)
        company = agent.company_name or "our company"
        summary = agent.summary.strip().rstrip(".") if agent.summary else ""

        if agent_tts_lang == "gu":
            if summary:
                return f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. {summary}"
            return f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. મિલકત ખરીદવી, વેચવી, ભાડે આપવી કે રોકાણ — કોઈ પણ બાબતમાં મદદ જોઈએ તો કહો!"

        elif agent_tts_lang == "interview_en":
            if summary:
                return f"Hello, I am {agent.name} from {company}. {summary}."
            return f"Hello, I am {agent.name}."

        else:
            if summary:
                return f"Hello! Main {agent.name} bol rahi hoon {company} se. {summary}."
            return f"Hello, Main {agent.name} bol rahi hoon {company} se. Aapne thode din pehle KIYA Seltos ke liye enquiry ki thi. kya aap abhi baat kar sakte hain?"

    except VoiceAgent.DoesNotExist:
        return "Hello, how can I assist you today?"


@sync_to_async
def mark_intro_shown(agent_id, session_id, language="hi"):
    from conversations.models import ConversationSession
    from agents.models import VoiceAgent
    try:
        agent = VoiceAgent.objects.get(id=agent_id)
        session, _ = ConversationSession.objects.get_or_create(
            agent=agent,
            session_id=session_id
        )
        state = session.state or {}
        state["intro_shown"] = True
        state["detected_language"] = language
        session.state = state
        session.save()
    except Exception as e:
        print("❌ mark_intro_shown error:", e)


# ================= AUDIO =================

def decode_g711(ulaw):
    return audioop.ulaw2lin(ulaw, 2)


def encode_g711(pcm):
    return audioop.lin2ulaw(pcm, 2)

# def _amplify_pcm(pcm: bytes, gain: float = 1.8) -> bytes:
#     """Amplify 16-bit PCM audio by gain factor with clipping protection."""
#     samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
#     samples = samples * gain
#     samples = np.clip(samples, -32768, 32767)
#     return samples.astype(np.int16).tobytes()

def _amplify_pcm(pcm: bytes, gain: float = 1.3) -> bytes:
    """Amplify 16-bit PCM with soft clipping to prevent distortion."""
    import numpy as np
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    samples = samples * gain
    # Soft clip instead of hard clip — reduces distortion on loud passages
    np.clip(samples, -32000, 32000, out=samples)
    return samples.astype(np.int16).tobytes()

def strip_wav_header(data: bytes) -> bytes:
    if data[:4] != b'RIFF':
        return data
    offset = 12
    while offset < len(data) - 8:
        chunk_id = data[offset:offset + 4]
        chunk_size = int.from_bytes(data[offset + 4:offset + 8], 'little')
        if chunk_id == b'data':
            return data[offset + 8:]
        offset += 8 + chunk_size
    return data[44:]


SILENCE_FRAME = b'\x7f' * 160


def split_into_sentences(text: str) -> list:
    sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', text) if s.strip()]
    return sentences if sentences else [text]


def is_end_intent(text: str) -> bool:
    text = text.lower().strip()
    end_keywords = [
        "bye", "goodbye", "ok bye", "okay bye",
        "thank you", "thanks a lot",
        "that's all", "no thanks", "call end",
        "અलविदा",
        "બાય", "આભાર"
    ]
    return any(keyword in text for keyword in end_keywords)


def _normalize(text: str) -> str:
    """Normalize text for deduplication: lowercase, strip punctuation/spaces."""
    return re.sub(r'[^\w\s]', '', text.lower()).strip()

def _is_duplicate_utterance(text_a: str, text_b: str) -> bool:
    """
    Returns True if two utterances are effectively the same.
    Handles cases where Azure final adds punctuation/casing vs raw partial.
    Also catches substring cases: partial 'haan bhai' vs final 'haan bhai karo'.
    """
    a = _normalize(text_a)
    b = _normalize(text_b)
    if not a or not b:
        return False
    # Exact match
    if a == b:
        return True
    # One is a prefix/suffix of the other (partial vs final)
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if longer.startswith(shorter) or longer.endswith(shorter):
        return True
    # Word overlap > 80%
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return False
    overlap_longer = len(words_a & words_b) / max(len(words_a), len(words_b))
    overlap_shorter = len(words_a & words_b) / min(len(words_a), len(words_b))
    # If it's a 70% match of the longer one OR a 90% match of the shorter one (subset)
    return overlap_longer >= 0.7 or overlap_shorter >= 0.9


# ================= AZURE SSML (kept for STT — NOT used for TTS anymore) =================

TTS_VOICE_MAP = {
    "en": "en-IN-AartiNeural",
    "hi": "hi-IN-AartiNeural",
    "gu": "gu-IN-DhwaniNeural",
}

SSML_STYLE_MAP = {
    "en": None,
    "hi": None,
    "gu": None,
}

SSML_PROSODY_MAP = {
    "en": {"rate": "0%", "pitch": "0%", "volume": "0%"},
    "hi": {"rate": "0%", "pitch": "0%", "volume": "0%"},
    "gu": {"rate": "+10%", "pitch": "0%", "volume": "0%"},
}


# ================= ELEVENLABS CONFIG =================

# ElevenLabs Voice IDs — change these to swap voices
# Find more voices at: https://elevenlabs.io/voice-library
ELEVENLABS_VOICES = {

    "kanika":   "aSFxChEgBmCyExpaDqHd",
    "gaia":     "4Mhjd1Q9JRWcKfDQvn26",
    "hetalben": "1wX3DrX9Q7x2fkeiljyg",   # Custom Female Voice (Hetalben) ⭐
    "aria":     "9BWtsMINqrJLrRacOk9x",    # Female Indian English
    "rachel":   "21m00Tcm4TlvDq8ikWAM",    # Female US English (Natural)
    "bella":    "EXAVITQu4vr4xnSDxMaL",    # Female US English (Warm)
    "adam":     "pNInz6obpgDQGcFmaJgB",    # Male US English (Clear, Deep)
}

# Which voice to use per language — edit here to change voices easily
ELEVENLABS_VOICE_MAP = {
    "en": ELEVENLABS_VOICES["kanika"],
    "hi": ELEVENLABS_VOICES["kanika"],
    "gu": ELEVENLABS_VOICES["kanika"],
}

# Initialize ElevenLabs client (reads ELEVENLABS_API_KEY from .env)
ELEVENLABS_CLIENT = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))


# ================= CONSUMER =================

class VoiceBotConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.loop = asyncio.get_running_loop()

        params = parse_qs(self.scope["query_string"].decode())
        self.agent_id = params.get("agent_id", [None])[0]
        # Prioritize 'phone' param (outbound auto-dialer) over 'from' header
        self.user_number = params.get("phone", [None])[0] or params.get("from", ["unknown"])[0]
        self.language = params.get("language", ["en"])[0]

        if not self.agent_id:
            await self.close()
            return

        self.session_id = str(uuid.uuid4())
        self.conversation = await create_conversation(
            self.agent_id, self.session_id, self.user_number
        )

        self.stream_sid = None

        # ── STATE ──────────────────────────────────────────────
        self.is_bot_speaking = False
        self.is_connected = True
        self.is_processing = False
        self.partial_text = ""
        self.final_text_queue = asyncio.Queue()

        self.last_dispatched_text = ""
        self.last_dispatch_time = 0.0

        # ── BOT SPEECH TIMING ──────────────────────────────────
        self._bot_speaking_started_at = 0.0
        self._bot_speaking_ended_at = 0.0
        self._post_speech_grace = 0.05  # 50ms
        self.current_phase = "GREETING_REPLY"

        # ── DUPLICATE PREVENTION ───────────────────────────────
        self._vad_dispatched_text = ""
        self._vad_dispatched_time = 0.0
        self._azure_final_received_time = 0.0

        # ── LOCKS & TASKS ──────────────────────────────────────
        self.processing_lock = asyncio.Lock()
        self.tts_task = None
        # NOTE: No Azure TTS synthesizer needed — using ElevenLabs

        # ── AUDIO / VAD ────────────────────────────────────────
        self.speech_active = False
        self.silence_start_time = None

        self.SPEECH_DETECT_RMS = 300
        self.SILENCE_TRIGGER_SEC = 0.2
        self.MIN_WORD_COUNT = 1

        # ── STT SETUP (Azure STT still used for speech recognition) ──
        self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
        self._setup_stt_callbacks()
        self.recognizer.start_continuous_recognition_async()

        # ── PRIME AZURE STT ────────────────────────────────────
        _prime_frames = SILENCE_FRAME * 50
        self.push_stream.write(_prime_frames)

        await self.accept()

        # Optimized startup: Single DB call for language, greeting, and state
        @sync_to_async
        def get_initial_call_data(agent_id, session_id, language):
            from agents.models import VoiceAgent
            from conversations.models import ConversationSession
            from conversations.services.core.behavior_router import get_role_strategy

            agent = VoiceAgent.objects.select_related('role_template').get(id=agent_id)
            company = agent.company_name or "our company"
            role_name = agent.role_template.role_name if agent.role_template else ""
            strategy_key = get_role_strategy(role_name)

            # 1. Determine TTS Lang
            if strategy_key == "real_estate":
                tts_lang = "gu"
            elif strategy_key == "interview_bot":
                tts_lang = "interview_en"
            else:
                tts_lang = "en"

            # 2. Get Opening Message
            summary_txt = agent.summary.strip().rstrip(".") if agent.summary else ""
            if tts_lang == "gu":
                greeting = f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. {summary_txt}" if summary_txt else f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. મિલકત ખરીદવી, વેચવી, ભાડે આપવી કે રોકાણ — કોઈ પણ બાબતમાં મદદ જોઈએ તો કહો!"
            elif tts_lang == "interview_en":
                greeting = f"Hello, I am {agent.name}."
            else:
                greeting = f"Hello! Main {agent.name} bol rahi hoon {company} se. {summary_txt}." if summary_txt else f"Hello, Main {agent.name} bol rahi hoon {company} se. Aapne thode din pehle, KIYA Seltos ke liye enquiry ki thi,  kya aap abhi baat kar sakte hain?"

            # 3. Mark intro shown
            session, _ = ConversationSession.objects.get_or_create(agent=agent, session_id=session_id)
            state = session.state or {}
            state["intro_shown"] = True
            state["detected_language"] = language
            session.state = state
            session.save()

            return tts_lang, greeting

        # Kick off DB fetch and TTS cache-check IN PARALLEL
        db_task = asyncio.create_task(get_initial_call_data(self.agent_id, self.session_id, self.language))

        # While DB is running, check if we already have cached audio for this agent
        cached_audio = _GREETING_AUDIO_CACHE.get(self.agent_id)

        self.agent_tts_lang, greeting = await db_task

        if cached_audio:
            print("⚡ Greeting served from audio cache (0ms TTS)")
            self.tts_task = asyncio.create_task(self._stream_cached_greeting(cached_audio))
        else:
            tts_task_lang = "gu" if self.agent_tts_lang == "gu" else ("en" if self.agent_tts_lang == "interview_en" else None)
            self.tts_task = asyncio.create_task(self._synthesize_and_cache_greeting(greeting, tts_task_lang))

        self.final_consumer_task = asyncio.create_task(self._final_text_consumer())
        self.keepalive_task = asyncio.create_task(self._keepalive_loop())

    # ================= KEEPALIVE =================

    async def _keepalive_loop(self):
        while self.is_connected:
            await asyncio.sleep(25)
            if not self.is_connected:
                break
            try:
                await self.send(text_data=json.dumps({"event": "ping"}))
                print("🏓 Keepalive ping sent")
            except Exception as e:
                print(f"❌ Keepalive failed: {e}")
                break

    # ================= STT CALLBACKS =================

    def _setup_stt_callbacks(self):
        def handle_recognizing(evt):
            if self.is_bot_speaking:
                return
            text = evt.result.text.strip() if evt.result.text else ""
            if text:
                detected_lang = evt.result.properties.get(
                    speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult
                )
                if detected_lang:
                    lang_code = detected_lang.split("-")[0]
                    if lang_code in ["en", "hi", "gu"] and not self.is_bot_speaking:
                        self.loop.call_soon_threadsafe(self._set_language, lang_code)

            self.loop.call_soon_threadsafe(self._set_partial, text)

        def handle_recognized(evt):
            recognised_at = time.time()

            text = evt.result.text.strip() if evt.result.text else ""
            if not text:
                return

            self.partial_text = ""

            detected_lang = evt.result.properties.get(
                speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
            )
            lang_code = detected_lang.split("-")[0] if detected_lang else "en"
            post_speech_grace = 0.6
            in_post_speech = (
                self._bot_speaking_ended_at > 0
                and (recognised_at - self._bot_speaking_ended_at) < post_speech_grace
            )
            if lang_code in ["en", "hi", "gu"] and not self.is_bot_speaking and not in_post_speech:
                self.loop.call_soon_threadsafe(self._set_language, lang_code)

            print(f"✅ Azure FINAL [{detected_lang}]: {text}")

            if self._recognised_during_bot_speech(recognised_at):
                print(f"🚫 Azure FINAL discarded (recognised during bot speech): {text!r}")
                return

            self._azure_final_received_time = recognised_at

            if (
                self._vad_dispatched_text
                and (recognised_at - self._vad_dispatched_time) < 30.0
                and _is_duplicate_utterance(text, self._vad_dispatched_text)
            ):
                print(f"⏭️ Azure FINAL suppressed (VAD already dispatched): {text!r}")
                self.loop.call_soon_threadsafe(self._clear_vad_dispatch)
                return

            self.loop.call_soon_threadsafe(
                lambda: self.final_text_queue.put_nowait(text)
            )

        def handle_canceled(evt):
            print("⚠️ STT Canceled:", evt.result.cancellation_details)

        self.recognizer.recognizing.connect(handle_recognizing)
        self.recognizer.recognized.connect(handle_recognized)
        self.recognizer.canceled.connect(handle_canceled)

    def _set_partial(self, text):
        self.partial_text = text

    def _set_language(self, lang_code):
        # Sticky regional language — don't switch back to English once in hi/gu
        if self.language in ["hi", "gu"] and lang_code == "en":
            return

        if self.language != lang_code:
            if not self.is_processing:
                print(f"🌐 Language switched to: {lang_code}")
                self.language = lang_code
                # No Azure TTS synthesizer to rebuild — ElevenLabs is stateless
                asyncio.ensure_future(self._save_detected_language(lang_code))

    async def _save_detected_language(self, lang_code):
        """Persist detected language to session state for prompt adaptation."""
        try:
            from conversations.models import ConversationSession
            from agents.models import VoiceAgent
            agent = await sync_to_async(VoiceAgent.objects.get)(id=self.agent_id)
            session = await sync_to_async(
                lambda: ConversationSession.objects.filter(
                    agent=agent, session_id=self.session_id
                ).first()
            )()
            if session:
                state = session.state or {}
                state["detected_language"] = lang_code
                session.state = state
                await sync_to_async(session.save)()
                print(f"💾 Language '{lang_code}' saved to session state")
        except Exception as e:
            print(f"❌ Save detected language error: {e}")

    def _clear_vad_dispatch(self):
        self._vad_dispatched_text = ""
        self._vad_dispatched_time = 0.0

    def _mark_bot_speaking_start(self):
        """Call immediately before bot audio begins playing."""
        self._bot_speaking_started_at = time.time()
        self._bot_speaking_ended_at = 0.0
        self.partial_text = ""

    def _mark_bot_speaking_end(self):
        """Call immediately after bot audio finishes or is cancelled."""
        self._bot_speaking_ended_at = time.time()
        self.partial_text = ""
        drained = 0
        while not self.final_text_queue.empty():
            try:
                self.final_text_queue.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
        if drained:
            print(f"🧹 Drained {drained} stale STT result(s) after bot speech")
        self.partial_text = ""

    def _recognised_during_bot_speech(self, recognised_at: float) -> bool:
        if self._bot_speaking_started_at == 0.0:
            return False
        bot_finished = self._bot_speaking_ended_at if self._bot_speaking_ended_at else time.time()
        grace_end = bot_finished + self._post_speech_grace
        return self._bot_speaking_started_at <= recognised_at <= grace_end

    # ================= FINAL TEXT CONSUMER =================

    async def _final_text_consumer(self):
        while self.is_connected:
            try:
                text = await asyncio.wait_for(self.final_text_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

            if not text:
                continue

            if self.is_bot_speaking or self.is_processing:
                print("⏭️ Skipped (bot busy):", text)
                continue

            normalized = _normalize(text)

            if self.last_dispatched_text and _is_duplicate_utterance(text, self.last_dispatched_text):
                if time.time() - self.last_dispatch_time < 4.0:
                    print("⏭️ Duplicate skipped (final consumer):", text)
                    continue

            if time.time() - self.last_dispatch_time < 0.5:
                print("⏭️ Cooldown skip:", text)
                continue

            if len(text.split()) < self.MIN_WORD_COUNT:
                print("⏭️ Too short:", text)
                continue

            print("⚡ DISPATCHING TO AI (Azure final):", text)
            self.last_dispatched_text = normalized
            self.last_dispatch_time = time.time()
            self._clear_vad_dispatch()
            self.partial_text = ""

            self.is_processing = True
            try:
                async with self.processing_lock:
                    await self.handle_ai_reply(text)
            finally:
                self.is_processing = False

    # ================= RECEIVE =================

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)

            if data.get("event") == "start":
                self.stream_sid = data["start"].get("streamSid")
                print(f"📡 streamSid captured: {self.stream_sid}")
                if self.stream_sid:
                    await save_stream_sid(self.conversation, self.stream_sid)
                    print(f"💾 streamSid saved to DB for conversation {self.conversation.id}")

            # --- TEST BACKDOOR ---
            elif data.get("event") == "test_text":
                text = data.get("text", "")
                print(f"🧪 [TEST-MESSAGE]: {text}")
                await self.handle_ai_reply(text)
                try:
                    custom = data["start"].get("customParameters", {})
                    number = custom.get("calledNumber") or custom.get("callerNumber")
                    if number and (self.user_number == "unknown" or not self.user_number):
                        self.user_number = number
                        await update_user_number(self.conversation, number)
                except Exception:
                    pass

            if data.get("event") == "media":
                await self._handle_audio_chunk(data)

        except Exception as e:
            print("❌ RECEIVE ERROR:", e)

    async def _handle_audio_chunk(self, data):
        payload = base64.b64decode(data["media"]["payload"])
        pcm = decode_g711(payload)

        if self.is_bot_speaking:
            self.push_stream.write(SILENCE_FRAME)
            return

        rms = audioop.rms(pcm, 2)

        self.push_stream.write(pcm)

        if rms > self.SPEECH_DETECT_RMS:
            self.speech_active = True
            self.silence_start_time = None
        else:
            if self.speech_active:
                if self.silence_start_time is None:
                    self.silence_start_time = time.time()
                elif time.time() - self.silence_start_time > self.SILENCE_TRIGGER_SEC:
                    self.speech_active = False
                    self.silence_start_time = None

                    if (
                        not self.is_bot_speaking
                        and not self.is_processing
                        and self.partial_text
                    ):
                        fallback_text = self.partial_text.strip()
                        self.partial_text = ""

                        if len(fallback_text.split()) < self.MIN_WORD_COUNT:
                            return

                        normalized = _normalize(fallback_text)

                        if self.last_dispatched_text and _is_duplicate_utterance(fallback_text, self.last_dispatched_text):
                            if time.time() - self.last_dispatch_time < 4.0:
                                print("⏭️ VAD duplicate skipped:", fallback_text)
                                return

                        if time.time() - self.last_dispatch_time < 0.5:
                            return

                        if (time.time() - self._azure_final_received_time) < 0.5:
                            print("⏭️ VAD skipped — Azure final just fired, letting it handle:", fallback_text)
                            return

                        print("⚡ FAST DISPATCH (partial VAD):", fallback_text)

                        self._vad_dispatched_text = normalized
                        self._vad_dispatched_time = time.time()

                        self.last_dispatched_text = normalized
                        self.last_dispatch_time = time.time()
                        self.is_processing = True
                        try:
                            async with self.processing_lock:
                                self.partial_text = ""
                                await self.handle_ai_reply(fallback_text)
                        finally:
                            self.is_processing = False

    # ================= STREAMING LLM BRIDGE =================

    async def _stream_llm(self, system_prompt, user_message):
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _run_streaming():
            try:
                for chunk in generate_response_streaming(system_prompt, user_message):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except Exception as e:
                print(f"❌ LLM Streaming error: {e}")
            loop.call_soon_threadsafe(queue.put_nowait, None)

        loop.run_in_executor(None, _run_streaming)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    # ================= LOCAL AUDIO FILE STREAMING =================

    async def _stream_local_audio_file(self, filename):
        """Read a local .raw audio file and stream it to the WebSocket."""
        filename = filename.replace(".mp3", ".raw")

        lang_prefix = f"{self.language}_"
        if not filename.startswith(lang_prefix):
            filename = f"{lang_prefix}{filename}"

        file_path = os.path.join("mp3_responses", filename)
        if not os.path.exists(file_path):
            print(f"⚠️ Audio file not found: {file_path}")
            return

        print(f"🔊 [PLAYBACK]: Streaming {filename}...")
        self.is_bot_speaking = True
        self._bot_speaking_started_at = time.time()

        try:
            start_time = time.time()
            bytes_sent = 0
            with open(file_path, "rb") as f:
                while self.is_connected:
                    chunk = f.read(160)
                    if not chunk:
                        break
                    payload = base64.b64encode(chunk).decode("utf-8")
                    try:
                        await self.send(json.dumps({
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {"payload": payload}
                        }))
                    except Exception:
                        break
                    bytes_sent += len(chunk)
                    expected_time = bytes_sent / 8000.0
                    actual_time = time.time() - start_time
                    if expected_time > actual_time:
                        await asyncio.sleep(expected_time - actual_time)
        finally:
            self.is_bot_speaking = False
            self._bot_speaking_ended_at = time.time()
            print(f"✅ [PLAYBACK]: Finished {filename}")

    # ================= AI REPLY HANDLER =================

    async def handle_ai_reply(self, text):
        if self.is_bot_speaking:
            print(f"🔇 [BARGE-IN DISABLED]: Ignoring user input '{text}' because bot is speaking.")
            return

        pipeline_start = time.time()
        text = text.strip()
        if not text:
            return

        normalized = text.lower().strip()

        # ── AUTOMOBILE INTENT ROUTER (FAST-PATH) ──────────────────
        if AUTOMOBILE_MATCHER:
            try:
                current_phase = "GREETING_REPLY"
                try:
                    from conversations.models import ConversationSession
                    session = await sync_to_async(
                        lambda: ConversationSession.objects.filter(session_id=self.session_id).first()
                    )()
                    if session and session.state:
                        current_phase = session.state.get("current_phase", "GREETING_REPLY")
                        self.current_phase = current_phase
                except:
                    pass

                match_result = AUTOMOBILE_MATCHER.find_match(text, current_phase=current_phase, threshold=0.70)

                if match_result["match_type"] != "NONE":
                    intent_name = match_result['intent']['intent_name']
                    print(f"⚡ [FAST-PATH]: Matched {intent_name} (Source: {match_result['match_type']})")

                    next_phase = match_result.get("next_phase")
                    if next_phase:
                        try:
                            session = await sync_to_async(
                                lambda: ConversationSession.objects.filter(session_id=self.session_id).first()
                            )()
                            if session:
                                state = session.state or {}
                                state["current_phase"] = next_phase
                                session.state = state
                                await sync_to_async(session.save)()
                                self.current_phase = next_phase
                                print(f"🔄 [PHASE UPDATE]: {current_phase} -> {next_phase}")
                        except Exception as state_err:
                            print(f"⚠️ State save failed: {state_err}")

                    await save_message(self.conversation, "user", text)

                    mp3_filename = match_result["mp3"]
                    raw_filename = mp3_filename.replace(".mp3", ".raw")
                    await self._stream_local_audio_file(raw_filename)
                    return

                else:
                    print(f"🧠 [ROUTER]: No match for '{text}'. Falling back to LLM/RAG.")

            except Exception as e:
                print(f"❌ [ROUTER ERROR]: {e}. Continuing with original logic.")

        # ── END INTENT ────────────────────────────────────────
        if is_end_intent(normalized):
            print("📴 END INTENT DETECTED:", text)

            await save_message(self.conversation, "user", text)

            if self.agent_tts_lang == "gu":
                farewell = "આપનો ખૂબ ખૂબ આભાર! જ્યારે પણ મિલકત વિશે કોઈ પ્રશ્ન હોય, અમે હંમેશા ઉપલબ્ધ છીએ. ધ્યાન રાખજો!"
            elif self.agent_tts_lang == "interview_en":
                farewell = "Thank you for your time. All the best for your preparation!"
            else:
                farewell = "Thank you for calling! Koi aur help chahiye toh zaroor call karna. Take care!"

            await save_message(self.conversation, "bot", farewell)

            if self.tts_task and not self.tts_task.done():
                self.tts_task.cancel()
                try:
                    await self.tts_task
                except asyncio.CancelledError:
                    pass

            tts_lang_for_farewell = "gu" if self.agent_tts_lang == "gu" else "en"
            await self.send_tts(farewell, tts_language=tts_lang_for_farewell)
            await close_conversation(self.conversation)

            await self.send(text_data=json.dumps({"event": "stop"}))

            self.is_connected = False
            await self.close()
            return

        # ── MAIN STREAMING PIPELINE ───────────────────────────
        print("🧠 AI INPUT:", text)

        t_prep = time.time()
        _, prep_result = await asyncio.gather(
            save_message(self.conversation, "user", text),
            sync_to_async(prepare_streaming)(self.agent_id, text, self.session_id, detected_language=self.language, current_phase=self.current_phase)
        )
        prep_ms = round((time.time() - t_prep) * 1000)

        tts_language = prep_result.get("tts_language", self.language)
        skip_output_translation = prep_result.get("skip_output_translation", False)
        skip_input_translation = prep_result.get("skip_input_translation", False)

        t_translate_in = time.time()
        message_for_ai = text
        translate_input_to = prep_result.get("translate_input_to", None)

        if skip_input_translation or translate_input_to == "original":
            message_for_ai = text
            print(f"⏩ Skipping input translation (using original: {self.language})")
        elif translate_input_to == "gu":
            if self.language != "gu":
                message_for_ai = await sync_to_async(translate_text)(
                    text, from_lang=self.language, to_lang="gu"
                )
                print(f"🌐 [{self.language}→gu]: {message_for_ai}")
        elif translate_input_to is None and self.language != "en":
            message_for_ai = await sync_to_async(translate_text)(
                text, from_lang=self.language, to_lang="en"
            )
            print(f"🌐 [{self.language}→en]: {message_for_ai}")

        translate_in_ms = round((time.time() - t_translate_in) * 1000)

        # Step 3a: Static reply
        if "static_reply" in prep_result:
            reply = prep_result["static_reply"]
            if not reply:
                return

            reply_for_user = reply
            if not skip_output_translation and self.language != "en":
                reply_for_user = await sync_to_async(translate_text)(
                    reply, from_lang="en", to_lang=self.language
                )

            total_ms = round((time.time() - pipeline_start) * 1000)
            print(f"⏱ PIPELINE (static): prep={prep_ms}ms | TOTAL={total_ms}ms")

            await save_message(self.conversation, "bot", reply_for_user)
            print("🤖 BOT REPLY:", reply_for_user)

            if self.tts_task and not self.tts_task.done():
                self.tts_task.cancel()
                try:
                    await self.tts_task
                except asyncio.CancelledError:
                    pass

            self.tts_task = asyncio.create_task(
                self.send_tts(reply_for_user, tts_language=tts_language)
            )

            if prep_result.get("auto_disconnect"):
                print("📴 AUTO-DISCONNECT (static reply): Booking confirmed by user — ending call")
                await self.tts_task
                await close_conversation(self.conversation)
                await self.send(text_data=json.dumps({"event": "stop"}))
                self.is_connected = False
                await self.close()

            return

        # Step 3b: STREAMING LLM + PER-SENTENCE TTS
        system_prompt = prep_result["system_prompt"]
        user_message = prep_result["user_message"]

        if not skip_input_translation and message_for_ai != text:
            user_message = message_for_ai

        if self.tts_task and not self.tts_task.done():
            self.tts_task.cancel()
            try:
                await self.tts_task
            except asyncio.CancelledError:
                pass

        self.is_bot_speaking = True
        self._mark_bot_speaking_start()
        t_llm = time.time()

        audio_queue = asyncio.Queue()
        full_response = ""
        first_sentence_time = None

        def _strip_disconnect_tags(text):
            for t in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]", "[END_CALL]",
                      "BOOKING_CONFIRMED", "NOT_INTERESTED", "LEAD_COMPLETE", "END_CALL"]:
                text = text.replace(t, "")
            return text.replace("[", "").replace("]", "").strip()

        async def streaming_producer():
            nonlocal full_response, first_sentence_time
            sentence_buffer = ""
            loop = asyncio.get_event_loop()

            async for chunk in self._stream_llm(system_prompt, user_message):
                if not self.is_bot_speaking:
                    break
                full_response += chunk
                clean_chunk = chunk
                for _tag in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]", "[END_CALL]"]:
                    clean_chunk = clean_chunk.replace(_tag, "")
                for _inner in ["BOOKING_CONFIRMED", "NOT_INTERESTED", "LEAD_COMPLETE", "END_CALL"]:
                    clean_chunk = clean_chunk.replace(_inner, "")
                clean_chunk = clean_chunk.replace("[", "").replace("]", "")
                sentence_buffer += clean_chunk

                if first_sentence_time is None:
                    boundary = re.search(r'[,;।!?]|\.\s+', sentence_buffer)
                elif tts_language == "gu":
                    boundary = re.search(r'[!?।]\s|[.]\s+(?=[A-Z\u0A80-\u0AFF])', sentence_buffer)
                else:
                    boundary = re.search(r'[.!?।]\s|[,;]\s+(?=\S)', sentence_buffer)

                if boundary:
                    sentence = sentence_buffer[:boundary.start() + 1].strip()
                    sentence_buffer = sentence_buffer[boundary.end():]
                    if sentence:
                        if first_sentence_time is None:
                            first_sentence_time = time.time()
                            print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

                        sentence = _strip_disconnect_tags(sentence)
                        if not sentence:
                            continue

                        try:
                            ulaw = await asyncio.wait_for(
                                loop.run_in_executor(
                                    None,
                                    lambda s=sentence, l=tts_language: self._synthesize_ulaw(s, l)
                                ),
                                timeout=15
                            )
                            await audio_queue.put(ulaw)
                        except asyncio.TimeoutError:
                            print(f"❌ TTS timeout: {sentence[:40]}")

            if sentence_buffer.strip() and self.is_bot_speaking:
                sentence = sentence_buffer.strip()
                if first_sentence_time is None:
                    first_sentence_time = time.time()
                    print(f"⚡ First sentence ready in {round((first_sentence_time - t_llm) * 1000)}ms: {sentence[:60]}")

                sentence = _strip_disconnect_tags(sentence)
                if not sentence:
                    await audio_queue.put(None)
                    return

                try:
                    ulaw = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda s=sentence, l=tts_language: self._synthesize_ulaw(s, l)
                        ),
                        timeout=15
                    )
                    await audio_queue.put(ulaw)
                except asyncio.TimeoutError:
                    pass

            await audio_queue.put(None)

        async def streaming_consumer():
            while True:
                ulaw = await audio_queue.get()
                if ulaw is None:
                    break
                if not self.is_bot_speaking:
                    break
                await self._stream_ulaw(ulaw)

        producer_task = asyncio.create_task(streaming_producer())
        consumer_task = asyncio.create_task(streaming_consumer())
        self.tts_task = consumer_task

        try:
            await asyncio.gather(producer_task, consumer_task)
        except asyncio.CancelledError:
            print("🛑 STREAMING TTS CANCELLED")
        except Exception as e:
            print("❌ STREAMING ERROR:", e)
        finally:
            self.is_bot_speaking = False
            self._mark_bot_speaking_end()

        llm_ms = round((time.time() - t_llm) * 1000)
        total_ms = round((time.time() - pipeline_start) * 1000)
        print(f"⏱ STREAMING PIPELINE: translate_in={translate_in_ms}ms | prep={prep_ms}ms | LLM+TTS={llm_ms}ms | TOTAL={total_ms}ms")

        if full_response:
            await sync_to_async(finalize_streaming)(full_response, prep_result)

        for _tag in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]", "[END_CALL]"]:
            full_response = full_response.replace(_tag, "")
        full_response = full_response.strip()

        reply_for_user = full_response
        if not skip_output_translation and self.language != "en" and full_response:
            reply_for_user = await sync_to_async(translate_text)(
                full_response, from_lang="en", to_lang=self.language
            )
        if reply_for_user:
            await save_message(self.conversation, "bot", reply_for_user)
        print("🤖 BOT REPLY:", reply_for_user)

        if prep_result.get("auto_disconnect"):
            if prep_result.get("skip_name_collection"):
                print("📴 AUTO-DISCONNECT (insurance): Ending call immediately")
                await asyncio.sleep(1.5)
                await close_conversation(self.conversation)
                await self.send(text_data=json.dumps({"event": "stop"}))
                self.is_connected = False
                await self.close()
                return

            print("📴 BOOKING CONFIRMED — LLM asked for name, waiting for user response")
            state = prep_result.get("state", {})
            session_obj = prep_result.get("session")
            if state is not None and session_obj:
                state["name_collection_pending"] = True
                from conversations.services.core.strategies import save_session
                await sync_to_async(save_session)(session_obj, state)
            return

    # ================= ELEVENLABS TTS =================

    def _synthesize_ulaw(self, text: str, language: str = None) -> bytes:
            """
            Synthesize speech using ElevenLabs pcm_8000 format.
            NO pydub / NO ffmpeg / NO MP3 decode needed.
            Returns G.711 u-law bytes ready for Twilio streaming.
            """
            lang = language or self.language
            voice_id = ELEVENLABS_VOICE_MAP.get(lang, ELEVENLABS_VOICE_MAP["en"])

            try:
                audio_generator = ELEVENLABS_CLIENT.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id="eleven_multilingual_v2",
                    output_format="pcm_8000",  # ← Native 8kHz 16-bit mono PCM, no MP3
                    voice_settings=VoiceSettings(
                        stability=0.25,
                        similarity_boost=0.75,
                        style=0.50,
                        use_speaker_boost=True
                    )
                )

                # Collect all PCM bytes first — prevents jitter from uneven chunk arrival
                pcm = b"".join(chunk for chunk in audio_generator if chunk)

                if not pcm:
                    print("❌ ElevenLabs returned empty audio")
                    return b""

                # Ensure even byte length for 16-bit samples
                if len(pcm) % 2 != 0:
                    pcm = pcm[:-1]

                # Mild amplification — PCM is already clean, no compression artifacts
                pcm = _amplify_pcm(pcm, gain=1.3)

                # Encode to G.711 u-law for Twilio telephony
                ulaw = encode_g711(pcm)

                print(f"✅ ElevenLabs TTS: {len(text)} chars → {len(ulaw)} bytes u-law")
                return ulaw

            except Exception as e:
                print(f"❌ ElevenLabs TTS error: {e}")
                import traceback
                traceback.print_exc()
                return b""

    # ================= AUDIO STREAMING HELPERS =================

    async def _stream_ulaw(self, ulaw: bytes):
        if not ulaw:
            return

        loop = asyncio.get_event_loop()
        start_time = loop.time()

        for idx, i in enumerate(range(0, len(ulaw), 160)):
            if not self.is_bot_speaking:
                print("🛑 TTS stopped mid-stream")
                return

            chunk = ulaw[i:i + 160].ljust(160, b'\x7f')
            await self._send_media_frame(chunk)

            target_time = start_time + (idx + 1) * 0.020
            sleep_duration = target_time - loop.time()
            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration)

    async def _send_media_frame(self, chunk: bytes):
        payload = base64.b64encode(chunk).decode()
        msg = {
            "event": "media",
            "media": {"payload": payload}
        }
        if self.stream_sid:
            msg["streamSid"] = self.stream_sid
        try:
            await self.send(text_data=json.dumps(msg))
        except Exception:
            pass

    # ================= GREETING HELPERS =================

    async def _synthesize_and_cache_greeting(self, text: str, tts_language: str = None):
        """
        Check for a local 'greeting.raw' first.
        If found, play instantly. Otherwise synthesize via ElevenLabs and cache.
        """
        local_greeting = os.path.join("mp3_responses", "greeting.raw")
        if os.path.exists(local_greeting):
            print(f"🚀 INSTANT GREETING: Found local file {local_greeting}")
            with open(local_greeting, "rb") as f:
                ulaw = f.read()
            await self._stream_cached_greeting(ulaw)
            return

        lang = tts_language or self.language
        loop = asyncio.get_event_loop()
        try:
            ulaw = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._synthesize_ulaw(text, lang)),
                timeout=20  # ElevenLabs may take slightly longer than Azure on first call
            )
        except Exception as e:
            print(f"❌ Greeting synthesis error: {e}")
            ulaw = b""

        if ulaw:
            _GREETING_AUDIO_CACHE[self.agent_id] = ulaw
            print(f"💾 Greeting audio cached for agent {self.agent_id} ({len(ulaw)} bytes)")

        await self._stream_cached_greeting(ulaw)

    async def _stream_cached_greeting(self, ulaw: bytes, **_):
        """Stream pre-synthesized greeting bytes — zero ElevenLabs round-trip."""
        if not ulaw:
            return
        self.is_bot_speaking = True
        self._mark_bot_speaking_start()
        try:
            await self._stream_ulaw(ulaw)
        finally:
            self.is_bot_speaking = False
            self._mark_bot_speaking_end()

    # ================= TTS (static replies) =================

    async def send_tts(self, text, tts_language: str = None):
        self.is_bot_speaking = True
        self._mark_bot_speaking_start()
        loop = asyncio.get_event_loop()
        lang = tts_language or self.language

        try:
            sentences = split_into_sentences(text)
            audio_queue = asyncio.Queue()

            async def producer():
                for i, sentence in enumerate(sentences):
                    if not self.is_bot_speaking:
                        break
                    try:
                        ulaw = await asyncio.wait_for(
                            loop.run_in_executor(
                                None,
                                lambda s=sentence, l=lang: self._synthesize_ulaw(s, l)
                            ),
                            timeout=20
                        )
                    except asyncio.TimeoutError:
                        print(f"❌ TTS TIMEOUT for sentence: {sentence[:40]}")
                        ulaw = b""
                    await audio_queue.put(ulaw)
                    if i < len(sentences) - 1 and ulaw:
                        pause_frames = SILENCE_FRAME * 6  # ~120ms natural gap
                        await audio_queue.put(pause_frames)
                await audio_queue.put(None)

            async def consumer():
                while True:
                    ulaw = await audio_queue.get()
                    if ulaw is None:
                        break
                    if not self.is_bot_speaking:
                        break
                    await self._stream_ulaw(ulaw)

            producer_task = asyncio.create_task(producer())
            consumer_task = asyncio.create_task(consumer())

            await asyncio.gather(producer_task, consumer_task)

        except asyncio.CancelledError:
            print("🛑 TTS CANCELLED")
            raise
        except Exception as e:
            print("❌ TTS ERROR:", e)
        finally:
            self.is_bot_speaking = False
            self._mark_bot_speaking_end()

    # ================= DISCONNECT =================

    async def disconnect(self, close_code):
        print("🔌 DISCONNECTED:", close_code)
        self.is_connected = False

        if hasattr(self, "keepalive_task") and self.keepalive_task:
            self.keepalive_task.cancel()
            try:
                await self.keepalive_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, "final_consumer_task") and self.final_consumer_task:
            self.final_consumer_task.cancel()
            try:
                await self.final_consumer_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, "tts_task") and self.tts_task and not self.tts_task.done():
            self.tts_task.cancel()
            try:
                await self.tts_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, "recognizer"):
            try:
                self.recognizer.stop_continuous_recognition_async()
            except Exception:
                pass

        if hasattr(self, "push_stream"):
            try:
                self.push_stream.close()
            except Exception:
                pass

        if hasattr(self, "conversation"):
            await close_conversation(self.conversation)

            conv_id = self.conversation.id
            user_phone = self.user_number

            import threading
            def _run_lead_analysis():
                try:
                    from conversations.services.lead_analyzer import analyze_lead
                    analyze_lead(conv_id)
                except Exception as e:
                    print(f"❌ Lead analysis background error: {e}")

                try:
                    from bot.views import on_call_ended, _campaign_active
                    if _campaign_active:
                        print(f"🔄 AUTO-DIALER (disconnect fallback): Triggering next call for {user_phone}")
                        on_call_ended(user_phone)
                except Exception as e:
                    print(f"⚠️ Auto-dialer fallback error: {e}")

            threading.Thread(target=_run_lead_analysis, daemon=True).start()
            print("📊 Lead analysis started in background...")