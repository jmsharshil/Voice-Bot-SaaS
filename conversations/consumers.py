        


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
from automobile_matcher import AutomobileMatcher

# --- GLOBAL MATCHER (Loaded once at startup) ---
try:
    AUTOMOBILE_MATCHER = AutomobileMatcher("automobile_intents.json")
except Exception as e:
    print(f"⚠️ Failed to load AutomobileMatcher: {e}")
    AUTOMOBILE_MATCHER = None

try:
    NAAVYA_MATCHER = AutomobileMatcher("automobile_bot/data/Naavya_intents.json")
except Exception as e:
    print(f"⚠️ Failed to load NaavyaMatcher: {e}")
    NAAVYA_MATCHER = None

try:
    LOAN_MATCHER = AutomobileMatcher("loan_bot/data/loan_intents.json")
except Exception as e:
    print(f"⚠️ Failed to load LoanMatcher: {e}")
    LOAN_MATCHER = None

try:
    REMINDER_MATCHER = AutomobileMatcher("reminder_bot/data/reminder_intents.json")
except Exception as e:
    print(f"⚠️ Failed to load ReminderMatcher: {e}")
    REMINDER_MATCHER = None

from elevenlabs import ElevenLabs, VoiceSettings

ELEVENLABS_CLIENT = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

ELEVENLABS_VOICE_MAP = {
    "en": "aSFxChEgBmCyExpaDqHd",  # Kanika
    "hi": "aSFxChEgBmCyExpaDqHd",
    "gu": "aSFxChEgBmCyExpaDqHd",
}





