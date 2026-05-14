# import azure.cognitiveservices.speech as speechsdk
# import os
# import base64

# # ✅ ADD: Language maps
# TTS_VOICE_MAP = {
#     "en": "en-IN-AnanyaNeural",
#     "hi": "hi-IN-AnanyaNeural",
#     "gu": "gu-IN-DhwaniNeural"
# }

# STT_LANGUAGE_MAP = {
#     "en": "en-IN",
#     "hi": "hi-IN",
#     "gu": "gu-IN"
# }

# AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
# AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")


# # ✅ UNCHANGED — telecom recognizer, just added language param
# def create_speech_recognizer(language="en"):
#     speech_config = speechsdk.SpeechConfig(
#         subscription=AZURE_SPEECH_KEY,
#         region=AZURE_SPEECH_REGION
#     )

#     # ✅ Auto detect between all 3 languages simultaneously
#     auto_detect_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
#         languages=["en-IN", "hi-IN", "gu-IN"]
#     )

#     speech_config.set_property_by_name("SPEECH-RecoModelKey", "telephony")

#     # ⚡ TUNED: Aggressive silence timeouts for low-latency voice bot
#     # EndSilence: 500ms — fires recognition 300ms faster (was 800ms)
#     # Segmentation: 300ms — catches sentence breaks 200ms faster (was 500ms)
#     # InitialSilence: 8000ms — generous wait for first speech
#     speech_config.set_property(
#         speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "400"
#     )
#     speech_config.set_property(
#         speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "3000"
#     )
#     speech_config.set_property(
#         speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "300"
#     )

#     speech_config.set_property_by_name(
#         "SpeechServiceConnection_LanguageIdMode", "Continuous"
#     )

#     audio_format = speechsdk.audio.AudioStreamFormat(
#         samples_per_second=8000,
#         bits_per_sample=16,
#         channels=1
#     )

#     push_stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
#     audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

#     recognizer = speechsdk.SpeechRecognizer(
#         speech_config=speech_config,
#         audio_config=audio_config,
#         auto_detect_source_language_config=auto_detect_config 
#     )

#     return recognizer, push_stream


# # ✅ ADD: synthesize_to_base64 with language + mode support
# def synthesize_to_base64(text: str, language="en", mode="web") -> str:
#     if not text:
#         return ""

#     text = text.strip()
#     text = text.replace("&", "and").replace("\n", " ")

#     voice = TTS_VOICE_MAP.get(language, "en-IN-AnanyaNeural")

#     speech_config = speechsdk.SpeechConfig(
#         subscription=AZURE_SPEECH_KEY,
#         region=AZURE_SPEECH_REGION
#     )
#     speech_config.speech_synthesis_voice_name = voice

#     if mode == "telephony":
#         # Telecom — raw 8kHz no WAV header
#         speech_config.set_speech_synthesis_output_format(
#             speechsdk.SpeechSynthesisOutputFormat.Riff8Khz16BitMonoPcm
#         )
#     else:
#         # Web browser — WAV header included, browser plays directly
#         speech_config.set_speech_synthesis_output_format(
#             speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
#         )

#     synthesizer = speechsdk.SpeechSynthesizer(
#         speech_config=speech_config,
#         audio_config=None
#     )

#     # ✅ Correct locale mapping for all 3 languages
#     lang_locale_map = {
#         "hi": "hi-IN",
#         "gu": "gu-IN",
#         "en": "en-IN"
#     }
#     xml_lang = lang_locale_map.get(language, "en-IN")

#     # # ✅ Gujarati needs slower rate on 8kHz telephony for clear pronunciation
#     # rate = "-8%" if language == "gu" else "-5%"

#     # ✅ Gujarati needs ultra-fast confident rate (+25%), volume (+20%) and authoritative pitch (-2Hz)
#     rate = "+25%" if language == "gu" else "-5%"
#     pitch = "-2Hz" if language == "gu" else "0%"
#     volume = "+20%" if language == "gu" else "0%"

#     ssml = f"""
#     <speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis" 
#            xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='{xml_lang}'>
#         <voice name='{voice}'>
#             <mstts:silence type="Leading" value="50ms"/> 
#             <prosody rate='{rate}' pitch='{pitch}' volume='{volume}'>
#                 <emphasis level="moderate">
#                     {text}
#                 </emphasis>
#             </prosody>
#             <mstts:silence type="Tailing" value="50ms"/>
#         </voice>
#     </speak>
#     """

