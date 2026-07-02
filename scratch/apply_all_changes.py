# scratch/apply_all_changes.py

import os

files_to_update = [
    r"c:\Users\AYUSHI PATEL\Eleven_labs\Voice-Bot-SaaS\conversations\consumers.py",
    r"c:\Users\AYUSHI PATEL\Eleven_labs\Voice-Bot-SaaS\conversations\consumers_service2.py"
]

globals_code = """
GLOBAL_SARVAM_CACHE = {}
SARVAM_HTTP_SESSION = None

def get_sarvam_session():
    global SARVAM_HTTP_SESSION
    if SARVAM_HTTP_SESSION is None:
        import requests
        from urllib3.util import Retry
        from requests.adapters import HTTPAdapter
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(pool_connections=10, pool_maxsize=50, max_retries=retries))
        SARVAM_HTTP_SESSION = session
    return SARVAM_HTTP_SESSION
"""

prewarm_startup_code = """

# ── SERVER STARTUP PRE-WARMING FOR SAMSUNG LLM BOT ─────────────────────────
def prewarm_sarvam_cache_at_startup():
    import threading
    import time as t_mod
    import os
    import re
    import audioop

    def run_prewarm():
        # Wait 5 seconds for the server to boot up completely
        t_mod.sleep(5)
        
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
            return
            
        print("🔥 [PREWARM]: Asynchronously pre-warming Sarvam TTS cache for common Samsung LLM phrases...")
        
        session = get_sarvam_session()
        api_url = "https://api.sarvam.ai/text-to-speech/stream"
        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json"
        }
        
        phrases = [
            "બરાબર.",
            "ખૂબ સરસ.",
            "અરે વાહ.",
            "જી ચોક્કસ.",
            "સમજાયું.",
            "કોઈ વાંધો નહીં.",
            "આભાર.",
            "ઓકે.",
            "નમસ્તે! હું નીલ છું. હું વીટેક સેમસંગ કેફે તરફથી વાત કરી રહ્યો છું. તમે થોડા દિવસ પહેલા સેમસંગ પ્રોડક્ટ માટે રસ દર્શાવ્યો હતો એટલે કોલ કર્યો છે. શું તમારી સાથે બે મિનિટ વાત થઈ શકે?",
            "નમસ્તે! હું નાવ્યા છું. હું વીટેક સેમસંગ કેફે તરફથી વાત કરી રહ્યો છું. તમે થોડા દિવસ પહેલા સેમસંગ પ્રોડક્ટ માટે રસ દર્શાવ્યો હતો એટલે કોલ કર્યો છે. શું તમારી સાથે બે મિનિટ વાત થઈ શકે?"
        ]
        
        for text in phrases:
            clean_text = text.strip()
            target_lang = "gu-IN"
            speaker = "shubh"
            pace = 1.15
            temp = 0.85
            
            norm_text = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()।!?]', '', clean_text).lower().strip()
            cache_key = (norm_text, target_lang, speaker, pace, temp)
            
            payload = {
                "text": clean_text,
                "target_language_code": target_lang,
                "speaker": speaker,
                "model": "bulbul:v3",
                "pace": pace,
                "speech_sample_rate": 8000,
                "output_audio_codec": "mulaw",
                "enable_preprocessing": False,
                "temperature": temp
            }
            
            try:
                response = session.post(api_url, headers=headers, json=payload, timeout=15)
                if response.status_code == 200 and response.content:
                    # Check if this module runs transcoding to A-law
                    # We look at the filename of the target file using local scope check
                    is_service2 = "consumers_service2" in globals().get("__file__", "") or "consumers_service2" in run_prewarm.__globals__.get("__file__", "")
                    if is_service2:
                        pcm_bytes = audioop.ulaw2lin(response.content, 2)
                        alaw_bytes = audioop.lin2alaw(pcm_bytes, 2)
                        GLOBAL_SARVAM_CACHE[cache_key] = alaw_bytes
                    else:
                        GLOBAL_SARVAM_CACHE[cache_key] = response.content
                t_mod.sleep(1.0)
            except Exception as e:
                print(f"⚠️ [PREWARM ERROR]: Failed to prewarm '{clean_text[:20]}': {e}")
                
        print("✅ [PREWARM]: Samsung LLM phrases pre-warmed successfully!")

    threading.Thread(target=run_prewarm, daemon=True).start()

prewarm_sarvam_cache_at_startup()
"""