_AUDIO_TRANSCRIPTIONS: dict = {
    # HINDI
    "hi_step1_greeting.raw": "Hello! Namaste... main Aaisha bol rahi hoon, West-coast Kia se. Umeed hai aap bilkul theek honge!",
    "hi_step2_confirm_interest.raw": "Aapne Kia Seltos mein interest show kiya tha... Ahmedabad se? Kya main sahi samajh rahi hoon?",
    "hi_step2_end_call.raw": "Koi baat nahi, aapka bahut bahut shukriya ki aapne call receive ki. Jab bhi koi zaroorat ho, hum hamesha aapki seva mein taiyaar hain. Aapka din bahut achha bita karein. Take care. Namaste!",
    "hi_step3_ask_timeline.raw": "Thank you! Waise bhi, Kia Seltos ek bahut hi shandar car hai — aapne sach mein bahut achhi car choose ki hai. Aap car is mahine lene ka plan kar rahe hain?... ya agle mahine?",
    "hi_step4_ask_callback.raw": "Thank you, confirming ke liye. For best deals, offers aur poori details ke liye, kya main apni dedicated sales team se ek callback arrange kar sakti hoon? Woh aapko personally assist karenge.",
    "hi_step4_end_call.raw": "Bilkul samajh gayi. Koi tension nahi. Jab bhi aap ready hon, hum hamesha aapke liye yahan hain. Aapka bahut bahut shukriya. Aapka din mubarak ho. Namaste!",
    "hi_step5_ask_time.raw": "Wonderful! Main abhi ye note kar leti hoon. Callback ke liye konsa time best rahega aapke liye? Aur koi specific din bhi batayein agar aapko convenient ho.",
    "hi_step7_confirm_testdrive.raw": "Thank you, maine aapka time note kar liya hai. Ek aur baat — kya aap Kia Seltos ka test drive lena pasand karenge? Believe me, ek baar drive karoge toh aapko aur kuch dekhna hi nahi padega!",
    "hi_step8_closing.raw": "Thank you so much! Hamari sales team aapse jaldi hi contact karegi. Aapka time dene ke liye Shukriya.",

    # ENGLISH
    "en_step1_greeting.raw": "Hello! I hope you are doing great. This is Aaisha calling from West-coast Kia.",
    "en_step2_confirm_interest.raw": "You had recently shown interest in the Kia Seltos from Ahmedabad. Am I speaking with the right person?",
    "en_step2_end_call.raw": "No worries at all, Thank you so much for picking up the call. Whenever you need any assistance, we are always here for you. Have a wonderful day ahead. Take care. Goodbye!",
    "en_step3_ask_timeline.raw": "That is absolutely wonderful! You have truly made an excellent choice — the Kia Seltos is an incredible car. Are you planning to purchase the car this month or next month?",
    "en_step4_ask_callback.raw": "Thank you for confirming. For the best deals, offers, and full details, may I arrange a callback from our dedicated sales team for you? They will personally assist you with everything.",
    "en_step4_end_call.raw": "Absolutely understood. No worries at all. Whenever you feel ready, we are always here to help you. Thank you so much for your time. Have a great day. Goodbye!",
    "en_step5_ask_time.raw": "Wonderful! Let me note that down. Which time would be most convenient for the callback? And do let me know a preferred day as well if you have one in mind.",
    "en_step7_confirm_testdrive.raw": "Thank you, I have noted your preferred time. One more thing, would you like to schedule a test drive of the Kia Seltos? Trust me, once you experience it, you will absolutely love it!",
    "en_step8_closing.raw": "Thank you so much! Our sales team will get in touch with you very soon. Thank you so much for giving us your precious time.",

    # GUJARATI
    "gu_step1_greeting.raw": "હેલો! કેમ છો? આશા છે બધું સારું હશે. હું આઈશા બોલી રહી છું, West-coast Kia માંથી.",
    "gu_step2_confirm_interest.raw": "તમે તાજેતરમાં Kia Seltos માં રસ દર્શાવ્યો હતો, Ahmedabad થી? શું હું સાચી વ્યક્તિ સાથે વાત કરી રહી છું?",
    "gu_step2_end_call.raw": "કોઈ વાત નહીં. કૉલ ઉઠાવ્યા બદલ ખૂબ ખૂબ આભાર. જ્યારે પણ કોઈ જરૂર હોય, અમે હંમેશા તમારી સેવામાં છીએ. તમારો દિવસ ખૂબ સરસ રહે. Namaste!",
    "gu_step3_ask_timeline.raw": "Thank you! સાચ્ચે, Kia Seltos ખૂબ જ અદ્ભૂત કાર છે — તમે ખૂબ જ સારી કાર પસંદ કરી છે. તમે આ કાર આ મહિને લેવાનું plan કરો છો... કે આગળ મહિને?",
    "gu_step4_ask_callback.raw": "Thank you, confirm કરવા બદલ. Best deals, offers, અને પૂરી details માટે, શું હું અમારી sales team તરફથી callback arrange કરી શકું? તેઓ personally તમારી મદદ કરશે.",
    "gu_step4_end_call.raw": "બિલ્કુલ સમજ ગઈ. કોઈ ચિંતા નહીં. જ્યારે પણ ready હો, અમે હંમેશા અહીં છીએ. ખૂબ ખૂબ આભાર. Namaste!",
    "gu_step5_ask_time.raw": "Wonderful! હું note કરી લઉં. Callback માટે તમને કઈ time convenient રહેશે? અને કોઈ specific day હોય તો તે પણ જણાવો.",
    "gu_step7_confirm_testdrive.raw": "Thank you, મેં તમારો time note કરી લીધો. એક વધુ વાત — શું તમે Kia Seltos નું test drive લેવા ઈચ્છો છો? Believe me, એક વાર drive કરો, ત્યારબાદ બીજી કોઈ car જોવાની જ ઈચ્છા ન થાય!",
    "gu_step8_closing.raw": "Thank you so much! અમારી sales team ટૂંક સમયમાં તમારો contact કરશે. તમારો આટલો કિંમતી સમય આપવા બદલ ખૂબ ખૂબ આભાર.",

    # HOSPITAL APPOINTMENT SCHEDULER
    "hosp_step1_greeting.raw": "Hello! I am Sophia calling from City Clinic. We received your booking request for tomorrow. Can we confirm your appointment?",
    "hosp_step2_ask_slot.raw": "Great! Would you prefer a morning session between 10 to 12, or an afternoon session between 2 to 4?",
    "hosp_step3_closing.raw": "Perfect! Your slot has been confirmed. We have sent the confirmation details on WhatsApp. Thank you, take care!",
    "hosp_step_cancellation.raw": "Understood. We have cancelled your request. Have a good day. Goodbye!",

    # NAAVYA AUTOMOBILE BOT (HINDI)
    "Naavya/hi_step1_greeting.raw": "Namaste! Main Naavya bol rahi hoon JMS automobile se. Aasha karti hoon aapka din achha ja raha hoga. Kya main aapse do minute baat kar sakti hoon?",
    "Naavya/hi_step2_discover_use.raw": "Bahut shukriya. Main aapki zaroorat ko thoda aur behatar samajhna chahti hoon. Kya aap gaadi zyada shehar mein chalane ke liye dekh rahe hain, lambi yatraon ke liye, ya dono ke liye?",
    "Naavya/hi_step2_end_call.raw": "Koi baat nahi sir. Aapne apna samay diya uske liye dhanyavaad. Agar bhavishya mein gaadi se judi kisi bhi jaankari ki zaroorat ho, toh humse kabhi bhi sampark kar sakte hain. Aapka din shubh ho.",
    "Naavya/hi_step3_discover_budget.raw": "Samajh gayi. Taaki main aapko behtar vikalp suggest kar sakoon, kya aap apna  budget range bata sakte hain?",
    "Naavya/hi_step4_discover_family.raw": "Bahut badhiya. Kya yeh gaadi mukhyata aapke vyaktigat upyog ke liye hogi ya poore parivaar ke liye bhi?",
    "Naavya/hi_step5_discover_musthaves.raw": "Aur kya aapki koi khaas pasand ya requirement hai? Jaise sunroof, automatic transmission, electric vehicle, ya phir adhik safety features?",
    "Naavya/hi_step6_pitch_visit.raw": "Sach kahun toh gaadi ki asli premium feeling usmein baithkar hi mehsoos hoti hai. Photos aur videos us experience ko poori tarah nahi dikha paate. Kya aap is hafte showroom visit karna pasand karenge?",
    "Naavya/hi_step7_offer_testdrive.raw": "Aur ek test drive se aap gaadi ki comfort, performance aur driving experience ko khud mehsoos kar sakte hain. Kya main aapke liye ek test drive schedule kar doon?",
    "Naavya/hi_step8_collect_details.raw": "Bahut achha. Kripya apna naam, suvidhajanak din aur samay  bata dijiye taaki main booking confirm kar sakoon..",
    "Naavya/hi_step9_closing.raw": " Aapki booking safaltaapurvak note kar li gayi hai. Aapka din mangalmay ho.",

    # NAAVYA AUTOMOBILE BOT (ENGLISH)
    "Naavya/en_step1_greeting.raw": "Hi there! This is Priya. So lovely to connect with you! Are you exploring a new car today, or is there a specific model you have your eye on?",
    "Naavya/en_step2_discover_use.raw": "That's wonderful! To understand your needs better, are you looking for a car for daily city use, weekend adventures, or a mix of both?",
    "Naavya/en_step2_end_call.raw": "No worries at all. Thank you so much for taking the call. Feel free to connect whenever you're ready to explore. Take care! Goodbye!",
    "Naavya/en_step3_discover_budget.raw": "Got it. And what budget range are you considering? A rough ballpark is totally fine.",
    "Naavya/en_step4_discover_family.raw": "Understood. Will this vehicle be primarily for yourself, or is it for the family too?",
    "Naavya/en_step5_discover_musthaves.raw": "Great choice! And do you have any must-haves, like a sunroof, an EV, an automatic gearbox, or high ground clearance?",
    "Naavya/en_step6_pitch_visit.raw": "Honestly, pictures and specs don't capture how premium it feels inside. Sitting inside makes all the difference! Would you like to visit our showroom this week?",
    "Naavya/en_step7_offer_testdrive.raw": "And of course, the best part — would you like to take it for a spin? A test drive tells you what no brochure can. What day works best for you?",
    "Naavya/en_step8_collect_details.raw": "Perfect! May I have your name, preferred date and time, and your phone number to confirm the booking?",
    "Naavya/en_step9_closing.raw": "Awesome! I have got you booked. We will have everything ready for you. Really looking forward to meeting you. Drive safe!",

    # NAAVYA AUTOMOBILE BOT (GUJARATI)
    "Naavya/gu_step1_greeting.raw": "હેલો! કેમ છો? હું પ્રિયા બોલી રહી છું. તમારી સાથે વાત કરીને આનંદ થયો! શું તમે આજે કોઈ નવી કાર જોવા માંગો છો કે કોઈ ખાસ મોડેલ વિશે વાત કરવી છે?",
    "Naavya/gu_step2_discover_use.raw": "ખૂબ સરસ! તમારી જરૂરિયાતોને વધુ સારી રીતે સમજવા માટે, શું તમે આ કાર રોજિંદા સિટી ડ્રાઇવ માટે જુઓ છો, વીકેન્ડ મુસાફરી માટે, કે બંનેના મિક્સ માટે?",
    "Naavya/gu_step2_end_call.raw": "કોઈ વાંધો નહીં. કૉલ પર વાત કરવા બદલ આભાર. જ્યારે પણ કાર વિશે કોઈ માહિતી જોઈએ, ચોક્કસ સંપર્ક કરજો. આવજો!",
    "Naavya/gu_step3_discover_budget.raw": "બરાબર. અને તમારું અંદાજિત બજેટ કેટલું છે? એક અંદાજ આપશો તો પણ ચાલશે.",
    "Naavya/gu_step4_discover_family.raw": "સમજી ગઈ. અને આ ગાડી મુખ્યત્વે તમારા પોતાના વપરાશ માટે છે, કે ફેમિલી માટે પણ છે?",
    "Naavya/gu_step5_discover_musthaves.raw": "સરસ! અને શું તમારી કોઈ ખાસ જરૂરિયાતો છે, જેમ કે સનરૂફ, ઇલેક્ટ્રિક કાર, ઓટોમેટિક ગીયરબોક્સ, કે વધુ ગ્રાઉન્ડ ક્લિયરન્સ?",
    "Naavya/gu_step6_pitch_visit.raw": "સાચું કહું તો, ફોટા કે વિડીયોમાં તે પ્રીમિયમ ફીલ નથી આવતી જે કારમાં બેસીને આવે છે. શું તમે આ અઠવાડિયે શોરૂમની મુલાકાત લેવાનું પસંદ કરશો?",
    "Naavya/gu_step7_offer_testdrive.raw": "અને હા, સૌથી ઉત્તમ વસ્તુ — શું તમે ટેસ્ટ ડ્રાઇવ લેવા માંગો છો? એક વાર ચલાવી જોશો તો બધો ખ્યાલ આવી જશે. તમારા માટે કયો દિવસ અનુકૂળ રહેશે?",
    "Naavya/gu_step8_collect_details.raw": "ખૂબ સરસ! ટેસ્ટ ડ્રાઈવ બુક કરવા માટે કૃપા કરીને તમારું નામ, અનુકૂળ તારીખ અને સમય, અને ફોન નંબર જણાવશો?",
    "Naavya/gu_step9_closing.raw": "ખૂબ સરસ! મેં તમારી એપોઇન્ટમેન્ટ બુક કરી લીધી છે. અમે શોરૂમ પર તમારી રાહ જોઈશું. સેફ ડ્રાઇવ કરજો! આવજો!",

    # JMS BANK LOAN BOT
    "loan_bot/loan_step1_greeting.raw": "Hello! Namaste... main JMS Bank ki taraf se Naavya bol rahi hoon. Aaj main aapko hamare exclusive loan products ke baare mein batana chahti hoon — home loan, business loan, personal loan aur bahut kuch. Kya aap apne kisi financial goal ke liye loan explore kar rahe hain?",
    "loan_bot/loan_step2_discover_type.raw": "Wonderful! JMS Bank mein hum aapki har zaroorat ke liye tailor-made loan solutions offer karte hain — chahe wo dream home ho, apna business grow karna ho, ya koi personal zaroorat. Aap kaunsa loan option explore karna chahenge?",
    "loan_bot/loan_step3_discover_amount.raw": "Great choice! aapko approximately kitne amount ka loan chahiye? Exact figure nahi pata toh koi baat nahi, ek rough idea bhi kaafi hai — hum uske hisaab se best plan suggest kar sakte hain.",
    "loan_bot/loan_step4_closing.raw": "Excellent! Aapki saari details note kar li gayi hain. Hamari expert team bahut jald aapse connect karegi aur aapke liye best loan offer ready karegi. JMS Bank choose karne ke liye bahut bahut shukriya!",
    "loan_bot/loan_step_rejection.raw": "Bilkul theek hai, koi problem nahi! Jab bhi aapko zaroorat ho, JMS Bank hamesha aapke liye available hai. Apna precious time dene ke liye dil se shukriya. Aapka din bahut accha jaye!",

    # JMS BANK LOAN REMINDER BOT
    "reminder_bot/reminder_step1_greeting.raw": "નમસ્તે! હું જે એમ એસ બેંકમાંથી નવ્યા બોલું છું. તમારી ઈ એમ આઈ ની તારીખ નજીક છે, તમે ક્યારે ચુકવણી કરશો?",
    "reminder_bot/reminder_step2_ask_mode.raw": "ધન્યવાદ જણાવવા માટે, તમે કઈ રીતે ચુકવણી કરશો? યુ પી આઈ, નેટબેંકિંગ કે અન્ય કોઈ રીતે?",
    "reminder_bot/reminder_step3_closing.raw": "સરસ! તમારી વિગતો નોંધી લેવામાં આવી છે. સમયસર ચુકવણી કરવા બદલ આભાર!",
    "reminder_bot/reminder_step_rejection.raw": "તમારી અસુવિધા બદલ દિલગીર છું. તમારી માહિતી નોંધી લેવામાં આવી છે. સમયસર ચુકવણી કરવા બદલ આભાર!",
}