#     result = synthesizer.speak_ssml_async(ssml).get()

#     if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
#         raise RuntimeError("Azure TTS failed")

#     return base64.b64encode(result.audio_data).decode("utf-8")

















import azure.cognitiveservices.speech as speechsdk
import os
import base64

# ✅ ADD: Language maps
TTS_VOICE_MAP = {
    "en": "en-IN-AnanyaNeural",
    "hi": "hi-IN-AnanyaNeural",
    "gu": "gu-IN-DhwaniNeural"
}

STT_LANGUAGE_MAP = {
    "en": "en-IN",
    "hi": "hi-IN",
    "gu": "gu-IN"
}

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")


# ✅ UNCHANGED — telecom recognizer, just added language param
def create_speech_recognizer(language="en"):
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )

    # ✅ Auto detect between all 3 languages simultaneously
    auto_detect_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
        languages=["en-IN", "hi-IN", "gu-IN"]
    )

    speech_config.set_property_by_name("SPEECH-RecoModelKey", "telephony")

    # ⚡ TUNED: Aggressive silence timeouts for low-latency voice bot
    # EndSilence: 500ms — fires recognition 300ms faster (was 800ms)
    # Segmentation: 300ms — catches sentence breaks 200ms faster (was 500ms)
    # InitialSilence: 8000ms — generous wait for first speech
    speech_config.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "700"
    )
    speech_config.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "8000"
    )
    speech_config.set_property(
        speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "500"
    )

    speech_config.set_property_by_name(
        "SpeechServiceConnection_LanguageIdMode", "AtStart"
    )
    speech_config.set_property_by_name(
        "SpeechServiceConnection_LanguageIdPriority", "Latency"
    )
    speech_config.set_property_by_name(
        "SpeechServiceResponse_RequestStreamingResponse", "true"
    )
    speech_config.set_property_by_name(
        "SpeechServiceResponse_RequestPostProcessing", "false"
    )
    speech_config.set_property_by_name(
        "SpeechServiceResponse_RequestSnrAdaptation", "true"
    )

    audio_format = speechsdk.audio.AudioStreamFormat(
        samples_per_second=8000,
        bits_per_sample=16,
        channels=1
    )

    push_stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config,
        auto_detect_source_language_config=auto_detect_config 
    )

    return recognizer, push_stream


# ✅ ADD: synthesize_to_base64 with language + mode support
def synthesize_to_base64(text: str, language="en", mode="web") -> str:
    if not text:
        return ""

    text = text.strip()
    text = text.replace("&", "and").replace("\n", " ")

    voice = TTS_VOICE_MAP.get(language, "en-IN-AnanyaNeural")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )
    speech_config.speech_synthesis_voice_name = voice

    if mode == "telephony":
        # Telecom — raw 8kHz no WAV header
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
        )
    else:
        # Web browser — WAV header included, browser plays directly
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=None
    )

    # ✅ Correct locale mapping for all 3 languages
    lang_locale_map = {
        "hi": "hi-IN",
        "gu": "gu-IN",
        "en": "en-IN"
    }
    xml_lang = lang_locale_map.get(language, "en-IN")

    # Targeted Humanization:
    if language == "gu":
        # Keeping your Gujarati settings exactly as they were
        rate = "+20%"
        pitch = "-2Hz"
        volume = "0%"
    else:
        # Improving Hindi and English:
        # Slower rate (-12%) and deeper pitch (-3Hz) creates a much more 
        # trustworthy, human advisory tone for insurance calls.
        rate = "+5%"
        pitch = "+2Hz"
        volume = "+10%"

    # Enhanced SSML for AnanyaNeural:
    # - Leading silence (150ms) ensures the first word sounds natural on a phone line.
    # - Moderate emphasis breaks the monotone "AI reading" style.
    ssml = f"""
    <speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis" 
           xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='{xml_lang}'>
        <voice name='{voice}'>
            <mstts:silence type="Leading" value="150ms"/>
            <prosody rate='{rate}' pitch='{pitch}' volume='{volume}'>
                <emphasis level="moderate">
                    {text}
                </emphasis>
            </prosody>
            <mstts:silence type="Tailing" value="50ms"/>
        </voice>
    </speak>
    """

    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError("Azure TTS failed")

    return base64.b64encode(result.audio_data).decode("utf-8")