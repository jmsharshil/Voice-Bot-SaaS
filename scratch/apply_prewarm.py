# scratch/apply_prewarm.py

import os

files_to_update = [
    r"c:\Users\AYUSHI PATEL\Eleven_labs\Voice-Bot-SaaS\conversations\consumers.py",
    r"c:\Users\AYUSHI PATEL\Eleven_labs\Voice-Bot-SaaS\conversations\consumers_service2.py"
]

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
                    # If this module runs transcoding to A-law, transcode.
                    # We check if we are in consumers_service2 by inspecting the cache value conversion
                    # Actually, we can check if the file path has service2
                    if "consumers_service2" in __file__:
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

for filepath in files_to_update:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Remove old connect pre-warm
    old_prewarm_block = """        if strategy_key in ["samsung_store_strategy", "samsung_llm_strategy"]:
            def prewarm():
                common_words = ["બરાબર.", "ખૂબ સરસ.", "અરે વાહ.", "જી ચોક્કસ.", "સમજાયું.", "કોઈ વાંધો નહીં.", "આભાર.", "ઓકે."]
                for word in common_words:
                    try:
                        self._synthesize_ulaw(word, "gu")
                    except Exception:
                        pass
            self.loop.run_in_executor(None, prewarm)"""
            
    if old_prewarm_block in content:
        content = content.replace(old_prewarm_block, "")
        print(f"Removed connection pre-warm block from {os.path.basename(filepath)}")
        
    # Add startup pre-warm to the end if not present
    if "prewarm_sarvam_cache_at_startup" not in content:
        content = content.rstrip() + prewarm_startup_code
        print(f"Appended startup pre-warming task to {os.path.basename(filepath)}")
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Done apply_prewarm!")