_GREETING_AUDIO_CACHE: dict = {}  # agent_id → bytes


# ================= DATABASE =================

@sync_to_async
def create_conversation(agent_id, session_id, user_number, campaign_id=None):
    conv = Conversation.objects.create(
        agent_id=agent_id,
        session_id=session_id,
        user_number=user_number,
        campaign_id=campaign_id
    )
    # Create immediate LeadAnalysis record so it shows on dashboard instantly
    LeadAnalysis.objects.create(
        conversation=conv,
        agent_id=agent_id,
        lead_level="cold",  # Default level for new/short calls
        summary="Call started..."
    )

    # Notify dialer that the call was answered
    if user_number:
        try:
            from bot.views import _answered_calls, _call_queue_lock, _normalize_phone
            clean_phone = _normalize_phone(user_number)
            with _call_queue_lock:
                _answered_calls.add(clean_phone)
            print(f"📞 AUTO-DIALER: Marked {clean_phone} as answered in campaign state.")
        except Exception as e:
            print(f"WARNING: Failed to mark phone as answered: {e}")

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
            return f"Hello, Main {agent.name} bol rahi hoon {company} se."

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

def _amplify_pcm(pcm: bytes, gain: float = 1.8) -> bytes:
    """Amplify 16-bit PCM audio by gain factor with clipping protection."""
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    samples = samples * gain
    samples = np.clip(samples, -32768, 32767)
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
        "અلविदा",
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


# ================= SSML BUILDER =================

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
    "gu": {"rate": "+20%", "pitch": "0%", "volume": "0%"},
}   


def _inject_english_lang_tags(text: str) -> str:
    import re

    def escape_xml(s):
        return s.replace('&', '&amp;').replace('"', '&quot;')

    def expand_if_acronym(word: str) -> str:
        if re.match(r'^[A-Z][A-Z0-9]+$', word):
            return ' '.join(word)
        if re.match(r'^[A-Z]{2,}', word) and re.search(r'[-/0-9]', word):
            parts = re.split(r'[-/]', word)
            spelled = []
            for part in parts:
                if re.match(r'^[A-Z0-9]+$', part):
                    spelled.append(' '.join(part))
                else:
                    spelled.append(part)
            return ' '.join(spelled)
        return word

    pattern = re.compile(r'([A-Za-z][A-Za-z0-9.\-/]*)')
    result = []
    last_end = 0

    for match in pattern.finditer(text):
        start, end = match.start(), match.end()
        gujarati_part = text[last_end:start]
        if gujarati_part:
            result.append(escape_xml(gujarati_part))
        english_word = match.group(1)
        expanded = expand_if_acronym(english_word)
        result.append(f'<lang xml:lang="en-IN">{escape_xml(expanded)}</lang>')
        last_end = end

    remaining = text[last_end:]
    if remaining:
        result.append(escape_xml(remaining))

    return ''.join(result)