# Let's read, modify and write consumers.py
with open(files_to_update[0], "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add globals under timezone import
if "GLOBAL_SARVAM_CACHE" not in content:
    content = content.replace("from django.utils import timezone", "from django.utils import timezone\n" + globals_code)
    print("Added globals to consumers.py")

# 2. Update _synthesize_ulaw in consumers.py
target_synthesis_block = """            clean_text = re.sub(r'<[^>]*>', '', text).strip()
            if not clean_text:
                return b""
            target_lang = "hi-IN" if is_loan_hi else "gu-IN"
            speaker = "shubh" if is_loan_hi else "ishita"
            if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"]:
                speaker = "shubh"
            pace = 1.1 if is_loan_hi else (1.15 if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"] else 1)

            payload = {
                "text": clean_text,
                "target_language_code": target_lang,
                "speaker": speaker,
                "model": "bulbul:v3",
                "pace": pace,
                "speech_sample_rate": 8000,
                "output_audio_codec": "mulaw",
                "enable_preprocessing": False
            }
            if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"]:
                payload["temperature"] = 0.85
            
            try:
                import time as t_mod
                t_start = t_mod.time()
                print(f"🎙️ [SARVAM TTS START]: Synthesizing '{clean_text[:40]}' using speaker '{speaker}' with pace '{pace}'")
                response = requests.post(api_url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                print(f"🎙️ [SARVAM TTS SUCCESS]: Done in {round((t_mod.time() - t_start) * 1000)}ms")
                return response.content"""

replacement_synthesis_block = """            clean_text = re.sub(r'<[^>]*>', '', text).strip()
            if not clean_text:
                return b""
            target_lang = "hi-IN" if is_loan_hi else "gu-IN"
            speaker = "shubh" if is_loan_hi else "ishita"
            if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"]:
                speaker = "shubh"
            pace = 1.1 if is_loan_hi else (1.15 if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"] else 1)
            temp = 0.85 if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"] else None

            # Normalise clean_text for cache key
            norm_text = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()।!?]', '', clean_text).lower().strip()
            cache_key = (norm_text, target_lang, speaker, pace, temp)
            
            if cache_key in GLOBAL_SARVAM_CACHE:
                print(f"🎯 [SARVAM CACHE HIT]: Found pre-synthesized audio for '{clean_text[:40]}'")
                return GLOBAL_SARVAM_CACHE[cache_key]

            payload = {
                "text": clean_text,
                "target_language_code": target_lang,
                "speaker": speaker,
                "model": "bulbul:v3",
                "pace": pace,
                "speech_sample_rate": 8000,
                "output_audio_codec": "mulaw",
                "enable_preprocessing": False
            }
            if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"]:
                payload["temperature"] = 0.85
            
            try:
                import time as t_mod
                t_start = t_mod.time()
                print(f"🎙️ [SARVAM TTS START]: Synthesizing '{clean_text[:40]}' using speaker '{speaker}' with pace '{pace}'")
                response = get_sarvam_session().post(api_url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                print(f"🎙️ [SARVAM TTS SUCCESS]: Done in {round((t_mod.time() - t_start) * 1000)}ms")
                if response.content:
                    GLOBAL_SARVAM_CACHE[cache_key] = response.content
                return response.content"""

if target_synthesis_block in content:
    content = content.replace(target_synthesis_block, replacement_synthesis_block)
    print("Updated _synthesize_ulaw in consumers.py")
else:
    # Check if already updated
    if "GLOBAL_SARVAM_CACHE" in content and "get_sarvam_session()" in content:
        print("_synthesize_ulaw in consumers.py is already updated or mismatch")

# Write consumers.py back
with open(files_to_update[0], "w", encoding="utf-8") as f:
    f.write(content)


# Now read, modify and write consumers_service2.py
with open(files_to_update[1], "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add globals under timezone import
if "GLOBAL_SARVAM_CACHE" not in content:
    content = content.replace("from django.utils import timezone", "from django.utils import timezone\n" + globals_code)
    print("Added globals to consumers_service2.py")

# 2. Update _synthesize_ulaw in consumers_service2.py
target_synthesis_block_s2 = """            clean_text = re.sub(r'<[^>]*>', '', text).strip()
            if not clean_text:
                return b""
            target_lang = "hi-IN" if is_loan_hi else "gu-IN"
            speaker = "shubh" if is_loan_hi else "ishita"
            if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"]:
                speaker = "shubh"
            pace = 1.1 if is_loan_hi else (1.15 if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"] else 1)

            payload = {
                "text": clean_text,
                "target_language_code": target_lang,
                "speaker": speaker,
                "model": "bulbul:v3",
                "pace": pace,
                "speech_sample_rate": 8000,
                "output_audio_codec": "mulaw",
                "enable_preprocessing": False
            }
            if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"]:
                payload["temperature"] = 0.85
            
            try:
                import time as t_mod
                t_start = t_mod.time()
                print(f"🎙️ [SARVAM TTS START]: Synthesizing '{clean_text[:40]}' using speaker '{speaker}' with pace '{pace}'")
                response = requests.post(api_url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                print(f"🎙️ [SARVAM TTS SUCCESS]: Done in {round((t_mod.time() - t_start) * 1000)}ms")
                # Transcode Sarvam u-law to A-law
                pcm_bytes = audioop.ulaw2lin(response.content, 2)
                return audioop.lin2alaw(pcm_bytes, 2)"""

replacement_synthesis_block_s2 = """            clean_text = re.sub(r'<[^>]*>', '', text).strip()
            if not clean_text:
                return b""
            target_lang = "hi-IN" if is_loan_hi else "gu-IN"
            speaker = "shubh" if is_loan_hi else "ishita"
            if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"]:
                speaker = "shubh"
            pace = 1.1 if is_loan_hi else (1.15 if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"] else 1)
            temp = 0.85 if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"] else None

            # Normalise clean_text for cache key
            norm_text = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()।!?]', '', clean_text).lower().strip()
            cache_key = (norm_text, target_lang, speaker, pace, temp)
            
            if cache_key in GLOBAL_SARVAM_CACHE:
                print(f"🎯 [SARVAM CACHE HIT]: Found pre-synthesized audio for '{clean_text[:40]}'")
                return GLOBAL_SARVAM_CACHE[cache_key]

            payload = {
                "text": clean_text,
                "target_language_code": target_lang,
                "speaker": speaker,
                "model": "bulbul:v3",
                "pace": pace,
                "speech_sample_rate": 8000,
                "output_audio_codec": "mulaw",
                "enable_preprocessing": False
            }
            if getattr(self, "strategy_key", None) in ["samsung_store_strategy", "samsung_llm_strategy"]:
                payload["temperature"] = 0.85
            
            try:
                import time as t_mod
                t_start = t_mod.time()
                print(f"🎙️ [SARVAM TTS START]: Synthesizing '{clean_text[:40]}' using speaker '{speaker}' with pace '{pace}'")
                response = get_sarvam_session().post(api_url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                print(f"🎙️ [SARVAM TTS SUCCESS]: Done in {round((t_mod.time() - t_start) * 1000)}ms")
                # Transcode Sarvam u-law to A-law
                pcm_bytes = audioop.ulaw2lin(response.content, 2)
                alaw_bytes = audioop.lin2alaw(pcm_bytes, 2)
                if alaw_bytes:
                    GLOBAL_SARVAM_CACHE[cache_key] = alaw_bytes
                return alaw_bytes"""

if target_synthesis_block_s2 in content:
    content = content.replace(target_synthesis_block_s2, replacement_synthesis_block_s2)
    print("Updated _synthesize_ulaw in consumers_service2.py")
else:
    if "GLOBAL_SARVAM_CACHE" in content and "get_sarvam_session()" in content:
        print("_synthesize_ulaw in consumers_service2.py is already updated or mismatch")

# Write consumers_service2.py back
with open(files_to_update[1], "w", encoding="utf-8") as f:
    f.write(content)

print("All changes applied successfully!")