def build_ssml(text: str, language: str) -> str:
    voice = TTS_VOICE_MAP.get(language, TTS_VOICE_MAP["en"])
    style = SSML_STYLE_MAP.get(language)
    prosody = SSML_PROSODY_MAP.get(language, SSML_PROSODY_MAP["en"])
    lang_tag = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}.get(language, "en-IN")

    if language == "gu":
        text = text.replace('&', '&amp;')
    else:
        text = text.replace('&', '&amp;')
        # Add natural pauses at punctuation
        # text = re.sub(r'([।])', r'\1<break time="400ms"/>', text)
        # text = re.sub(r'([?!])\s', r'\1<break time="350ms"/> ', text)

    prosody_open = f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}" volume="{prosody.get("volume", "0%")}">'
    prosody_close = '</prosody>'

    if language != "gu":
        # text = re.sub(
        #     r'^(Hello|Hi|Namaste|Ji|Acha|Haan|Okay|Suniye|Bilkul),',
        #     r'\1,<break time="300ms"/>',
        #     text, flags=re.I
        # )
        # # Comma pauses — natural breath points
        # text = re.sub(r',\s*(?!<break)', ', <break time="180ms"/>', text)
        # # Question — slight pitch lift
        # if text.rstrip().endswith("?"):
        #     text = f'<prosody pitch="+2%">{text}</prosody>'
        pass

    if language == "gu":
        inner = f'{prosody_open}{text}{prosody_close}'
    # elif style:
    #     inner = (
    #         f'<mstts:express-as style="{style}" styledegree="1.2">'
    #         f'{prosody_open}{text}{prosody_close}'
    #         f'</mstts:express-as>'
    #     )
    # else:
    #     inner = (
    #         f'<mstts:express-as style="customerservice" styledegree="1.0">'
    #         f'{prosody_open}{text}{prosody_close}'
    #         f'</mstts:express-as>'
    #     )
    else:
        inner = f'{prosody_open}{text}{prosody_close}'

    return (
        f'<speak version="1.0" '
        f'xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xmlns:mstts="http://www.w3.org/2001/mstts" '
        f'xml:lang="{lang_tag}">'
        f'<voice name="{voice}">'
        f'{inner}'
        f'</voice>'
        f'</speak>'
    )


# ================= CONSUMER =================

class VoiceBotConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.loop = asyncio.get_running_loop()

        params = parse_qs(self.scope["query_string"].decode())
        self.agent_id = params.get("agent_id", [None])[0]
        # Prioritize 'phone' param (outbound auto-dialer) over 'from' header
        self.user_number = params.get("phone", [None])[0] or params.get("from", ["unknown"])[0]
        self.language = params.get("language", ["hi"])[0]

        campaign_id_str = params.get("campaign_id", [None])[0]
        campaign_id = None
        if campaign_id_str:
            try:
                campaign_id = int(campaign_id_str)
            except ValueError:
                pass

        if not self.agent_id:
            await self.close()
            return

        self.session_id = str(uuid.uuid4())
        self.conversation = await create_conversation(
            self.agent_id, self.session_id, self.user_number, campaign_id
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
        # Timestamps for when bot speech started and ended.
        # Any Azure STT result recognised DURING bot speech is discarded —
        # it means the user spoke over the bot and we don't want to process it.
        self._bot_speaking_started_at = 0.0   # set every time is_bot_speaking → True
        self._bot_speaking_ended_at = 0.0     # set every time is_bot_speaking → False
        # Grace period (seconds) after bot stops speaking during which STT results
        # are still treated as "spoken during bot turn" and discarded.
        self._post_speech_grace = 0.05  # 50ms — tight enough since we gate silence not real audio
        self.current_phase = "GREETING_REPLY"

        # ── DUPLICATE PREVENTION ───────────────────────────────
        # Tracks whether VAD partial-dispatch already fired for current utterance.
        # When Azure final arrives, it checks this to avoid double-processing.
        self._vad_dispatched_text = ""       # normalized text that VAD already sent to AI
        self._vad_dispatched_time = 0.0      # when VAD dispatched it
        self._azure_final_received_time = 0.0  # when Azure last fired recognized

        # ── LOCKS & TASKS ──────────────────────────────────────
        self.processing_lock = asyncio.Lock()
        self.tts_task = None
        self._tts_synthesizers = {}  # Cache synthesizers by language code

        # ── AUDIO / VAD ────────────────────────────────────────
        # self.jitter_buffer = []
        # self.jitter_delay = 2

        self.speech_active = False
        self.silence_start_time = None

        self.SPEECH_DETECT_RMS = 300   # 300 = catches quiet speech; VAD fires faster
        self.SILENCE_TRIGGER_SEC = 0.9   # 900ms — gives user natural pauses to finish their thoughts
        self.MIN_WORD_COUNT = 1

        # Interrupt detection removed — user speech during bot speech is silently dropped

        # ── STT SETUP ──────────────────────────────────────────
        self.recognizer, self.push_stream = create_speech_recognizer(language=self.language)
        self._setup_stt_callbacks()
        self.recognizer.start_continuous_recognition_async()

        # ── PRIME AZURE STT ────────────────────────────────────
        # Write ~1 second of silence (50 frames × 20ms) immediately after
        # starting the recognizer. This forces Azure to fully negotiate its
        # internal WebSocket + model session NOW, so the first user utterance
        # gets recognized instantly instead of paying a cold-start penalty.
        _prime_frames = SILENCE_FRAME * 50
        self.push_stream.write(_prime_frames)
        # print("🔥 Azure STT session primed (50 silence frames)")

        # ── TTS SYNTHESIZER ───────────────────────────────────
        self._tts_synthesizer = self._build_tts_synthesizer()

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
            if strategy_key in ["real_estate", "reminder_strategy"]:
                tts_lang = "gu"
            elif strategy_key == "interview_bot":
                tts_lang = "interview_en"
            else:
                tts_lang = "en"
                
            # 2. Get Opening Message
            summary_txt = agent.summary.strip().rstrip(".") if agent.summary else ""
            if tts_lang == "gu":
                if strategy_key == "reminder_strategy":
                    greeting = "નમસ્તે! હું જે એમ એસ બેંકમાંથી નવ્યા બોલું છું. તમારી ઈ એમ આઈ ની તારીખ નજીક છે, તમે ક્યારે ચુકવણી કરશો?"
                else:
                    greeting = f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. {summary_txt}" if summary_txt else f"નમસ્તે! હું {agent.name} છું, {company} તરફથી. મિલકત ખરીદવી, વેચવી, ભાડે આપવી કે રોકાણ — કોઈ પણ બાબતમાં મદદ જોઈએ તો કહો!"
            elif tts_lang == "interview_en":
                greeting = f"Hello, I am {agent.name}."
            else:
                greeting = f"Hello! Main {agent.name} bol rahi hoon {company} se. {summary_txt}." if summary_txt else f"Hello, Main {agent.name} bol rahi hoon {company} se. kya aap abhi baat kar sakte hain?"
            
            # 3. Mark intro shown
            session, _ = ConversationSession.objects.get_or_create(agent=agent, session_id=session_id)
            state = session.state or {}
            state["intro_shown"] = True
            state["detected_language"] = language
            if strategy_key == "hospital_minimal":
                state["step"] = "confirm_interest"
            elif strategy_key in ["loan_strategy", "reminder_strategy"]:
                state["call_phase"] = "interest_confirmation"
            session.state = state
            session.save()
            
            return tts_lang, greeting, strategy_key

        # Kick off DB fetch and TTS cache-check IN PARALLEL
        db_task = asyncio.create_task(get_initial_call_data(self.agent_id, self.session_id, self.language))

        # While DB is running, check if we already have cached audio for this agent
        cached_audio = _GREETING_AUDIO_CACHE.get(f"{self.agent_id}_{self.language}")

        self.agent_tts_lang, greeting, self.strategy_key = await db_task

        # Determine greeting audio path
        if self.strategy_key == "hospital_minimal":
            greeting_file = "hosp_step1_greeting.raw"
        elif self.strategy_key == "loan_strategy":
            greeting_file = "loan_bot/loan_step1_greeting.raw"
        elif self.strategy_key == "reminder_strategy":
            greeting_file = "reminder_bot/reminder_step1_greeting.raw"
        elif self.strategy_key == "automobile_Naavya":
            greeting_file = f"Naavya/{self.language}_step1_greeting.raw"
        else:
            greeting_file = f"{self.language}_step1_greeting.raw"
        greeting_text = _AUDIO_TRANSCRIPTIONS.get(greeting_file, greeting)

        # Record the greeting message in the database so it appears in the chat transcript
        await save_message(self.conversation, "bot", greeting_text)

        local_greeting_path = os.path.join("mp3_responses", greeting_file)
        if cached_audio:
            # ⚡ INSTANT: stream pre-synthesized bytes directly — zero TTS latency
            print("⚡ Greeting served from audio cache (0ms TTS)")
            self.tts_task = asyncio.create_task(self._stream_cached_greeting(cached_audio))
        elif os.path.exists(local_greeting_path):
            print(f"🚀 INSTANT GREETING: Found local file {local_greeting_path}")
            with open(local_greeting_path, "rb") as f:
                ulaw = f.read()
            self.tts_task = asyncio.create_task(self._stream_cached_greeting(ulaw))
        else:
            # First call for this agent: synthesize and cache for future calls
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
                        # 🚨 Do NOT switch language while bot speaks — echo causes mis-detection
                        self.loop.call_soon_threadsafe(self._set_language, lang_code)
            
            self.loop.call_soon_threadsafe(self._set_partial, text)

        def handle_recognized(evt):
            # Capture recognition time immediately — used for bot-speech gating
            recognised_at = time.time()

            text = evt.result.text.strip() if evt.result.text else ""
            if not text:
                return

            self.partial_text = ""  # Clear any stale partial VAD text from this turn

            detected_lang = evt.result.properties.get(
                speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, "en-IN"
            )
            lang_code = detected_lang.split("-")[0] if detected_lang else "en"
            # 🚨 BLOCK language switching while bot is speaking or within 600ms after it ends
            # (bot audio echo can arrive late and falsely trigger a language switch)
            post_speech_grace = 0.6
            in_post_speech = (
                self._bot_speaking_ended_at > 0
                and (recognised_at - self._bot_speaking_ended_at) < post_speech_grace
            )
            if lang_code in ["en", "hi", "gu"] and not self.is_bot_speaking and not in_post_speech:
                self.loop.call_soon_threadsafe(self._set_language, lang_code)

            print(f"✅ Azure FINAL [{detected_lang}]: {text}")

            # ── GATE 1: Discard if recognised while bot was speaking ───────
            # Azure STT keeps running even when we stop feeding audio — its
            # internal buffer can still produce a result after bot speech ends.
            # Any result timestamped inside [bot_started … bot_ended + grace]
            # is the user talking OVER the bot; we must not process it.
            if self._recognised_during_bot_speech(recognised_at):
                print(f"🚫 Azure FINAL discarded (recognised during bot speech): {text!r}")
                return

            # Record when Azure fired so VAD path can check recency
            self._azure_final_received_time = recognised_at

            # ── GATE 2: Did VAD already dispatch this utterance? ───────────
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
        # ⚡ STICKY REGIONAL LANGUAGE: Once the conversation has entered a regional language (Hindi or Gujarati),
        # do NOT automatically switch back to English ('en'). Users frequently use English loanwords 
        # (Hinglish/Gujlish) like "City mein", "Automatic car", which Azure STT detects as 'en-IN',
        # but they still want the conversation to continue in their regional language.
        if self.language in ["hi", "gu"] and lang_code == "en":
            return

        if self.language != lang_code:
            # Only switch if we are NOT in the middle of processing (to avoid state corruption)
            if not self.is_processing:
                print(f"🌐 Language switched to: {lang_code}")
                self.language = lang_code
                self._tts_synthesizer = self._build_tts_synthesizer()
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
        # Wipe any STT partial that was building before bot started — it's stale
        self.partial_text = ""

    def _mark_bot_speaking_end(self):
        """Call immediately after bot audio finishes or is cancelled."""
        self._bot_speaking_ended_at = time.time()
        self.partial_text = ""  # ⚡ Clear partial text again to avoid stale dispatch
        # Drain every STT result that arrived while bot was speaking — all stale
        drained = 0
        while not self.final_text_queue.empty():
            try:
                self.final_text_queue.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
        if drained:
            print(f"🧹 Drained {drained} stale STT result(s) after bot speech")
        # Clear partial too — Azure was hearing bot audio, not user
        self.partial_text = ""

    def _recognised_during_bot_speech(self, recognised_at: float) -> bool:
        """
        True if an Azure recognition arrived while the bot was speaking OR
        within the post-speech grace window (self._post_speech_grace seconds).
        recognised_at = time.time() captured inside handle_recognized callback.
        """
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

            # Check against last dispatched using fuzzy match
            if self.last_dispatched_text and _is_duplicate_utterance(text, self.last_dispatched_text):
                # Only skip if dispatch was recent (within 4 seconds)
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
            # Clear any stale VAD dispatch record since Azure final now owns this utterance
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
                start_payload = data.get("start", {})
                self.stream_sid = start_payload.get("streamSid")
                print(f"📡 streamSid captured: {self.stream_sid}")
                # Save stream_sid to DB for CDR matching
                if self.stream_sid:
                    await save_stream_sid(self.conversation, self.stream_sid)
                    print(f"💾 streamSid saved to DB for conversation {self.conversation.id}")

                try:
                    # For outbound calls: calledNumber is customer
                    # For inbound calls: callerNumber is customer
                    custom = start_payload.get("customParameters", {})
                    number = custom.get("calledNumber") or custom.get("callerNumber") or start_payload.get("caller")

                    if number and (self.user_number == "unknown" or not self.user_number):
                        clean_num = str(number).strip()
                        if clean_num.startswith("+91") and len(clean_num) == 13:
                            clean_num = clean_num[3:]
                        elif clean_num.startswith("91") and len(clean_num) == 12:
                            clean_num = clean_num[2:]

                        self.user_number = clean_num
                        await update_user_number(self.conversation, clean_num)
                        print(f"💾 Customer number '{clean_num}' extracted from start payload")
                except Exception as ex:
                    print("⚠️ Error extracting caller number from start payload:", ex)
            
            # --- TEST BACKDOOR ---
            elif data.get("event") == "test_text":
                text = data.get("text", "")
                print(f"🧪 [TEST-MESSAGE]: {text}")
                await self.handle_ai_reply(text)

            if data.get("event") == "media":
                await self._handle_audio_chunk(data)

        except Exception as e:
            print("❌ RECEIVE ERROR:", e)

    async def _handle_audio_chunk(self, data):
        payload = base64.b64decode(data["media"]["payload"])
        pcm = decode_g711(payload)

        # ── BOT SPEAKING GUARD ─────────────────────────────────
        # While the bot is speaking, drop real user audio so we never
        # dispatch or run VAD on it. However, we still write SILENCE
        # frames to the Azure STT push stream so the session stays warm.
        # Without this, Azure's recognition engine goes "cold" during the
        # greeting and the first user utterance suffers a noticeable delay.
        if self.is_bot_speaking:
            self.push_stream.write(SILENCE_FRAME)
            return

        rms = audioop.rms(pcm, 2)

        # Feed real audio to Azure STT (bot is silent)
        self.push_stream.write(pcm)

        # ── VAD PARTIAL-TEXT DISPATCH ──────────────────────────
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

                        # ── DEDUP: skip if already dispatched recently ─────
                        if self.last_dispatched_text and _is_duplicate_utterance(fallback_text, self.last_dispatched_text):
                            if time.time() - self.last_dispatch_time < 4.0:
                                print("⏭️ VAD duplicate skipped:", fallback_text)
                                return

                        if time.time() - self.last_dispatch_time < 0.5:
                            return

                        # ── DEDUP: if Azure final arrived very recently for
                        #    the same content, let Azure final handle it ─────
                        if (time.time() - self._azure_final_received_time) < 0.5:
                            print("⏭️ VAD skipped — Azure final just fired, letting it handle:", fallback_text)
                            return

                        print("⚡ FAST DISPATCH (partial VAD):", fallback_text)

                        # Record that VAD dispatched this so Azure final can skip it
                        self._vad_dispatched_text = normalized
                        self._vad_dispatched_time = time.time()

                        self.last_dispatched_text = normalized
                        self.last_dispatch_time = time.time()
                        self.is_processing = True
                        try:
                            async with self.processing_lock:
                                self.partial_text = "" # ⚡ Clear immediately after dispatch
                                await self.handle_ai_reply(fallback_text)
                        finally:
                            self.is_processing = False

    # ================= (INTERRUPT DETECTION REMOVED) =================
    # Barge-in / interruption detection has been intentionally removed.
    # When the bot is speaking, all user audio is dropped at _handle_audio_chunk.
    # After the bot finishes its full response, user speech is accepted normally.

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

    # ================= AI (STREAMING) =================

    async def _stream_local_audio_file(self, filename):
        """Read a local .raw audio file and stream it to the WebSocket."""
        filename = filename.replace(".mp3", ".raw")
        
        # Determine current language prefix (e.g., 'hi_', 'en_', 'gu_')
        # Check if the file exists directly first (e.g. hosp_step2_ask_slot.raw)
        file_path = os.path.join("mp3_responses", filename)
        if not os.path.exists(file_path):
            lang_prefix = f"{self.language}_"
            if "/" in filename:
                folder, name = filename.split("/", 1)
                if not name.startswith(lang_prefix):
                    filename = f"{folder}/{lang_prefix}{name}"
            else:
                if not filename.startswith(lang_prefix):
                    filename = f"{lang_prefix}{filename}"
            
        # Record the bot reply in the database chat logs
        transcription = _AUDIO_TRANSCRIPTIONS.get(filename)
        if transcription:
            await save_message(self.conversation, "bot", transcription)

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
                    # Read 160 bytes (20ms of u-law audio)
                    chunk = f.read(160)
                    if not chunk:
                        break
                    
                    # Encode to base64 for Twilio/Daphne
                    payload = base64.b64encode(chunk).decode("utf-8")
                    try:
                        await self.send(json.dumps({
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {"payload": payload}
                        }))
                    except Exception:
                        break  # Stop streaming immediately if client disconnected
                    
                    bytes_sent += len(chunk)
                    
                    # Precise throttling based on clock (fixes Windows 20ms jitter)
                    expected_time = bytes_sent / 8000.0
                    actual_time = time.time() - start_time
                    if expected_time > actual_time:
                        await asyncio.sleep(expected_time - actual_time)
        finally:
            self.is_bot_speaking = False
            self._bot_speaking_ended_at = time.time()
            print(f"✅ [PLAYBACK]: Finished {filename}")

    async def handle_ai_reply(self, text):
        # ── STRICT BARGE-IN PREVENTION ──
        # Completely ignore any user input received while the bot is speaking
        if self.is_bot_speaking:
            print(f"🔇 [BARGE-IN DISABLED]: Ignoring user input '{text}' because bot is speaking.")
            return

        pipeline_start = time.time()
        text = text.strip()
        if not text:
            return

        normalized = text.lower().strip()

        # ── INTENT ROUTER (FAST-PATH) ──────────────────
        is_automobile = getattr(self, "strategy_key", None) == "automobile"
        is_naavya = getattr(self, "strategy_key", None) == "automobile_Naavya"
        is_loan = getattr(self, "strategy_key", None) == "loan_strategy"
        is_reminder = getattr(self, "strategy_key", None) == "reminder_strategy"
        
        if (is_automobile and AUTOMOBILE_MATCHER) or (is_naavya and NAAVYA_MATCHER) or (is_loan and LOAN_MATCHER) or (is_reminder and REMINDER_MATCHER):
            if is_loan:
                matcher = LOAN_MATCHER
            elif is_reminder:
                matcher = REMINDER_MATCHER
            else:
                matcher = NAAVYA_MATCHER if is_naavya else AUTOMOBILE_MATCHER
            try:
                # 1. Initialize/Load current phase (Safe attribute check)
                current_phase = "GREETING_REPLY"
                try:
                    # Try to get state from the conversation session
                    from conversations.models import ConversationSession
                    session = await sync_to_async(
                        lambda: ConversationSession.objects.filter(session_id=self.session_id).first()
                    )()
                    if session and session.state:
                        current_phase = session.state.get("current_phase", "GREETING_REPLY")
                        if is_loan:
                            current_phase = session.state.get("call_phase", "interest_confirmation")
                            # Map strategy phase to intents phase if they differ:
                            # 'interest_confirmation' -> 'GREETING_REPLY'
                            # 'discover_loan_type' -> 'DISCOVER_LOAN_TYPE'
                            # 'collect_amount' -> 'COLLECT_ANSWERS'
                            phase_map = {
                                "interest_confirmation": "GREETING_REPLY",
                                "discover_loan_type": "DISCOVER_LOAN_TYPE",
                                "collect_amount": "COLLECT_ANSWERS",
                            }
                            current_phase = phase_map.get(current_phase, "GREETING_REPLY")
                        elif is_reminder:
                            current_phase = session.state.get("call_phase", "interest_confirmation")
                            phase_map = {
                                "interest_confirmation": "GREETING_REPLY",
                                "ask_payment_mode": "ASK_PAYMENT_MODE",
                                "closing": "CLOSING",
                            }
                            current_phase = phase_map.get(current_phase, "GREETING_REPLY")
                        self.current_phase = current_phase
                except:
                    pass

                # 2. Check for semantic match (Fast-Path)
                match_result = matcher.find_match(text, current_phase=current_phase, threshold=0.70)

                if match_result["match_type"] != "NONE":
                    intent_name = match_result['intent']['intent_name']
                    print(f"⚡ [FAST-PATH]: Matched {intent_name} (Source: {match_result['match_type']})")
                    
                    # 3. Handle State Transition (Persist to DB)
                    next_phase = match_result.get("next_phase")
                    if next_phase:
                        try:
                            session = await sync_to_async(
                                lambda: ConversationSession.objects.filter(session_id=self.session_id).first()
                            )()
                            if session:
                                state = session.state or {}
                                state["current_phase"] = next_phase
                                if is_loan:
                                    rev_map = {
                                        "GREETING_REPLY": "interest_confirmation",
                                        "DISCOVER_LOAN_TYPE": "discover_loan_type",
                                        "COLLECT_ANSWERS": "collect_amount",
                                        "CLOSING": "closing"
                                    }
                                    state["call_phase"] = rev_map.get(next_phase, "interest_confirmation")
                                elif is_reminder:
                                    rev_map = {
                                        "GREETING_REPLY": "interest_confirmation",
                                        "ASK_PAYMENT_MODE": "ask_payment_mode",
                                        "CLOSING": "closing"
                                    }
                                    state["call_phase"] = rev_map.get(next_phase, "interest_confirmation")
                                session.state = state
                                await sync_to_async(session.save)()
                                self.current_phase = next_phase
                                print(f"🔄 [PHASE UPDATE]: {current_phase} -> {next_phase}")
                        except Exception as state_err:
                            print(f"⚠️ State save failed: {state_err}")

                    # 4. Record the turn in database
                    await save_message(self.conversation, "user", text)
                    
                    # 5. Play MP3/Raw Audio instantly
                    mp3_filename = match_result["mp3"]
                    raw_filename = mp3_filename.replace(".mp3", ".raw")
                    await self._stream_local_audio_file(raw_filename)

                    # 6. Auto-disconnect if this was a closing intent
                    if next_phase == "CLOSING" or match_result.get("intent", {}).get("intent_name", "").endswith("closing"):
                        print("📴 [AUTO-DISCONNECT]: Closing intent played — ending call.")
                        await close_conversation(self.conversation)
                        await self.send(text_data=json.dumps({"event": "stop"}))
                        self.is_connected = False
                        await self.close()
                        return

                    # SUCCESS: Fast-Path handled the turn, we are done!
                    return


                else:
                    print(f"🧠 [ROUTER]: No match for '{text}'. Falling back to original code behaviour (LLM/RAG).")

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

            # Parse PLAY_AUDIO tag if present
            audio_match = re.search(r'\[\s*PLAY_AUDIO:\s*([a-zA-Z0-9_\-\./]+)(?:\.raw)?\s*\]', reply, re.I)
            if audio_match:
                audio_filename = audio_match.group(1).strip()
                if not audio_filename.endswith(".raw"):
                    audio_filename += ".raw"
                print(f"🎯 [PLAY_AUDIO TAG DETECTED IN STATIC REPLY]: {audio_filename}")
                
                # Retrieve translation/transcription to log to DB
                transcription = _AUDIO_TRANSCRIPTIONS.get(audio_filename, reply)
                await save_message(self.conversation, "bot", transcription)
                
                if self.tts_task and not self.tts_task.done():
                    self.tts_task.cancel()
                    try:
                        await self.tts_task
                    except asyncio.CancelledError:
                        pass
                        
                self.tts_task = asyncio.create_task(self._stream_local_audio_file(audio_filename))
            else:
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
            text = re.sub(r'\[\s*PLAY_AUDIO:[^\]]*\]', '', text, flags=re.I)
            text = re.sub(r'PLAY_AUDIO:\s*[a-zA-Z0-9_\-\./]*(?:\.raw)?', '', text, flags=re.I)
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
                sentence_buffer += chunk

                # if tts_language == "gu":
                #     boundary = re.search(r'[!?।]\s|[.]\s+(?=[A-Z\u0A80-\u0AFF])', sentence_buffer)
                # else:
                #     boundary = re.search(r'[.!?।]\s|[,;]\s+(?=\S)', sentence_buffer)

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
                        
                        # --- HUMAN RHYTHM LOGIC ---
                        if self.language != "gu":
                            # 1. Add a natural "thinking" pause after initial greetings or filler words
                            tts_text = re.sub(r'^(Hello|Hi|Namaste|Ji|Acha|Haan|Okay|Suniye),', r'\1, <break time="250ms"/>', sentence, flags=re.I)
                            # 2. Add subtle 'thinking' breaks at commas so Arjun doesn't rush like a robot
                            tts_text = tts_text.replace(",", ", <break time='200ms'/>")
                            # 3. Add a slight lift in pitch for questions
                            if tts_text.endswith("?"):
                                tts_text = f"<prosody pitch='+3%'>{tts_text}</prosody>"
                        else:
                            # Keep Gujarati fast and direct as per existing settings
                            tts_text = sentence

                        try:
                            ulaw = await asyncio.wait_for(
                                loop.run_in_executor(
                                    None,
                                    lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
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
                
                # --- HUMAN RHYTHM LOGIC ---
                if self.language != "gu":
                    tts_text = re.sub(r'^(Hello|Hi|Namaste|Ji|Acha|Haan|Okay|Suniye),', r'\1, <break time="250ms"/>', sentence, flags=re.I)
                    tts_text = tts_text.replace(",", ", <break time='200ms'/>")
                    if tts_text.endswith("?"):
                        tts_text = f"<prosody pitch='+3%'>{tts_text}</prosody>"
                else:
                    tts_text = sentence

                try:
                    ulaw = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda s=tts_text, l=tts_language: self._synthesize_ulaw(s, l)
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

        play_override_audio = None
        if full_response:
            audio_match = re.search(r'\[\s*PLAY_AUDIO:\s*([a-zA-Z0-9_\-\.]+)(?:\.raw)?\s*\]', full_response, re.I)
            if audio_match:
                play_override_audio = audio_match.group(1).strip()
                if not play_override_audio.endswith(".raw"):
                    play_override_audio += ".raw"
                print(f"🎯 [PLAY_AUDIO TAG DETECTED]: {play_override_audio}")
            full_response = re.sub(r'\[\s*PLAY_AUDIO:[^\]]*\]', '', full_response, flags=re.I).strip()

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

        # ── FLOW FOLLOW-UP ────────────────────────────────────────────────────
        # After the LLM answers an out-of-script question, stream the current
        # phase's pre-recorded audio question to snap the call back on-track.
        # NOTE: _stream_local_audio_file prepends self.language automatically,
        #       so pass bare filenames (no lang prefix) here.
        if not prep_result.get("auto_disconnect"):
            _phase_audio = None
            if play_override_audio:
                _phase_audio = play_override_audio
                # Map audio back to phase and update phase in state
                AUDIO_TO_PHASE = {
                    "step2_confirm_interest.raw": "CONFIRM_INTEREST",
                    "step3_ask_timeline.raw": "ASK_TIMELINE",
                    "step4_ask_callback.raw": "CONFIRM_CALLBACK",
                    "step5_ask_time.raw": "ASK_CALLBACK_TIME",
                    "step7_confirm_testdrive.raw": "CONFIRM_TESTDRIVE",
                }
                new_phase = AUDIO_TO_PHASE.get(play_override_audio)
                if new_phase:
                    print(f"🔄 [PLAY_AUDIO PHASE UPDATE]: Updating phase to {new_phase}")
                    try:
                        session = await sync_to_async(
                            lambda: ConversationSession.objects.filter(session_id=self.session_id).first()
                        )()
                        if session:
                            state = session.state or {}
                            state["current_phase"] = new_phase
                            session.state = state
                            await sync_to_async(session.save)()
                            self.current_phase = new_phase
                    except Exception as phase_err:
                        print(f"⚠️ Failed to update phase via PLAY_AUDIO tag: {phase_err}")
            elif self.current_phase:
                _phase_audio = {
                    "CONFIRM_INTEREST":  "step2_confirm_interest.raw",
                    "ASK_TIMELINE":      "step3_ask_timeline.raw",
                    "CONFIRM_CALLBACK":  "step4_ask_callback.raw",
                    "ASK_CALLBACK_TIME": "step5_ask_time.raw",
                    "CONFIRM_TESTDRIVE": "step7_confirm_testdrive.raw",
                }.get(self.current_phase)

            if _phase_audio:
                print(f"🔁 [FLOW FOLLOW-UP]: Playing {_phase_audio}")
                await asyncio.sleep(0.3)
                await self._stream_local_audio_file(_phase_audio)
        # ─────────────────────────────────────────────────────────────────────

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

    # ================= TTS HELPERS =================


    def _get_synthesizer(self, language: str):
        """Reuses cached synthesizer or builds a new one if needed."""
        if language in self._tts_synthesizers:
            return self._tts_synthesizers[language]
            
        synthesizer = self._build_tts_synthesizer(language)
        # Pre-heat the connection to avoid handshake delay on first speak
        try:
            conn = speechsdk.Connection.from_speech_synthesizer(synthesizer)
            conn.open(True)
        except Exception as e:
            print(f"⚠️ TTS Connection pre-heat failed: {e}")
            
        self._tts_synthesizers[language] = synthesizer
        return synthesizer

    def _build_tts_synthesizer(self, language: str = None):
        lang = language or self.language
        speech_config = speechsdk.SpeechConfig(
            subscription=os.getenv("AZURE_SPEECH_KEY"),
            region=os.getenv("AZURE_SPEECH_REGION")
        )
        speech_config.speech_synthesis_voice_name = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["en"])
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
        )
        # Latency optimization for TTS
        speech_config.set_property_by_name("SpeechServiceResponse_RequestStreamingResponse", "true")
        return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    def _synthesize_ulaw(self, text: str, language: str = None) -> bytes:
        lang = language or self.language
        if lang == "gu":
            try:
                ssml = build_ssml(text, lang)
                synthesizer = self._get_synthesizer(lang)
                result = synthesizer.speak_ssml_async(ssml).get()
                
                if result.reason == speechsdk.ResultReason.Canceled:
                    details = result.cancellation_details
                    print("❌ Azure TTS Canceled:", details.reason, details.error_details)
                    return b""
                    
                pcm = result.audio_data
                pcm = strip_wav_header(pcm)
                
                if len(pcm) % 2 != 0:
                    pcm = pcm[:-1]
                    
                pcm = _amplify_pcm(pcm, gain=0.6)
                return encode_g711(pcm)
            except Exception as azure_err:
                print(f"❌ Azure synthesis failed for Gujarati: {azure_err}")
                return b""

        voice_id = ELEVENLABS_VOICE_MAP.get(lang, ELEVENLABS_VOICE_MAP["en"])
        
        # Strip any SSML/XML tags before sending to ElevenLabs
        clean_text = re.sub(r'<[^>]*>', '', text).strip()
        if not clean_text:
            return b""
            
        try:
            audio_generator = ELEVENLABS_CLIENT.text_to_speech.convert(
                voice_id=voice_id,
                text=clean_text,
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
                return encode_g711(pcm)
            else:
                print(f"❌ ElevenLabs returned empty audio for text: {clean_text[:40]}")
        except Exception as e:
            print(f"❌ ElevenLabs synthesis failed: {e}. Falling back to Azure TTS.")

        # Fallback to Azure Speech SDK
        try:
            ssml = build_ssml(text, lang)
            synthesizer = self._get_synthesizer(lang)
            result = synthesizer.speak_ssml_async(ssml).get()
            
            if result.reason == speechsdk.ResultReason.Canceled:
                details = result.cancellation_details
                print("❌ Azure TTS Canceled:", details.reason, details.error_details)
                return b""
                
            pcm = result.audio_data
            pcm = strip_wav_header(pcm)
            
            if len(pcm) % 2 != 0:
                pcm = pcm[:-1]
                
            pcm = _amplify_pcm(pcm, gain=0.6)
            return encode_g711(pcm)
        except Exception as azure_err:
            print(f"❌ Azure fallback synthesis also failed: {azure_err}")
            return b""

    async def _stream_ulaw(self, ulaw: bytes):
        if not ulaw:
            return

        loop = asyncio.get_event_loop()

        # for _ in range(2):
        #     if not self.is_bot_speaking:
        #         return
        #     await self._send_media_frame(SILENCE_FRAME)
        #     await asyncio.sleep(0.020)

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

        # for _ in range(2):
        #     if not self.is_bot_speaking:
        #         return
        #     await self._send_media_frame(SILENCE_FRAME)
        #     await asyncio.sleep(0.020)

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
            # Cleanly ignore disconnected protocol exceptions on user hangup
            pass

    # ================= TTS (static replies / intro) =================

    async def _synthesize_and_cache_greeting(self, text: str, tts_language: str = None):
        """
        Check for a local language-specific greeting file first. 
        If it exists, play it instantly. Otherwise, synthesize and cache.
        """
        import os
        lang = tts_language or self.language
        greeting_file = "hosp_step1_greeting.raw" if getattr(self, "strategy_key", None) == "hospital_minimal" else f"{lang}_step1_greeting.raw"
        local_greeting = os.path.join("mp3_responses", greeting_file)
        if os.path.exists(local_greeting):
            print(f"🚀 INSTANT GREETING: Found local file {local_greeting}")
            with open(local_greeting, "rb") as f:
                ulaw = f.read()
            await self._stream_cached_greeting(ulaw)
            return

        loop = asyncio.get_event_loop()
        try:
            ulaw = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._synthesize_ulaw(text, lang)),
                timeout=15
            )
        except Exception as e:
            print(f"❌ Greeting synthesis error: {e}")
            ulaw = b""

        if ulaw:
            _GREETING_AUDIO_CACHE[f"{self.agent_id}_{lang}"] = ulaw
            print(f"💾 Greeting audio cached for agent {self.agent_id}_{lang} ({len(ulaw)} bytes)")

        await self._stream_cached_greeting(ulaw)

    async def _stream_cached_greeting(self, ulaw: bytes, **_):
        """Stream pre-synthesized greeting bytes — zero Azure TTS round-trip."""
        if not ulaw:
            return
        self.is_bot_speaking = True
        self._mark_bot_speaking_start()
        try:
            await self._stream_ulaw(ulaw)
        finally:
            self.is_bot_speaking = False
            self._mark_bot_speaking_end()















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
                            timeout=15
                        )
                    except asyncio.TimeoutError:
                        print(f"❌ TTS TIMEOUT for sentence: {sentence[:40]}")
                        ulaw = b""
                    await audio_queue.put(ulaw)
                    # Natural inter-sentence pause (skip after last sentence)
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
            user_phone = self.user_number  # Capture phone for auto-dialer
            
            import threading
            def _run_lead_analysis():
                try:
                    from conversations.services.lead_analyzer import analyze_lead
                    analyze_lead(conv_id)
                except Exception as e:
                    print(f"❌ Lead analysis background error: {e}")
                
                # 🔄 AUTO-DIALER FALLBACK: Trigger next call if campaign is active
                try:
                    from bot.views import on_call_ended, _campaign_active
                    if _campaign_active:
                        print(f"🔄 AUTO-DIALER (disconnect fallback): Triggering next call for {user_phone}")
                        on_call_ended(user_phone)
                except Exception as e:
                    print(f"⚠️ Auto-dialer fallback error: {e}")

            threading.Thread(target=_run_lead_analysis, daemon=True).start()
            print("📊 Lead analysis started in background...")

       