# import tempfile
# import re

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import AllowAny
# from rest_framework.decorators import api_view

# from django.shortcuts import render

# from agents.models import VoiceAgent
# from assistant.management.commands.stt import speech_to_text
# from conversations.services.core.dialogue_engine import process_message
# from conversations.services.speech_service import synthesize_to_base64
# from conversations.services.translator_service import detect_language, translate_text
# from .models import Conversation, Message
# from .serializers import ConversationSerializer, MessageSerializer


# # ======================================================
# # DEMO PAGE
# # ======================================================

# def demo_page(request):
#     return render(request, "demo_chat.html")


# # ======================================================
# # AUTHENTICATED AGENT CHAT
# # ======================================================

# class ChatAPIView(APIView):
#     authentication_classes = []
#     permission_classes = []

#     def post(self, request, agent_id):
#         api_key = request.headers.get("X-API-KEY")

#         agent = VoiceAgent.objects.filter(
#             id=agent_id,
#             api_key=api_key,
#             is_active=True
#         ).first()

#         if not agent:
#             return Response({"error": "Unauthorized"}, status=401)

#         message = request.data.get("message")
#         if not message:
#             return Response({"error": "Message required"}, status=400)

#         session_id = request.data.get("session_id")

#         reply, session_id = process_message(
#             agent=agent,
#             message=message,
#             session_id=session_id
#         )

#         return Response({
#             "agent": agent.name,
#             "reply": reply,
#             "session_id": session_id
#         })


# # ======================================================
# # TTS HELPER
# # ======================================================

# def clean_for_tts(text: str) -> str:
#     if not text:
#         return ""

#     # Remove emojis
#     text = re.sub(r"[\U00010000-\U0010ffff]", "", text)

#     # Remove markdown **bold**
#     text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

#     # Remove remaining markdown symbols
#     text = re.sub(r"[*_`~>#]", "", text)

#     # Normalize spaces
#     text = re.sub(r"\s+", " ", text).strip()

#     return text


# # ======================================================
# # DEMO CHAT — Insurance Bot (Auto-Activated)
# # ======================================================

# class DemoChatAPIView(APIView):
#     permission_classes = [AllowAny]
#     authentication_classes = []

#     def post(self, request):
#         session_id = request.data.get("session_id")
#         language = "en"

#         industry_id = request.data.get("industry_id")
#         role_id = request.data.get("role_id")

#         print("Industry ID:", industry_id)
#         print("Role ID:", role_id)

#         bot = None

#         # ✅ Priority 1: Find by role_id
#         if role_id:
#             bot = VoiceAgent.objects.filter(
#                 role_template_id=role_id,
#                 is_demo=True,
#                 is_active=True
#             ).first()

#         # ✅ Priority 2: Find by industry_id
#         if not bot and industry_id:
#             bot = VoiceAgent.objects.filter(
#                 role_template__industry_id=industry_id,
#                 is_demo=True,
#                 is_active=True
#             ).first()

#         # ✅ Final fallback
#         if not bot:
#             bot = VoiceAgent.objects.filter(
#                 is_demo=True,
#                 is_active=True
#             ).first()

#         if not bot:
#             return Response({"error": "No demo bot found"}, status=404)

#         print("SELECTED BOT:", bot.role_template.role_name)

#         if not bot:
#             return Response({"error": "No Insurance Advisor bot found. Please configure one in admin."}, status=404)

#         audio_file = request.FILES.get("audio")
#         message = request.data.get("message")

#         # 🎧 AUDIO → STT
#         if audio_file:
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
#                 for chunk in audio_file.chunks():
#                     f.write(chunk)
#                 audio_path = f.name

#             message = speech_to_text(audio_path)

#             if not message:
#                 fallback = "Sorry, I could not hear you clearly. Please try again."
#                 return Response({
#                     "reply": fallback,
#                     "audio": synthesize_to_base64(fallback, language=language, mode="web"),
#                     "session_id": session_id
#                 })

#         # 🟢 GREETING
#         if not session_id and not message:
#             message = "start conversation"

#         if not message:
#             return Response({"error": "message or audio required"}, status=400)

#         # Auto detect language from user message
#         if message and message != "start conversation":
#             language = detect_language(message)
#         else:
#             language = "en"

#         # Translate user message → English for AI
#         message_for_ai = message
#         if language != "en":
#             message_for_ai = translate_text(message, from_lang=language, to_lang="en")
#         reply, session_id = process_message(
#             agent=bot,
#             message=message_for_ai,
#             session_id=session_id
#         )

#         # Translate AI reply → user's language
#         reply_for_user = reply
#         if language != "en":
#             reply_for_user = translate_text(reply, from_lang="en", to_lang=language)

#         clean_reply = clean_for_tts(reply_for_user)

#         return Response({
#             "user_text": message,
#             "reply": reply_for_user,
#             "audio": synthesize_to_base64(clean_reply, language=language, mode="web"),
#             "session_id": session_id
#         })


# # ======================================================
# # CONVERSATION HISTORY APIs
# # ======================================================

# # Get all conversations (for dashboard)
# @api_view(["GET"])
# def get_conversations(request):
#     conversations = Conversation.objects.all().order_by("-started_at")
#     serializer = ConversationSerializer(conversations, many=True)
#     return Response({
#         "count": conversations.count(),
#         "data": serializer.data
#     })


# # Get full conversation (messages)
# @api_view(["GET"])
# def get_conversation_messages(request, session_id):
#     try:
#         conversation = Conversation.objects.get(session_id=session_id)
#     except Conversation.DoesNotExist:
#         return Response({"error": "Conversation not found"}, status=404)

#     messages = Message.objects.filter(conversation=conversation).order_by("created_at")
#     serializer = MessageSerializer(messages, many=True)

#     return Response({
#         "session_id": conversation.session_id,
#         "user_number": conversation.user_number,
#         "messages": serializer.data
#     })




# # ======================================================
# # CALL ANALYTICS DASHBOARD
# # ======================================================

# from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField, Q
# from django.http import JsonResponse
# from collections import OrderedDict

# def call_analytics_page(request):
#     return render(request, "call_analytics.html")


# @api_view(["GET"])
# def call_analytics_data(request):
#     """
#     Returns all voice-call conversations grouped by user_number,
#     with summary stats for the dashboard.
#     """
#     conversations = Conversation.objects.all().order_by("-started_at")

#     total_sessions = conversations.count()

#     total_messages = Message.objects.filter(
#         conversation__in=conversations
#     ).count()

#     # Average duration (only completed calls)
#     completed = conversations.filter(ended_at__isnull=False)
#     avg_dur = None
#     if completed.exists():
#         durations = []
#         for c in completed:
#             delta = (c.ended_at - c.started_at).total_seconds()
#             if delta > 0:
#                 durations.append(delta)
#         avg_dur = round(sum(durations) / len(durations)) if durations else 0

#     # Group by user_number
#     number_map = OrderedDict()
#     for c in conversations:
#         num = c.user_number or "unknown"
#         if num not in number_map:
#             number_map[num] = {
#                 "user_number": num,
#                 "session_count": 0,
#                 "last_call": None,
#                 "sessions": [],
#             }

#         msg_count = c.messages.count()
#         duration = None
#         if c.ended_at and c.started_at:
#             duration = round((c.ended_at - c.started_at).total_seconds())

#         number_map[num]["session_count"] += 1

#         if number_map[num]["last_call"] is None:
#             number_map[num]["last_call"] = c.started_at.isoformat()

#         number_map[num]["sessions"].append({
#             "session_id": c.session_id,
#             "started_at": c.started_at.isoformat(),
#             "ended_at": c.ended_at.isoformat() if c.ended_at else None,
#             "message_count": msg_count,
#             "duration_seconds": duration,
#         })

#     return Response({
#         "total_sessions": total_sessions,

#         "total_messages": total_messages,
#         "avg_duration_seconds": avg_dur or 0,
#         "numbers": list(number_map.values()),
#     })


# @api_view(["GET"])
# def call_analytics_session(request, session_id):
#     """
#     Returns full message list for a specific session.
#     """
#     try:
#         conversation = Conversation.objects.get(session_id=session_id)
#     except Conversation.DoesNotExist:
#         return Response({"error": "Session not found"}, status=404)

#     messages = Message.objects.filter(conversation=conversation).order_by("created_at")

#     duration = None
#     if conversation.ended_at and conversation.started_at:
#         duration = round((conversation.ended_at - conversation.started_at).total_seconds())

#     return Response({
#         "session_id": conversation.session_id,
#         "user_number": conversation.user_number,
#         "started_at": conversation.started_at.isoformat(),
#         "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
#         "duration_seconds": duration,
#         "messages": [
#             {
#                 "role": m.role,
#                 "text": m.text,
#                 "created_at": m.created_at.isoformat(),
#             }
#             for m in messages
#         ],
#     })


# # ======================================================
# # PER-BOT ANALYTICS (additive — existing APIs untouched)
# # ======================================================

# @api_view(["GET"])
# def call_analytics_per_bot(request):
#     """
#     Returns analytics broken down by each bot (VoiceAgent).
#     Computes per-bot: sessions, durations, messages, activity timeline.
#     """
#     from agents.models import VoiceAgent

#     bots = VoiceAgent.objects.filter(is_active=True)
#     bot_stats = []

#     for bot in bots:
#         convos = Conversation.objects.filter(agent=bot)
#         total_sessions = convos.count()

#         if total_sessions == 0:
#             continue


#         total_messages = Message.objects.filter(conversation__agent=bot).count()

#         # Duration stats (only completed calls)
#         completed = convos.filter(ended_at__isnull=False)
#         durations = []
#         for c in completed:
#             delta = (c.ended_at - c.started_at).total_seconds()
#             if delta > 0:
#                 durations.append(delta)

#         avg_dur = round(sum(durations) / len(durations)) if durations else 0
#         total_dur = round(sum(durations)) if durations else 0
#         min_dur = round(min(durations)) if durations else 0
#         max_dur = round(max(durations)) if durations else 0

#         # Messages per session
#         avg_msgs = round(total_messages / total_sessions, 1) if total_sessions else 0

#         # Activity timeline
#         first_convo = convos.order_by("started_at").first()
#         last_convo = convos.order_by("-started_at").first()

#         bot_stats.append({
#             "bot_id": str(bot.id),
#             "bot_name": bot.name,
#             "industry": bot.industry.name if bot.industry else "—",
#             "company": bot.company_name or "—",
#             "total_sessions": total_sessions,

#             "total_messages": total_messages,
#             "avg_duration_seconds": avg_dur,
#             "total_duration_seconds": total_dur,
#             "min_duration_seconds": min_dur,
#             "max_duration_seconds": max_dur,
#             "avg_messages_per_session": avg_msgs,
#             "first_call": first_convo.started_at.isoformat() if first_convo else None,
#             "last_call": last_convo.started_at.isoformat() if last_convo else None,
#         })

#     # Sort by total sessions descending
#     bot_stats.sort(key=lambda x: x["total_sessions"], reverse=True)

#     return Response({"bots": bot_stats})


# # ======================================================
# # LEAD ANALYSIS DASHBOARD + API
# # ======================================================

# from .models import LeadAnalysis
# from .serializers import LeadAnalysisSerializer


# def lead_analysis_page(request):
#     return render(request, "lead_analysis.html")


# @api_view(["GET"])
# def lead_analysis_data(request):
#     """
#     Returns all lead analyses with summary stats.
#     Query params:
#         ?level=hot|warm|cold|not_interested  — filter by lead level
#         ?agent=<agent_id>                     — filter by bot/agent
#     """
#     leads = LeadAnalysis.objects.select_related(
#         "conversation", "agent"
#     ).order_by("-analyzed_at")

#     # Filters
#     level = request.GET.get("level")
#     if level:
#         leads = leads.filter(lead_level=level)

#     agent_id = request.GET.get("agent")
#     if agent_id:
#         leads = leads.filter(agent_id=agent_id)

#     # Stats
#     total = leads.count()
#     hot = leads.filter(lead_level="hot").count()
#     warm = leads.filter(lead_level="warm").count()
#     cold = leads.filter(lead_level="cold").count()
#     not_interested = leads.filter(lead_level="not_interested").count()

#     serializer = LeadAnalysisSerializer(leads, many=True)

#     return Response({
#         "total": total,
#         "stats": {
#             "hot": hot,
#             "warm": warm,
#             "cold": cold,
#             "not_interested": not_interested,
#         },
#         "leads": serializer.data,
#     })


# @api_view(["GET"])
# def lead_analysis_detail(request, session_id):
#     """
#     Returns lead analysis for a specific session, including full conversation.
#     """
#     try:
#         conversation = Conversation.objects.get(session_id=session_id)
#     except Conversation.DoesNotExist:
#         return Response({"error": "Conversation not found"}, status=404)

#     try:
#         lead = LeadAnalysis.objects.select_related(
#             "conversation", "agent"
#         ).get(conversation=conversation)
#     except LeadAnalysis.DoesNotExist:
#         return Response({"error": "Lead analysis not available for this session"}, status=404)

#     messages = Message.objects.filter(conversation=conversation).order_by("created_at")

#     return Response({
#         "lead": LeadAnalysisSerializer(lead).data,
#         "messages": [
#             {
#                 "role": m.role,
#                 "text": m.text,
#                 "created_at": m.created_at.isoformat(),
#             }
#             for m in messages
#         ],
#     })


# # ======================================================
# # TELECOM CDR WEBHOOK (POST — receives call data after call ends)
# # ======================================================

# from .models import CallDetailRecord
# from datetime import datetime as dt


# @api_view(["POST"])
# def telecom_cdr_webhook(request):
#     """
#     Receives Call Detail Record from telecom system after each call ends.
#     Matches recording_file_name (minus .wav) to Conversation.session_id.
#     No authentication required (as per telecom team agreement).
#     """
#     data = request.data

#     # Validate required fields
#     required = ["call_id", "phone_number", "calldate", "did", "uniqueid"]
#     missing = [f for f in required if f not in data]
#     if missing:
#         return Response(
#             {"error": f"Missing required fields: {', '.join(missing)}"},
#             status=400
#         )

#     # Check for duplicate (by uniqueid)
#     if CallDetailRecord.objects.filter(uniqueid=data["uniqueid"]).exists():
#         return Response(
#             {"status": "duplicate", "message": "CDR already received for this uniqueid"},
#             status=200
#         )

#     # Parse dates safely
#     try:
#         calldate = dt.strptime(data["calldate"], "%Y-%m-%d %H:%M:%S")
#     except (ValueError, TypeError):
#         calldate = None

#     answer_time = None
#     if data.get("answer_time"):
#         try:
#             answer_time = dt.strptime(data["answer_time"], "%Y-%m-%d %H:%M:%S")
#         except (ValueError, TypeError):
#             pass

#     # Extract session_id from recording_file_name (strip .wav extension)
#     recording_file = data.get("recording_file_name", "")
#     session_id = recording_file.replace(".wav", "").strip() if recording_file else ""
    
#     print(f"🔍 DEBUG: Attempting to match CDR. Telecom Filename: '{recording_file}' -> Extracted ID: '{session_id}'")

#     # Try to match to existing Conversation
#     conversation = None
#     matched = False
#     if session_id:
#         try:
#             conversation = Conversation.objects.get(session_id=session_id)
#             matched = True
#             print(f"✅ MATCH FOUND! Conversation ID: {conversation.id}")
#         except Conversation.DoesNotExist:
#             print(f"❌ NO MATCH: Could not find any Conversation with session_id='{session_id}'")
    
#     raw_phone = data.get("phone_number", "")
#     if raw_phone:
#         # Extract last 10 digits to handle +91, 0, etc.
#         clean_phone = "".join(filter(str.isdigit, raw_phone))[-10:]
        
#         if clean_phone:
#             # Find the most recent conversation for this phone number
#             conversation = Conversation.objects.filter(
#                 user_number__icontains=clean_phone
#             ).order_by("-started_at").first()

#     if conversation:
#         matched = True
#         print(f"✅ SUCCESS: CDR Matched to Lead! Phone: {raw_phone} -> Conv ID: {conversation.id}")
#     else:
#         print(f"⚠️ UNMATCHED: CDR saved but no matching Lead found for Phone: {raw_phone}")

#     # Save CDR
#     cdr = CallDetailRecord.objects.create(
#         conversation=conversation,
#         telecom_call_id=data.get("call_id", 0),
#         phone_number=raw_phone,
#         calldate=calldate,
#         did=data.get("did", ""),
#         duration=data.get("duration", 0),
#         disposition=data.get("disposition", "ANSWERED"),
#         call_type=data.get("call_type", "OUTBOUND"),
#         answer_time=answer_time,
#         uniqueid=data["uniqueid"],
#         recording_file_name=data.get("recording_file_name", ""),
#         matched=matched,
#     )

#     result = {
#         "status": "success",
#         "cdr_id": cdr.id,
#         "matched": matched,
#     }

#     if matched:
#         result["conversation_id"] = conversation.id
#         result["agent_name"] = conversation.agent.name if conversation.agent else None
#         print(f"📞 CDR RECEIVED & MATCHED: {data['phone_number']} → session {session_id[:12]}...")
#     else:
#         print(f"📞 CDR RECEIVED (unmatched): {data['phone_number']} — recording: {recording_file}")

#     return Response(result, status=201)


# @api_view(["GET"])
# def telecom_cdr_list(request):
#     """
#     Returns all CDR records with optional filters.
#     Query params: ?matched=true|false  &did=+91...  &disposition=ANSWERED
#     """
#     cdrs = CallDetailRecord.objects.select_related("conversation", "conversation__agent").order_by("-received_at")

#     # Filters
#     matched = request.GET.get("matched")
#     if matched is not None:
#         cdrs = cdrs.filter(matched=matched.lower() == "true")

#     did = request.GET.get("did")
#     if did:
#         cdrs = cdrs.filter(did=did)

#     disposition = request.GET.get("disposition")
#     if disposition:
#         cdrs = cdrs.filter(disposition=disposition)

#     total = cdrs.count()
#     matched_count = cdrs.filter(matched=True).count()
#     unmatched_count = cdrs.filter(matched=False).count()

#     records = []
#     for cdr in cdrs[:200]:  # Limit to 200 records
#         record = {
#             "id": cdr.id,
#             "telecom_call_id": cdr.telecom_call_id,
#             "phone_number": cdr.phone_number,
#             "calldate": cdr.calldate.isoformat() if cdr.calldate else None,
#             "did": cdr.did,
#             "duration": cdr.duration,
#             "disposition": cdr.disposition,
#             "call_type": cdr.call_type,
#             "answer_time": cdr.answer_time.isoformat() if cdr.answer_time else None,
#             "uniqueid": cdr.uniqueid,
#             "recording_file_name": cdr.recording_file_name,
#             "matched": cdr.matched,
#             "received_at": cdr.received_at.isoformat(),
#         }
#         if cdr.matched and cdr.conversation:
#             record["session_id"] = cdr.conversation.session_id
#             record["agent_name"] = cdr.conversation.agent.name if cdr.conversation.agent else None
#         records.append(record)

#     return Response({
#         "total": total,
#         "matched": matched_count,
#         "unmatched": unmatched_count,
#         "records": records,
#     })















from bot.services.azure_storage import AzureBlobService
import tempfile
import re

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from agents.models import VoiceAgent
from assistant.management.commands.stt import speech_to_text
from conversations.services.core.dialogue_engine import process_message
from conversations.services.speech_service import synthesize_to_base64
from conversations.services.translator_service import detect_language, translate_text
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer


# ======================================================
# DEMO PAGE
# ======================================================

def demo_page(request):
    return render(request, "demo_chat.html")


# ======================================================
# AUTHENTICATED AGENT CHAT
# ======================================================

class ChatAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, agent_id):
        api_key = request.headers.get("X-API-KEY")

        agent = VoiceAgent.objects.filter(
            id=agent_id,
            api_key=api_key,
            is_active=True
        ).first()

        if not agent:
            return Response({"error": "Unauthorized"}, status=401)

        message = request.data.get("message")
        if not message:
            return Response({"error": "Message required"}, status=400)

        session_id = request.data.get("session_id")

        reply, session_id = process_message(
            agent=agent,
            message=message,
            session_id=session_id
        )

        return Response({
            "agent": agent.name,
            "reply": reply,
            "session_id": session_id
        })


# ======================================================
# TTS HELPER
# ======================================================

def clean_for_tts(text: str) -> str:
    if not text:
        return ""

    # Remove emojis
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)

    # Remove markdown **bold**
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

    # Remove remaining markdown symbols
    text = re.sub(r"[*_`~>#]", "", text)

    # Normalize spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ======================================================
# DEMO CHAT — Insurance Bot (Auto-Activated)
# ======================================================

class DemoChatAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        session_id = request.data.get("session_id")
        language = "en"

        industry_id = request.data.get("industry_id")
        role_id = request.data.get("role_id")

        print("Industry ID:", industry_id)
        print("Role ID:", role_id)

        bot = None

        # ✅ Priority 1: Find by role_id
        if role_id:
            bot = VoiceAgent.objects.filter(
                role_template_id=role_id,
                is_demo=True,
                is_active=True
            ).first()

        # ✅ Priority 2: Find by industry_id
        if not bot and industry_id:
            bot = VoiceAgent.objects.filter(
                role_template__industry_id=industry_id,
                is_demo=True,
                is_active=True
            ).first()

        # ✅ Final fallback
        if not bot:
            bot = VoiceAgent.objects.filter(
                is_demo=True,
                is_active=True
            ).first()

        if not bot:
            return Response({"error": "No demo bot found"}, status=404)

        print("SELECTED BOT:", bot.role_template.role_name)

        if not bot:
            return Response({"error": "No Insurance Advisor bot found. Please configure one in admin."}, status=404)

        audio_file = request.FILES.get("audio")
        message = request.data.get("message")

        # 🎧 AUDIO → STT
        if audio_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)
                audio_path = f.name

            message = speech_to_text(audio_path)

            if not message:
                fallback = "Sorry, I could not hear you clearly. Please try again."
                return Response({
                    "reply": fallback,
                    "audio": synthesize_to_base64(fallback, language=language, mode="web"),
                    "session_id": session_id
                })

        # 🟢 GREETING
        if not session_id and not message:
            message = "start conversation"

        if not message:
            return Response({"error": "message or audio required"}, status=400)

        # Auto detect language from user message
        if message and message != "start conversation":
            language = detect_language(message)
        else:
            language = "en"

        # Translate user message → English for AI
        message_for_ai = message
        if language != "en":
            message_for_ai = translate_text(message, from_lang=language, to_lang="en")
        reply, session_id = process_message(
            agent=bot,
            message=message_for_ai,
            session_id=session_id
        )

        # Translate AI reply → user's language
        reply_for_user = reply
        if language != "en":
            reply_for_user = translate_text(reply, from_lang="en", to_lang=language)

        clean_reply = clean_for_tts(reply_for_user)

        return Response({
            "user_text": message,
            "reply": reply_for_user,
            "audio": synthesize_to_base64(clean_reply, language=language, mode="web"),
            "session_id": session_id
        })


# ======================================================
# CONVERSATION HISTORY APIs
# ======================================================

# Get all conversations (for dashboard)
@api_view(["GET"])
def get_conversations(request):
    conversations = Conversation.objects.all().order_by("-started_at")
    serializer = ConversationSerializer(conversations, many=True)
    return Response({
        "count": conversations.count(),
        "data": serializer.data
    })


# Get full conversation (messages)
@api_view(["GET"])
def get_conversation_messages(request, session_id):
    try:
        conversation = Conversation.objects.get(session_id=session_id)
    except Conversation.DoesNotExist:
        return Response({"error": "Conversation not found"}, status=404)

    messages = Message.objects.filter(conversation=conversation).order_by("created_at")
    serializer = MessageSerializer(messages, many=True)

    return Response({
        "session_id": conversation.session_id,
        "user_number": conversation.user_number,
        "messages": serializer.data
    })


@api_view(["GET"])
def get_campaign_lead_conversation(request):
    """
    Fetches the conversation transcript for a specific lead in a campaign.
    Query params: campaign_id, phone
    """
    campaign_id = request.query_params.get("campaign_id")
    phone = request.query_params.get("phone")

    if not campaign_id or not phone:
        return Response({"error": "campaign_id and phone are required"}, status=400)

    # Normalize phone number
    from bot.views import _normalize_phone
    phone = _normalize_phone(phone)

    try:
        # Find the conversation. Since we added campaign_id on Conversation model, we can filter by it!
        conversation = Conversation.objects.filter(campaign_id=campaign_id, user_number=phone).order_by("-started_at").first()
        if not conversation:
            # Fallback to search by user_number but restrict to conversations that started on or after the campaign's started_at timestamp.
            # This prevents matching old, unrelated conversations from previous campaigns/tests.
            from bot.models import Campaign
            campaign = Campaign.objects.filter(id=campaign_id).first()
            if campaign:
                conversation = Conversation.objects.filter(
                    user_number=phone,
                    started_at__gte=campaign.started_at
                ).order_by("-started_at").first()
            else:
                conversation = Conversation.objects.filter(user_number=phone).order_by("-started_at").first()

        if not conversation:
            return Response({"error": "No conversation found for this number"}, status=404)

        # Get messages
        messages = Message.objects.filter(conversation=conversation).order_by("created_at")
        
        # Serialize messages
        msg_data = []
        for m in messages:
            msg_data.append({
                "role": m.role,
                "text": m.text,
                "created_at": m.created_at.isoformat()
            })

        # Include LeadAnalysis summary if available
        lead_summary = ""
        lead_level = "unknown"
        try:
            if hasattr(conversation, 'lead_analysis') and conversation.lead_analysis:
                lead_summary = conversation.lead_analysis.summary
                lead_level = conversation.lead_analysis.lead_level
        except:
            pass

        return Response({
            "session_id": conversation.session_id,
            "user_number": conversation.user_number,
            "started_at": conversation.started_at.isoformat(),
            "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
            "lead_level": lead_level,
            "lead_summary": lead_summary,
            "messages": msg_data
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)




# ======================================================
# CALL ANALYTICS DASHBOARD
# ======================================================

from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField, Q
from django.http import JsonResponse
from collections import OrderedDict

def call_analytics_page(request):
    return render(request, "call_analytics.html")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def call_analytics_data(request):
    """
    Returns all voice-call conversations grouped by user_number,
    with summary stats for the dashboard.
    """
    conversations = Conversation.objects.all().order_by("-started_at")

    # Scope queryset to user's assigned agent if applicable
    if hasattr(request.user, "profile") and request.user.profile.assigned_agent:
        conversations = conversations.filter(agent=request.user.profile.assigned_agent)

    total_sessions = conversations.count()

    total_messages = Message.objects.filter(
        conversation__in=conversations
    ).count()

    # Average duration (only completed calls)
    completed = conversations.filter(ended_at__isnull=False)
    avg_dur = None
    if completed.exists():
        durations = []
        for c in completed:
            delta = (c.ended_at - c.started_at).total_seconds()
            if delta > 0:
                durations.append(delta)
        avg_dur = round(sum(durations) / len(durations)) if durations else 0

    # Group by user_number
    number_map = OrderedDict()
    for c in conversations:
        num = c.user_number or "unknown"
        if num not in number_map:
            number_map[num] = {
                "user_number": num,
                "session_count": 0,
                "last_call": None,
                "sessions": [],
            }

        msg_count = c.messages.count()
        duration = None
        if c.ended_at and c.started_at:
            duration = round((c.ended_at - c.started_at).total_seconds())

        number_map[num]["session_count"] += 1

        if number_map[num]["last_call"] is None:
            number_map[num]["last_call"] = c.started_at.isoformat()

        number_map[num]["sessions"].append({
            "session_id": c.session_id,
            "started_at": c.started_at.isoformat(),
            "ended_at": c.ended_at.isoformat() if c.ended_at else None,
            "message_count": msg_count,
            "duration_seconds": duration,
        })

    return Response({
        "total_sessions": total_sessions,

        "total_messages": total_messages,
        "avg_duration_seconds": avg_dur or 0,
        "numbers": list(number_map.values()),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def call_analytics_session(request, session_id):
    """
    Returns full message list for a specific session.
    """
    try:
        conversation = Conversation.objects.get(session_id=session_id)
    except Conversation.DoesNotExist:
        return Response({"error": "Session not found"}, status=404)

    # Scoping check
    if hasattr(request.user, "profile") and request.user.profile.assigned_agent:
        if conversation.agent != request.user.profile.assigned_agent:
            return Response({"error": "Forbidden: You do not have permission to access this session's data."}, status=403)

    messages = Message.objects.filter(conversation=conversation).order_by("created_at")

    duration = None
    if conversation.ended_at and conversation.started_at:
        duration = round((conversation.ended_at - conversation.started_at).total_seconds())

    return Response({
        "session_id": conversation.session_id,
        "user_number": conversation.user_number,
        "started_at": conversation.started_at.isoformat(),
        "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
        "duration_seconds": duration,
        "messages": [
            {
                "role": m.role,
                "text": m.text,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    })


# ======================================================
# PER-BOT ANALYTICS (additive — existing APIs untouched)
# ======================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def call_analytics_per_bot(request):
    """
    Returns analytics broken down by each bot (VoiceAgent).
    Computes per-bot: sessions, durations, messages, activity timeline.
    """
    from agents.models import VoiceAgent

    bots = VoiceAgent.objects.filter(is_active=True)
    if hasattr(request.user, "profile") and request.user.profile.assigned_agent:
        bots = bots.filter(id=request.user.profile.assigned_agent.id)
    bot_stats = []

    for bot in bots:
        convos = Conversation.objects.filter(agent=bot)
        total_sessions = convos.count()

        if total_sessions == 0:
            continue


        total_messages = Message.objects.filter(conversation__agent=bot).count()

        # Duration stats (only completed calls)
        completed = convos.filter(ended_at__isnull=False)
        durations = []
        for c in completed:
            delta = (c.ended_at - c.started_at).total_seconds()
            if delta > 0:
                durations.append(delta)

        avg_dur = round(sum(durations) / len(durations)) if durations else 0
        total_dur = round(sum(durations)) if durations else 0
        min_dur = round(min(durations)) if durations else 0
        max_dur = round(max(durations)) if durations else 0

        # Messages per session
        avg_msgs = round(total_messages / total_sessions, 1) if total_sessions else 0

        # Activity timeline
        first_convo = convos.order_by("started_at").first()
        last_convo = convos.order_by("-started_at").first()

        bot_stats.append({
            "bot_id": str(bot.id),
            "bot_name": bot.name,
            "industry": bot.industry.name if bot.industry else "—",
            "company": bot.company_name or "—",
            "total_sessions": total_sessions,

            "total_messages": total_messages,
            "avg_duration_seconds": avg_dur,
            "total_duration_seconds": total_dur,
            "min_duration_seconds": min_dur,
            "max_duration_seconds": max_dur,
            "avg_messages_per_session": avg_msgs,
            "first_call": first_convo.started_at.isoformat() if first_convo else None,
            "last_call": last_convo.started_at.isoformat() if last_convo else None,
        })

    # Sort by total sessions descending
    bot_stats.sort(key=lambda x: x["total_sessions"], reverse=True)

    return Response({"bots": bot_stats})


# ======================================================
# LEAD ANALYSIS DASHBOARD + API
# ======================================================

from .models import LeadAnalysis
from .serializers import LeadAnalysisSerializer


def lead_analysis_page(request):
    return render(request, "lead_analysis.html")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lead_analysis_data(request):
    """
    Returns all lead analyses with summary stats.
    Query params:
        ?level=hot|warm|cold|not_interested  — filter by lead level
        ?agent=<agent_id>                     — filter by bot/agent
    """
    leads = LeadAnalysis.objects.select_related(
        "conversation", "agent"
    ).prefetch_related(
        "conversation__messages"
    ).order_by("-analyzed_at")

    # Scope query to assigned agent if applicable
    if hasattr(request.user, "profile") and request.user.profile.assigned_agent:
        leads = leads.filter(agent=request.user.profile.assigned_agent)

    # Filters
    level = request.GET.get("level")
    if level:
        leads = leads.filter(lead_level=level)

    agent_id = request.GET.get("agent")
    if agent_id:
        leads = leads.filter(agent_id=agent_id)

    # Stats
    total = leads.count()
    hot = leads.filter(lead_level="hot").count()
    warm = leads.filter(lead_level="warm").count()
    cold = leads.filter(lead_level="cold").count()
    not_interested = leads.filter(lead_level="not_interested").count()

    serializer = LeadAnalysisSerializer(leads, many=True)

    return Response({
        "total": total,
        "stats": {
            "hot": hot,
            "warm": warm,
            "cold": cold,
            "not_interested": not_interested,
        },
        "leads": serializer.data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lead_analysis_detail(request, session_id):
    """
    Returns lead analysis for a specific session, including full conversation.
    """
    try:
        conversation = Conversation.objects.get(session_id=session_id)
    except Conversation.DoesNotExist:
        return Response({"error": "Conversation not found"}, status=404)

    # Scoping check
    if hasattr(request.user, "profile") and request.user.profile.assigned_agent:
        if conversation.agent != request.user.profile.assigned_agent:
            return Response({"error": "Forbidden: You do not have permission to access this lead's data."}, status=403)

    try:
        lead = LeadAnalysis.objects.select_related(
            "conversation", "agent"
        ).get(conversation=conversation)
    except LeadAnalysis.DoesNotExist:
        return Response({"error": "Lead analysis not available for this session"}, status=404)

    messages = Message.objects.filter(conversation=conversation).order_by("created_at")

    return Response({
        "lead": LeadAnalysisSerializer(lead).data,
        "messages": [
            {
                "role": m.role,
                "text": m.text,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_lead_level(request, session_id):
    """
    Updates the lead level for a specific conversation session.
    """
    new_level = request.data.get("lead_level")
    if not new_level or new_level not in ["hot", "warm", "cold", "not_interested"]:
        return Response({"error": "Invalid or missing lead_level. Must be one of: hot, warm, cold, not_interested"}, status=400)

    try:
        conversation = Conversation.objects.get(session_id=session_id)
    except Conversation.DoesNotExist:
        return Response({"error": "Conversation not found"}, status=404)

    # Scoping check
    if hasattr(request.user, "profile") and request.user.profile.assigned_agent:
        if conversation.agent != request.user.profile.assigned_agent:
            return Response({"error": "Forbidden: You do not have permission to access this lead's data."}, status=403)

    try:
        lead = LeadAnalysis.objects.get(conversation=conversation)
    except LeadAnalysis.DoesNotExist:
        return Response({"error": "Lead analysis not available for this session"}, status=404)

    lead.lead_level = new_level
    lead.save()

    return Response({
        "success": True,
        "lead_level": lead.lead_level,
        "message": f"Lead level updated to {lead.lead_level} successfully."
    })


# ======================================================
# TELECOM CDR WEBHOOK (POST — receives call data after call ends)
# ======================================================

from .models import CallDetailRecord
from datetime import datetime as dt
from django.db import IntegrityError, transaction


@api_view(["GET", "POST"])
def icemake_webhook(request):
    """
    Flexible webhook endpoint for Ice Make telecom trunk.
    Handles both incoming call setup (inbound twiml) and post-call CDR webhook.
    """
    try:
        raw_data = getattr(request, "data", {}) or {}
        if not raw_data and request.body:
            import json
            try:
                raw_data = json.loads(request.body.decode("utf-8"))
            except Exception:
                raw_data = {}

        pass
    except Exception as e:
        raw_data = getattr(request, "data", {}) or {}

    # Check if CDR post-call webhook payload
    if "call" in raw_data or "recording_url" in raw_data or "duration" in raw_data or "call_id" in raw_data or "event" in raw_data:
        from agents.models import VoiceAgent
        ice_agent = VoiceAgent.objects.filter(role_template__role_name__icontains="Ice Make").first()
        ice_agent_id = str(ice_agent.id) if ice_agent else None
        return _process_telecom_cdr_request(request, raw_data, target_agent_id=ice_agent_id)

    # Route to inbound call handler
    try:
        from bot.views import inbound_call_webhook
        return inbound_call_webhook(request)
    except Exception as e_inb:
        print(f"[ICEMAKE-WEBHOOK] Inbound delegate error: {e_inb}")
        return Response({"status": "ok"}, status=200)

@api_view(["POST"])
def telecom_cdr_webhook(request):
    raw_data = request.data or {}
    return _process_telecom_cdr_request(request, raw_data)

@csrf_exempt
@api_view(["GET", "POST"])
def kylas_webhook(request):
    """
    [ON HOLD / DISABLED FOR NOW]
    Bridge Endpoint: Receives real-time Lead events from Kylas CRM.
    Currently commented out per user request to focus exclusively on Sarvam AI Ready Agent.
    """
    return Response({
        "status": "disabled",
        "message": "Kylas CRM integration is temporarily on hold. Focus is exclusively on Sarvam AI Agent."
    }, status=200)


@csrf_exempt
@api_view(["POST"])
def sarvam_cdr_webhook(request):
    """
    Sarvam AI Ready Agent Webhook Endpoint.
    Receives post-call summary, interaction metrics, recording URL, and transcript from Sarvam AI Agent,
    and updates/creates local SarvamCallRecord entries for real-time dashboard display.
    (Kylas CRM sync is currently ON HOLD by user request).
    Target Webhook URL: https://unprecious-waltraud-nasological.ngrok-free.dev/api/webhook/sarvam/cdr/
    """
    try:
        raw_data = getattr(request, "data", {}) or {}
        if not raw_data and request.body:
            import json
            try:
                raw_data = json.loads(request.body.decode("utf-8"))
            except Exception:
                raw_data = {}

        print("\n" + "="*60)
        print("🎙️ [SARVAM CDR WEBHOOK RECEIVED]")
        import json
        print(f"Payload: {json.dumps(raw_data, indent=2)}")
        print("="*60 + "\n")

        call_obj = raw_data.get("call") if isinstance(raw_data.get("call"), dict) else {}
        metadata = raw_data.get("metadata", {})

        # ✅ Extract interaction_id (supports interaction_id, interactionId, call_id, callId, sid)
        interaction_id = (
            raw_data.get("interaction_id")
            or raw_data.get("interactionId")
            or raw_data.get("call_id")
            or raw_data.get("callId")
            or call_obj.get("sid")
            or call_obj.get("id")
        )

        # ✅ Extract attempt_id
        attempt_id = raw_data.get("attempt_id") or raw_data.get("attemptId")

        # ✅ Extract phone — reads user_phone_number, phone_number, user_identifier, caller numbers
        user_phone = (
            raw_data.get("user_phone_number")
            or raw_data.get("phone_number")
            or raw_data.get("user_identifier")
            or call_obj.get("from")
            or call_obj.get("caller_number")
            or call_obj.get("to")
            or ""
        )
        # Clean phone: remove non-digit chars, keep last 10 digits
        if user_phone:
            user_phone_clean = "".join(filter(str.isdigit, str(user_phone)))[-10:]
            if user_phone_clean:
                user_phone = user_phone_clean

        # ✅ Extract call timing fields
        call_start_time = raw_data.get("call_start_time") or raw_data.get("started_at") or raw_data.get("timestamp")
        call_end_time = raw_data.get("call_end_time") or raw_data.get("ended_at")
        call_length = float(raw_data.get("call_length") or raw_data.get("duration_in_seconds") or raw_data.get("duration") or 0)

        # ✅ Parse conversation_log into a readable transcript string
        conversation_log = raw_data.get("conversation_log") or []
        if isinstance(conversation_log, list) and conversation_log:
            transcript_from_log = "\n\n".join([
                f"{msg.get('role', 'speaker').upper()}: {msg.get('en_text') or msg.get('text') or ''}"
                for msg in conversation_log
            ])
        else:
            transcript_from_log = None

        transcript = (
            transcript_from_log
            or raw_data.get("call_transcript")
            or raw_data.get("transcript")
            or raw_data.get("interaction_transcript")
            or raw_data.get("analysis", {}).get("transcript")
        )

        if isinstance(interaction_id, str) and ("{" in interaction_id or "[" in interaction_id or "test" in interaction_id):
            interaction_id = None

        # ✅ Fix bare UUID: prepend date in YYYYMMDD format
        if interaction_id and isinstance(interaction_id, str) and "/" not in interaction_id:
            from datetime import datetime
            raw_ts = call_start_time or raw_data.get("timestamp") or call_obj.get("timestamp")
            if raw_ts:
                try:
                    ts_str = str(raw_ts).replace("Z", "+00:00").split(".")[0]
                    call_date = datetime.fromisoformat(ts_str).strftime("%Y%m%d")
                    interaction_id = f"{call_date}/{interaction_id}"
                    print(f"✅ [CDR FIX] Formatted bare interaction_id with date: {interaction_id}")
                except Exception as ts_err:
                    call_date = datetime.utcnow().strftime("%Y%m%d")
                    interaction_id = f"{call_date}/{interaction_id}"
                    print(f"⚠️ [CDR FIX] Timestamp parse failed: {ts_err} — using today: {interaction_id}")
            else:
                from datetime import datetime
                call_date = datetime.utcnow().strftime("%Y%m%d")
                interaction_id = f"{call_date}/{interaction_id}"
                print(f"⚠️ [CDR FIX] No timestamp in payload — using today's date: {interaction_id}")

        from conversations.services.kylas_sarvam_bridge import SarvamAgentService
        from conversations.models import SarvamCallRecord, SarvamAgent

        # ✅ Detect which SarvamAgent this CDR belongs to using app_id or agent_phone from payload
        cdr_app_id = raw_data.get("app_id") or raw_data.get("agent_id") or ""
        cdr_agent_phone = raw_data.get("agent_phone_number") or raw_data.get("agent_phone") or ""
        webhook_sarvam_agent = None
        if cdr_app_id:
            webhook_sarvam_agent = SarvamAgent.objects.filter(app_id=cdr_app_id, is_active=True).first()
        if not webhook_sarvam_agent and cdr_agent_phone:
            clean_agent_phone = "".join(filter(str.isdigit, str(cdr_agent_phone)))
            webhook_sarvam_agent = SarvamAgent.objects.filter(
                agent_phone__icontains=clean_agent_phone[-10:]
            ).first() if len(clean_agent_phone) >= 10 else None
        if not webhook_sarvam_agent:
            webhook_sarvam_agent = SarvamAgent.objects.filter(is_active=True).first()

        print(f"🔍 [SARVAM CDR] Resolved agent: {webhook_sarvam_agent.name if webhook_sarvam_agent else 'DEFAULT (env)'} | app_id={cdr_app_id}")

        recording_url = (
            raw_data.get("recording_url")
            or raw_data.get("audio_url")
            or raw_data.get("recording")
            or raw_data.get("call_recording")
            or call_obj.get("recordingUrl")
            or call_obj.get("recording_url")
        )

        # ✅ Try fetching recording using this agent's credentials
        if interaction_id:
            print(f"🎙️ [SARVAM RECORDINGS API] Fetching call recording for interaction_id: {interaction_id}")
            rec_result = SarvamAgentService.fetch_interaction_recording(
                interaction_id=interaction_id, sarvam_agent=webhook_sarvam_agent
            )
            if rec_result:
                if isinstance(rec_result, str) and rec_result.startswith("http"):
                    recording_url = rec_result
                elif isinstance(rec_result, dict):
                    recording_url = rec_result.get("recording_url") or rec_result.get("audio_url") or rec_result.get("url") or recording_url

            # ✅ Fetch transcript from API only if conversation_log/call_transcript didn't give us one
            if not transcript:
                print(f"🔍 [SARVAM ANALYTICS API] Fetching transcript for interaction_id: {interaction_id}")
                analytics_res = SarvamAgentService.fetch_interaction_transcript(interaction_id=interaction_id)
                if isinstance(analytics_res, dict) and "transcript" in analytics_res:
                    transcript = analytics_res.get("transcript")
                elif isinstance(analytics_res, list):
                    transcript = "\n\n".join([f"{item.get('role', 'Speaker').upper()}: {item.get('text', '')}" for item in analytics_res])

        # ✅ Build final_status — prefer final_status / completion_status / call_disposition / status
        final_status = (
            raw_data.get("final_status")
            or raw_data.get("completion_status")
            or raw_data.get("call_disposition")
            or raw_data.get("status")
            or call_obj.get("status")
            or "COMPLETED"
        )
        output_vars = raw_data.get("output_agent_variables") or raw_data.get("final_agent_variables") or {}
        if isinstance(output_vars, dict) and output_vars.get("final_status"):
            final_status = output_vars["final_status"]

        # ✅ Extract candidate_name early to assist in record matching
        candidate_name = (
            raw_data.get("candidate_name")
            or raw_data.get("user_name")
            or raw_data.get("customer_name")
            or metadata.get("customer_name")
            or metadata.get("user_name")
            or (output_vars.get("candidate_name") if isinstance(output_vars, dict) else None)
            or (output_vars.get("user_name") if isinstance(output_vars, dict) else None)
            or (output_vars.get("customer_name") if isinstance(output_vars, dict) else None)
            or "Customer"
        )

        rec = None
        if attempt_id:
            rec = SarvamCallRecord.objects.filter(attempt_id=attempt_id).first()
        if not rec and interaction_id:
            rec = SarvamCallRecord.objects.filter(interaction_id=interaction_id).first()
            if not rec and "/" in str(interaction_id):
                raw_iid = str(interaction_id).split("/")[-1]
                rec = SarvamCallRecord.objects.filter(interaction_id__endswith=raw_iid).first()
        if not rec and user_phone:
            clean_p = "".join(filter(str.isdigit, str(user_phone)))[-10:]
            if clean_p:
                from datetime import timedelta
                from django.utils import timezone
                recent_threshold = timezone.now() - timedelta(minutes=30)
                rec = SarvamCallRecord.objects.filter(
                    phone_number__icontains=clean_p,
                    created_at__gte=recent_threshold
                ).order_by("-created_at").first()

        # Fallback 1: Match by candidate_name if present on recent active calls for this agent
        if not rec and candidate_name and candidate_name not in ["Customer", "Valued Customer", "Candidate"]:
            from datetime import timedelta
            from django.utils import timezone
            recent_threshold = timezone.now() - timedelta(minutes=30)
            rec_qs = SarvamCallRecord.objects.filter(
                candidate_name__icontains=candidate_name,
                created_at__gte=recent_threshold
            )
            if webhook_sarvam_agent:
                rec_qs = rec_qs.filter(sarvam_agent=webhook_sarvam_agent)
            rec = rec_qs.order_by("-created_at").first()
            if rec:
                print(f"✅ [SARVAM CDR LOGS]: Mapped webhook payload to recent call #{rec.id} ({rec.phone_number}) via candidate_name '{candidate_name}'.")

        # Fallback 2: Match to most recent DIALING / IN_PROGRESS / INITIATED / PENDING call for this agent
        if not rec:
            from datetime import timedelta
            from django.utils import timezone
            recent_threshold = timezone.now() - timedelta(minutes=30)
            rec_qs = SarvamCallRecord.objects.filter(
                status__in=["DIALING", "IN_PROGRESS", "INITIATED", "PENDING"],
                created_at__gte=recent_threshold
            )
            if webhook_sarvam_agent:
                rec_qs = rec_qs.filter(sarvam_agent=webhook_sarvam_agent)
            rec = rec_qs.order_by("-created_at").first()
            if rec:
                print(f"⚠️ [SARVAM CDR LOGS]: Mapped webhook payload to recent active call #{rec.id} ({rec.phone_number}) via status fallback.")
        language_val = (
            raw_data.get("detected_language")
            or raw_data.get("language")
            or metadata.get("language")
            or metadata.get("detected_language")
            or (output_vars.get("detected_language") if isinstance(output_vars, dict) else None)
            or (output_vars.get("language") if isinstance(output_vars, dict) else None)
            or "hi-IN"
        )
        duration = call_length or float(
            raw_data.get("duration")
            or raw_data.get("duration_in_seconds")
            or call_obj.get("duration")
            or 0
        )

        # Build summary from all rich fields in the root payload
        if not output_vars and raw_data:
            ignored_keys = {"call", "metadata", "interaction_id", "interactionId", "call_id", "callId", "attempt_id", "attemptId",
                            "user_phone_number", "phone_number", "user_identifier", "status", "duration",
                            "transcript", "call_transcript", "conversation_log", "call_start_time", "call_end_time", "call_length",
                            "agent_phone", "agent_phone_number", "provider_reference_id", "campaign_id"}
            output_vars = {k: v for k, v in raw_data.items() if k not in ignored_keys and v}

        # Clean empty string attempt_id to None to avoid unique constraint issues
        clean_attempt_id = attempt_id if attempt_id else None

        if rec:
            rec.interaction_id = interaction_id or rec.interaction_id
            rec.status = final_status
            rec.duration_seconds = duration if duration > 0 else rec.duration_seconds
            if candidate_name and candidate_name not in ["Candidate", "Customer", "Valued Customer", ""]:
                if not rec.candidate_name or rec.candidate_name.lower() in ["candidate", "customer", "valued customer", "none", "null", ""] or rec.candidate_name.startswith("Candidate #"):
                    rec.candidate_name = candidate_name
            if language_val:
                rec.language = language_val
            if isinstance(output_vars, dict) and output_vars:
                rec.summary = output_vars
            if transcript:
                rec.transcript = transcript
            if recording_url:
                rec.audio_url = recording_url
            # Backfill sarvam_agent if missing
            if webhook_sarvam_agent and not rec.sarvam_agent:
                rec.sarvam_agent = webhook_sarvam_agent
            rec.save()
            print(f"✅ [SARVAM CDR LOGS]: Updated local SarvamCallRecord ID #{rec.id} for {rec.phone_number} -> Status: {final_status}, Recording: {'YES' if rec.audio_url else 'NO'}, Transcript: {'YES' if rec.transcript else 'NO'}, Agent: {rec.sarvam_agent.name if rec.sarvam_agent else 'N/A'}")
        else:
            if not user_phone and not interaction_id:
                print(f"⚠️ [SARVAM CDR LOGS]: Ignored dummy webhook payload (No user_phone or interaction_id).")
            else:
                is_inbound = bool(call_obj.get("direction") == "inbound" or raw_data.get("direction") == "inbound" or not attempt_id)
                rec_call_type = "Inbound Call" if is_inbound else "Outbound Call"
                rec = SarvamCallRecord.objects.create(
                    sarvam_agent=webhook_sarvam_agent,
                    attempt_id=clean_attempt_id,
                    interaction_id=interaction_id,
                    phone_number=str(user_phone or "unknown"),
                    candidate_name=candidate_name or "Valued Customer",
                    language=language_val or "hi-IN",      # ✅ FIX: never pass None to NOT NULL column
                    status=final_status or "COMPLETED",
                    call_type=rec_call_type,
                    duration_seconds=duration or 0.0,
                    summary=output_vars if isinstance(output_vars, dict) else {},
                    transcript=transcript or "",
                    audio_url=recording_url,
                )
                print(f"✅ [SARVAM CDR LOGS]: Created new local SarvamCallRecord ID #{rec.id} ({rec_call_type}) for {user_phone} -> Status: {final_status}, Recording: {'YES' if rec.audio_url else 'NO'}, Agent: {webhook_sarvam_agent.name if webhook_sarvam_agent else 'N/A'}")

        # ✅ REAL-TIME CAMPAIGN LEAD SYNC: If this call belongs to a multi-stage campaign, update the lead outcome instantly!
        if rec:
            try:
                from conversations.models import SarvamCampaignLead
                CDR_MISSED_STATUSES = {
                    "NO_ANSWER", "BUSY", "FAILED", "UNREACHABLE", "CANCELLED", "MISSED",
                    "QUEUED", "DIALING", "UNANSWERED", "REJECTED", "NOT_ANSWERED", "TIMEOUT", "IN_PROGRESS", "PENDING"
                }
                c_lead = (
                    getattr(rec, "stage_1_lead", None).first()
                    or getattr(rec, "stage_2_lead", None).first()
                    or getattr(rec, "stage_3_lead", None).first()
                )
                if not c_lead and rec.campaign:
                    clean_p = "".join(filter(str.isdigit, str(rec.phone_number)))[-10:]
                    c_lead = rec.campaign.leads.filter(phone_number__icontains=clean_p).first()

                if c_lead:
                    stage_num = rec.campaign_stage or (
                        1 if (c_lead.stage_1_call_id == rec.id or not c_lead.stage_2_call_id) else (
                            2 if c_lead.stage_2_call_id == rec.id else 3
                        )
                    )
                    is_ans = (rec.duration_seconds >= 3.0 and str(rec.status).upper() not in CDR_MISSED_STATUSES)

                    if stage_num == 1:
                        c_lead.stage_1_call = rec
                        if is_ans:
                            c_lead.stage_1_status = "ANSWERED"
                            c_lead.stage_2_status = "SKIPPED"
                            c_lead.stage_3_status = "SKIPPED"
                            c_lead.final_status = "ANSWERED"
                            print(f"🎯 [SARVAM CAMPAIGN SYNC]: Lead #{c_lead.id} ({c_lead.candidate_name}) marked ANSWERED ({rec.duration_seconds:.1f}s) in Stage 1 via Webhook.")
                        elif str(rec.status).upper() in CDR_MISSED_STATUSES:
                            c_lead.stage_1_status = "MISSED"
                            if c_lead.final_status != "ANSWERED":
                                c_lead.final_status = "IN_PROGRESS"
                        c_lead.save()

                    elif stage_num == 2:
                        c_lead.stage_2_call = rec
                        if is_ans:
                            c_lead.stage_2_status = "ANSWERED"
                            c_lead.stage_3_status = "SKIPPED"
                            c_lead.final_status = "ANSWERED"
                            print(f"🎯 [SARVAM CAMPAIGN SYNC]: Lead #{c_lead.id} ({c_lead.candidate_name}) marked ANSWERED ({rec.duration_seconds:.1f}s) in Stage 2 (Retry 1) via Webhook.")
                        elif str(rec.status).upper() in CDR_MISSED_STATUSES:
                            c_lead.stage_2_status = "MISSED"
                            if c_lead.final_status != "ANSWERED":
                                c_lead.final_status = "IN_PROGRESS"
                        c_lead.save()

                    elif stage_num == 3:
                        c_lead.stage_3_call = rec
                        if is_ans:
                            c_lead.stage_3_status = "ANSWERED"
                            c_lead.final_status = "ANSWERED"
                            print(f"🎯 [SARVAM CAMPAIGN SYNC]: Lead #{c_lead.id} ({c_lead.candidate_name}) marked ANSWERED ({rec.duration_seconds:.1f}s) in Stage 3 (Final Retry) via Webhook.")
                        elif str(rec.status).upper() in CDR_MISSED_STATUSES:
                            c_lead.stage_3_status = "MISSED"
                            if c_lead.final_status != "ANSWERED":
                                c_lead.final_status = "MISSED_ALL_RETRIES"
                        c_lead.save()

                    # Recalculate and update campaign totals
                    camp = c_lead.campaign
                    if camp:
                        camp.stage_1_answered = camp.leads.filter(stage_1_status="ANSWERED").count()
                        camp.stage_1_missed = camp.leads.filter(stage_1_status="MISSED").count()
                        camp.stage_2_answered = camp.leads.filter(stage_2_status="ANSWERED").count()
                        camp.stage_2_missed = camp.leads.filter(stage_2_status="MISSED").count()
                        camp.stage_3_answered = camp.leads.filter(stage_3_status="ANSWERED").count()
                        camp.stage_3_missed = camp.leads.filter(stage_3_status="MISSED").count()
                        camp.answered_count = camp.leads.filter(final_status="ANSWERED").count()
                        camp.missed_count = camp.leads.filter(final_status="MISSED_ALL_RETRIES").count()
                        camp.save()
            except Exception as sync_err:
                print(f"⚠️ [SARVAM CAMPAIGN LEAD SYNC ERROR]: {sync_err}")

        # =========================================================
        # [KYLAS CRM INTEGRATION - ON HOLD / COMMENTED OUT FOR NOW]
        # =========================================================

        # ✅ AUTO RECORDING RETRY: If no recording yet, spawn background thread to retry
        # Sarvam takes 30-90 seconds to process audio after call ends
        if rec and not rec.audio_url and rec.interaction_id and "/" in rec.interaction_id:
            import threading
            record_id = rec.id
            iid = rec.interaction_id

            def _retry_fetch_recording(record_id, interaction_id, max_retries=4, delay_sec=60):
                """Background thread: retries fetching recording every 60s until available."""
                import time
                import requests as _requests
                import os

                # ✅ Use this record's agent credentials (not hardcoded Raahi env values)
                try:
                    from conversations.models import SarvamCallRecord as _SCR, SarvamAgent as _SA
                    _r = _SCR.objects.select_related("sarvam_agent").filter(id=record_id).first()
                    _agent = _r.sarvam_agent if (_r and _r.sarvam_agent) else None
                except Exception:
                    _agent = None

                if _agent and _agent.org_id and _agent.api_key:
                    org_id = _agent.org_id
                    ws_id = _agent.workspace_id
                    app_id = _agent.app_id
                    api_key = _agent.api_key
                else:
                    org_id = os.getenv("SARVAM_ORG_ID", "01a03cbf-1bf4-70f0-995f-854d6d2dd105")
                    ws_id = os.getenv("SARVAM_WORKSPACE_ID", "01a03cbf-1bfb-770a-bb91-06baeec9d28e")
                    app_id = os.getenv("SARVAM_AGENT_ID", "iiiEM---Rec-136dc7be-adb6")
                    api_key = os.getenv("SARVAM_AGENT_API_KEY", "")

                rec_url = f"https://apps.sarvam.ai/api/analytics/v1/{org_id}/{ws_id}/{app_id}/recordings/{interaction_id}"
                headers = {"X-API-Key": api_key}

                for attempt in range(1, max_retries + 1):
                    time.sleep(delay_sec)
                    try:
                        # Import inside thread after sleep — Django is already set up by Daphne
                        from conversations.models import SarvamCallRecord
                        r = SarvamCallRecord.objects.filter(id=record_id).first()
                        if not r:
                            break
                        if r.audio_url:
                            print(f"✅ [RECORDING RETRY] Record #{record_id} already has audio, skipping.")
                            break

                        print(f"🔄 [RECORDING RETRY] Attempt {attempt}/{max_retries} for {interaction_id}...")
                        resp = _requests.get(rec_url, headers=headers, timeout=15, allow_redirects=True)

                        if resp.status_code == 200:
                            # Got the audio — save the URL
                            final_url = resp.url
                            r.audio_url = final_url
                            r.save(update_fields=["audio_url"])
                            print(f"✅ [RECORDING RETRY] Got recording for record #{record_id} on attempt {attempt}! Saved: {final_url[:80]}")
                            break
                        elif resp.status_code == 404:
                            print(f"⏳ [RECORDING RETRY] Not ready yet (attempt {attempt}/{max_retries}), retrying in {delay_sec}s...")
                        else:
                            print(f"⚠️ [RECORDING RETRY] Unexpected status {resp.status_code} on attempt {attempt}")
                    except Exception as e:
                        print(f"⚠️ [RECORDING RETRY] Attempt {attempt} error: {e}")

            t = threading.Thread(target=_retry_fetch_recording, args=(record_id, iid), daemon=True)
            t.start()
            print(f"⏳ [RECORDING RETRY] Scheduled background retry for record #{rec.id} (interaction: {iid})")

        return Response({
            "status": "success",
            "message": "Sarvam AI CDR webhook data & audio recording synced successfully",
            "record_id": rec.id if rec else None,
            "interaction_id": rec.interaction_id if rec else None,
            "status_saved": rec.status if rec else final_status,
            "audio_url": rec.audio_url if rec else None
        }, status=200)

    except Exception as e:
        print(f"❌ [SARVAM CDR WEBHOOK ERROR]: {e}")
        return Response({"status": "error", "message": str(e)}, status=500)



def safe_int_val(val, default=0):
    if not val:
        return default
    try:
        return int(float(str(val)))
    except Exception:
        return default

def _process_telecom_cdr_request(request, raw_data, target_agent_id=None):
    """
    Internal helper to process CDR webhook data from Service 1 or Service 2.
    """

    # Normalize Service 2 format to internal schema format
    if "call" in raw_data:
        call_data = raw_data["call"]
        event = raw_data.get("event", "")

        # Accept final call events (completed, failed, ended, or if no event string provided)
        is_final = not event or event in ["call.completed", "call.failed", "call.ended"]
        if not is_final:
            return Response(
                {"status": "ignored", "message": f"Non-final event '{event}' ignored"},
                status=200
            )

        # Map Service 2 fields to old format keys
        custom_params = call_data.get("customParameters") or call_data.get("custom_parameters")
        if not isinstance(custom_params, dict):
            custom_params = {}
            
        payload_call_type = (custom_params.get("callType") or custom_params.get("call_type") or "").lower()
        direction_val = str(call_data.get("direction") or "").lower()
        
        if direction_val == "inbound" or payload_call_type == "inbound":
            direction = "inbound"
        else:
            direction = "outbound"

        known_dids = [
            "7971019486", "917971019486",
            "7971017251", "917971017251",
            "7969016753", "917969016753",
            "100259134222", "91100259134222"
        ]

        # First priority: Direct phone_number field if present (Insurance-Bot / IVRManager format)
        direct_phone = raw_data.get("phone_number") or raw_data.get("caller_number")
        if direct_phone and direct_phone != "unknown":
            clean_dp = "".join(filter(str.isdigit, str(direct_phone)))
            if not any(b in clean_dp for b in known_dids):
                phone_number = str(direct_phone).strip()
                did = str(raw_data.get("did") or call_data.get("from") or call_data.get("to") or "unknown").strip()
            else:
                # Direct phone_number was DID -> real caller is in 'did'
                phone_number = str(raw_data.get("did") or "").strip()
                did = str(direct_phone).strip()
        else:
            raw_from = str(call_data.get("from") or "").strip()
            raw_to = str(call_data.get("to") or "").strip()
            clean_from = "".join(filter(str.isdigit, raw_from))
            clean_to = "".join(filter(str.isdigit, raw_to))

            if any(b in clean_from for b in known_dids):
                # 'from' is DID -> 'to' is REAL CALLER!
                phone_number = raw_to
                did = raw_from
            elif any(b in clean_to for b in known_dids):
                # 'to' is DID -> 'from' is REAL CALLER!
                phone_number = raw_from
                did = raw_to
            else:
                phone_number = raw_from if direction == "inbound" else raw_to
                did = raw_to if direction == "inbound" else raw_from

        print(f"🎯 [CDR RESOLVED USER CALLER NUMBER]: {phone_number} (DID: {did})")

        status = call_data.get("status", "")
        if status in ["failed", "FAILED"]:
            disposition = "FAILED"
        elif call_data.get("callStatus") in ["NO ANSWER", "NO_ANSWER"]:
            disposition = "NO ANSWER"
        elif call_data.get("answeredAt") is not None or status in ["ended", "completed"]:
            disposition = "ANSWERED"
        else:
            disposition = "NO ANSWER"

        data = {
            "uniqueid": call_data.get("id") or raw_data.get("uniqueid") or f"cdr_{uuid.uuid4().hex[:12]}",
            "ws_session_id": call_data.get("id") or raw_data.get("ws_session_id"),
            "phone_number": phone_number or "unknown",
            "did": did or "unknown",
            "duration": safe_int_val(call_data.get("durationSec") or raw_data.get("duration")),
            "disposition": disposition,
            "call_type": direction.upper(),
            "recording_file_name": call_data.get("recordingUrl") or call_data.get("recording_file_name") or raw_data.get("recording_file_name") or raw_data.get("resource_url") or "",
            "call_id": safe_int_val(custom_params.get("outboundQueueId") or raw_data.get("call_id")),
        }

        # Parse and format dates to strings
        started_at_str = call_data.get("startedAt") or raw_data.get("calldate") or raw_data.get("callDate")
        if started_at_str:
            try:
                dt_obj = dt.strptime(started_at_str.split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
                data["calldate"] = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                data["calldate"] = started_at_str
        else:
            data["calldate"] = dt.now().strftime("%Y-%m-%d %H:%M:%S")

        answered_at_str = call_data.get("answeredAt") or raw_data.get("answer_time")
        if answered_at_str:
            try:
                dt_obj = dt.strptime(answered_at_str.split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
                data["answer_time"] = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                data["answer_time"] = answered_at_str
        else:
            data["answer_time"] = None
    else:
        # Service 1 / IVRManager format
        data = dict(raw_data)
        data["calldate"] = raw_data.get("calldate") or raw_data.get("callDate") or dt.now().strftime("%Y-%m-%d %H:%M:%S")
        data["recording_file_name"] = raw_data.get("recording_file_name") or raw_data.get("resource_url") or ""
        data["duration"] = safe_int_val(raw_data.get("duration") or raw_data.get("call_duration"))
        data["disposition"] = raw_data.get("disposition") or raw_data.get("call_status") or "ANSWERED"
        data["call_id"] = safe_int_val(raw_data.get("call_id"))

    # Ensure required fields have valid defaults
    if "call_id" not in data or data["call_id"] is None:
        data["call_id"] = 0
    if "phone_number" not in data or not data["phone_number"]:
        data["phone_number"] = "unknown"
    if "did" not in data or not data["did"]:
        data["did"] = "unknown"
    if "uniqueid" not in data or not data["uniqueid"]:
        data["uniqueid"] = f"cdr_{uuid.uuid4().hex[:12]}"
    if "calldate" not in data or not data["calldate"]:
        data["calldate"] = dt.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "─" * 80)
    print("📋 [NORMALIZED ICEMAKE POST PAYLOAD - IVRManager Format]:")
    import json
    normalized_print_payload = {
        "call_id": data.get("call_id"),
        "phone_number": data.get("phone_number"),
        "did": data.get("did"),
        "uniqueid": data.get("uniqueid"),
        "call_date": data.get("calldate"),
        "call_status": data.get("disposition"),
        "call_duration": str(data.get("duration")),
        "resource_url": data.get("recording_file_name")
    }
    print(json.dumps(normalized_print_payload, indent=2, default=str))
    print("─" * 80 + "\n")

    # Parse dates safely
    from django.utils import timezone
    try:
        calldate = dt.strptime(data["calldate"], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        calldate = timezone.now()

    if not calldate:
        calldate = timezone.now()

    answer_time = None
    if data.get("answer_time"):
        try:
            answer_time = dt.strptime(data["answer_time"], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            pass

    # Try to match to existing Conversation
    conversation = None
    matched = False

    # 1. BEST: Match by ws_session_id → Conversation.stream_sid (checking with and without "stream_" prefix)
    ws_sid = data.get("ws_session_id")
    if ws_sid:
        conversation = Conversation.objects.filter(stream_sid=ws_sid).first()
        if not conversation:
            # Try with "stream_" prefix
            conversation = Conversation.objects.filter(stream_sid=f"stream_{ws_sid}").first()
        if not conversation and ws_sid.startswith("stream_"):
            # Try without "stream_" prefix
            conversation = Conversation.objects.filter(stream_sid=ws_sid[7:]).first()

        if conversation:
            print(f"PERFECT MATCH: ws_session_id '{ws_sid}' -> Conversation {conversation.id}")

    # 2. FALLBACK: Match by phone number (last 10 digits) within 15 mins window
    if not conversation:
        raw_phone = data.get("phone_number", "")
        if raw_phone and calldate:
            import datetime
            clean_phone = "".join(filter(str.isdigit, raw_phone))[-10:]
            if clean_phone:
                time_15m_start = calldate - datetime.timedelta(minutes=15)
                time_15m_end = calldate + datetime.timedelta(minutes=15)
                qs = Conversation.objects.filter(
                    user_number__icontains=clean_phone,
                    cdr__isnull=True,
                    started_at__range=(time_15m_start, time_15m_end)
                )
                if target_agent_id:
                    qs = qs.filter(agent_id=target_agent_id)
                conversation = qs.order_by("-started_at").first()
                if conversation:
                    print(f"FALLBACK MATCH: Phone '{clean_phone}' -> Conversation {conversation.id}")

    # 3. SECOND FALLBACK: Match by timestamp window (for Service 2 "unknown" phone numbers) - only match conversations without a CDR
    if not conversation:
        raw_phone = data.get("phone_number", "")
        if raw_phone and calldate:
            import datetime
            time_threshold_start = calldate - datetime.timedelta(minutes=5)
            time_threshold_end = calldate + datetime.timedelta(minutes=5)
            
            qs = Conversation.objects.filter(
                user_number="unknown",
                cdr__isnull=True,
                started_at__range=(time_threshold_start, time_threshold_end)
            )
            if target_agent_id:
                qs = qs.filter(agent_id=target_agent_id)
            conversation = qs.order_by("-started_at").first()
            
            if conversation:
                print(f"CDR TIMESTAMP MATCH: Linked unmatched 'unknown' Conversation {conversation.id} to phone {raw_phone}")

    # 4. THIRD FALLBACK: Match latest active conversation created around calldate (within 15 mins)
    if not conversation and calldate:
        import datetime
        time_start = calldate - datetime.timedelta(minutes=15)
        time_end = calldate + datetime.timedelta(minutes=15)
        qs = Conversation.objects.filter(
            started_at__range=(time_start, time_end)
        )
        if target_agent_id:
            qs = qs.filter(agent_id=target_agent_id)
        conversation = qs.order_by("-started_at").first()

    if conversation:
        matched = True
        new_call_type = data.get("call_type")
        if new_call_type and conversation.call_type != new_call_type:
            conversation.call_type = new_call_type
            conversation.save(update_fields=["call_type"])

        if data.get("phone_number") and data.get("phone_number") != "unknown":
            conversation.user_number = data.get("phone_number", "")
            conversation.save(update_fields=["user_number"])

    # Handle Recording (Download from provider and upload to Azure)
    rec_file = data.get("recording_file_name", "")
    if rec_file:
        if not rec_file.startswith("http"):
            original_url = f"https://voice-bot.on-forge.com/recordings/{rec_file}"
        else:
            original_url = rec_file
        
        azure_service = AzureBlobService()
        azure_url = azure_service.download_and_upload(original_url, data.get("phone_number", "unknown"))
        
        if azure_url:
            rec_file = azure_url
        else:
            rec_file = original_url

    # Save or update CDR safely
    existing_cdr = None
    if conversation:
        existing_cdr = CallDetailRecord.objects.filter(conversation=conversation).first()
    if not existing_cdr and data.get("uniqueid"):
        existing_cdr = CallDetailRecord.objects.filter(uniqueid=data["uniqueid"]).first()

    if existing_cdr:
        if data.get("phone_number") and data.get("phone_number") != "unknown":
            existing_cdr.phone_number = data.get("phone_number")
        if data.get("did") and data.get("did") != "unknown":
            existing_cdr.did = data.get("did")
        existing_cdr.recording_file_name = rec_file or existing_cdr.recording_file_name
        existing_cdr.duration = safe_int_val(data.get("duration"), existing_cdr.duration)
        existing_cdr.disposition = data.get("disposition", existing_cdr.disposition)
        existing_cdr.answer_time = answer_time or existing_cdr.answer_time
        if not existing_cdr.uniqueid or existing_cdr.uniqueid == str(data["uniqueid"]):
            existing_cdr.uniqueid = data["uniqueid"]
        existing_cdr.matched = True
        existing_cdr.save()
        cdr = existing_cdr
    else:
        try:
            with transaction.atomic():
                cdr = CallDetailRecord.objects.create(
                    conversation=conversation,
                    telecom_call_id=safe_int_val(data.get("call_id"), 0),
                    phone_number=data.get("phone_number", ""),
                    calldate=calldate,
                    did=data.get("did", ""),
                    duration=safe_int_val(data.get("duration"), 0),
                    disposition=data.get("disposition", "ANSWERED"),
                    call_type=data.get("call_type", "OUTBOUND"),
                    answer_time=answer_time,
                    uniqueid=data.get("uniqueid") or f"cdr_{uuid.uuid4().hex[:12]}",
                    recording_file_name=rec_file,
                    matched=matched,
                )
        except IntegrityError as e:
            existing_cdr = CallDetailRecord.objects.filter(uniqueid=data["uniqueid"]).first()
            if existing_cdr:
                if rec_file and not existing_cdr.recording_file_name:
                    existing_cdr.recording_file_name = rec_file
                    existing_cdr.save(update_fields=["recording_file_name"])
                return Response(
                    {"status": "duplicate", "message": "CDR already received for this uniqueid", "cdr_id": existing_cdr.id},
                    status=200
                )
            else:
                import uuid
                cdr = CallDetailRecord.objects.create(
                    conversation=conversation,
                    telecom_call_id=safe_int_val(data.get("call_id"), 0),
                    phone_number=data.get("phone_number", ""),
                    calldate=calldate,
                    did=data.get("did", ""),
                    duration=safe_int_val(data.get("duration"), 0),
                    disposition=data.get("disposition", "ANSWERED"),
                    call_type=data.get("call_type", "OUTBOUND"),
                    answer_time=answer_time,
                    uniqueid=f"cdr_{uuid.uuid4().hex[:12]}",
                    recording_file_name=rec_file,
                    matched=matched,
                )
        else:
            return Response(
                {"status": "duplicate", "message": "CDR already received for this uniqueid"},
                status=200
            )

    result = {
        "status": "success",
        "cdr_id": cdr.id,
        "matched": matched,
    }

    if matched and conversation:
        result["conversation_id"] = conversation.id
        result["agent_name"] = conversation.agent.name if conversation.agent else None

        # Check if Ice Make Ticket exists for this conversation and sync to Google Sheet
        try:
            from icemake_bot.models import IcemakeTicket
            from icemake_bot.strategy import _append_to_google_sheet
            ticket = IcemakeTicket.objects.filter(conversation=conversation).first()
            if ticket and not ticket.google_sheet_synced:
                print(f"🎯 [ICEMAKE POST API CDR RECEIVED]: Syncing real SIM caller number '{data.get('phone_number')}' to Google Sheet!")
                _append_to_google_sheet(ticket, force=False)
        except Exception as e_resync:
            print(f"⚠️ Ice Make POST API Google Sheet sync error: {e_resync}")

    # 🔄 AUTO-DIALER: Trigger next call if a campaign is active
    try:
        from bot.models import CampaignStatus
        status = CampaignStatus.objects.filter(id=1).first()
        if status and status.is_active:
            from bot.views import on_call_ended
            on_call_ended(data.get("phone_number", ""))
    except Exception as e:
        print(f"⚠️ AUTO-DIALER trigger error: {e}")

    return Response(result, status=201)


@api_view(["GET"])
def telecom_cdr_list(request):
    """
    Returns all CDR records with optional filters.
    Query params: ?matched=true|false  &did=+91...  &disposition=ANSWERED
    """
    cdrs = CallDetailRecord.objects.select_related("conversation", "conversation__agent").order_by("-received_at")

    # Filters
    matched = request.GET.get("matched")
    if matched is not None:
        cdrs = cdrs.filter(matched=matched.lower() == "true")

    did = request.GET.get("did")
    if did:
        cdrs = cdrs.filter(did=did)

    disposition = request.GET.get("disposition")
    if disposition:
        cdrs = cdrs.filter(disposition=disposition)

    total = cdrs.count()
    matched_count = cdrs.filter(matched=True).count()
    unmatched_count = cdrs.filter(matched=False).count()

    records = []
    for cdr in cdrs[:200]:  # Limit to 200 records
        record = {
            "id": cdr.id,
            "telecom_call_id": cdr.telecom_call_id,
            "phone_number": cdr.phone_number,
            "calldate": cdr.calldate.isoformat() if cdr.calldate else None,
            "did": cdr.did,
            "duration": cdr.duration,
            "disposition": cdr.disposition,
            "call_type": cdr.call_type,
            "answer_time": cdr.answer_time.isoformat() if cdr.answer_time else None,
            "uniqueid": cdr.uniqueid,
            "recording_file_name": cdr.recording_file_name,
            "matched": cdr.matched,
            "received_at": cdr.received_at.isoformat(),
        }
        if cdr.matched and cdr.conversation:
            record["session_id"] = cdr.conversation.session_id
            record["agent_name"] = cdr.conversation.agent.name if cdr.conversation.agent else None
        records.append(record)

    return Response({
        "total": total,
        "matched": matched_count,
        "unmatched": unmatched_count,
        "records": records,
    })


# ======================================================
# CALL MINUTES USAGE API
# ======================================================
import math

def _round_seconds_to_billed_minutes(total_seconds):
    """
    Rounding logic:
      1-29 sec  → 0.5 min (30 sec)
      30-59 sec → 1 min
      60-89 sec → 1.5 min
      90-119 sec → 2 min
      i.e. round UP to the nearest 30-second interval, then convert to minutes.
    """
    if total_seconds <= 0:
        return 0.0
    # Shift by 1 to align the boundaries correctly (1-29 -> 1, 30-59 -> 2, etc.)
    shifted_seconds = total_seconds + 1
    rounded_intervals = math.ceil(shifted_seconds / 30)
    return rounded_intervals * 30 / 60.0


def _calculate_bot_usage(agent):
    """Calculate total billed minutes for a given VoiceAgent."""
    return agent.used_minutes


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def minutes_usage_api(request):
    """
    Returns call minutes usage vs quota.
    - Superadmin: returns usage for ALL bots
    - Subadmin/User: returns usage for their assigned bot only
    """
    user = request.user
    is_admin = user.is_superuser

    results = []

    if is_admin:
        # Superadmin sees all bots
        bots = VoiceAgent.objects.filter(is_active=True)
        for bot in bots:
            used = _calculate_bot_usage(bot)
            results.append({
                "bot_id": str(bot.id),
                "bot_name": bot.name,
                "used_minutes": used,
                "quota_minutes": bot.minutes_quota,
                "remaining_minutes": round(max(bot.minutes_quota - used, 0), 1),
            })
        # Also provide a combined total
        total_used = sum(r["used_minutes"] for r in results)
        total_quota = sum(r["quota_minutes"] for r in results)
        return Response({
            "is_admin": True,
            "total_used": round(total_used, 1),
            "total_quota": total_quota,
            "total_remaining": round(max(total_quota - total_used, 0), 1),
            "bots": results,
        })
    else:
        # Subadmin / normal user — show their assigned bot's usage
        assigned_agent = None
        if hasattr(user, 'profile') and user.profile.assigned_agent:
            assigned_agent = user.profile.assigned_agent

        if assigned_agent:
            used = _calculate_bot_usage(assigned_agent)
            return Response({
                "is_admin": False,
                "bot_id": str(assigned_agent.id),
                "bot_name": assigned_agent.name,
                "used_minutes": used,
                "quota_minutes": assigned_agent.minutes_quota,
                "remaining_minutes": round(max(assigned_agent.minutes_quota - used, 0), 1),
            })
        else:
            return Response({
                "is_admin": False,
                "used_minutes": 0,
                "quota_minutes": 0,
                "remaining_minutes": 0,
                "message": "No bot assigned to this user.",
            })

def icemake_dashboard_page(request):
    """Renders the ICEMAKE Support & Call Recordings Dashboard page."""
    from django.shortcuts import render
    return render(request, "icemake_dashboard.html")


@api_view(["GET"])
def icemake_dashboard_data(request):
    """
    Returns JSON array of all IcemakeTicket records joined with CallDetailRecord.
    """
    from datetime import timedelta
    from icemake_bot.models import IcemakeTicket
    from conversations.models import CallDetailRecord

    tickets = IcemakeTicket.objects.select_related("conversation").order_by("-created_at")
    
    data = []
    for t in tickets[:200]:
        cdr = None
        # 1. Direct match on conversation CDR
        if t.conversation:
            cdr = CallDetailRecord.objects.filter(conversation=t.conversation).exclude(recording_file_name="").first()
            if not cdr:
                cdr = CallDetailRecord.objects.filter(conversation=t.conversation).first()
        
        # 2. Match by stream SID if available
        if (not cdr or not cdr.recording_file_name) and t.conversation and t.conversation.stream_sid:
            sid = t.conversation.stream_sid.replace("stream_", "")
            cdr = CallDetailRecord.objects.filter(uniqueid=sid).exclude(recording_file_name="").first()
            if not cdr:
                cdr = CallDetailRecord.objects.filter(uniqueid=f"stream_{sid}").exclude(recording_file_name="").first()

        # 3. Match strictly by phone number AND Ice Make strategy key
        if (not cdr or not cdr.recording_file_name) and t.registered_mobile:
            clean_reg = "".join(filter(str.isdigit, str(t.registered_mobile)))[-10:]
            if clean_reg and t.created_at:
                cdr_phone = CallDetailRecord.objects.filter(
                    phone_number__icontains=clean_reg,
                    received_at__gte=t.created_at - timedelta(minutes=15),
                    received_at__lte=t.created_at + timedelta(minutes=15),
                    conversation__agent__role_template__role_name__icontains="Ice Make"
                ).exclude(recording_file_name="").order_by("-received_at").first()
                if cdr_phone:
                    cdr = cdr_phone

        rec_url = getattr(cdr, "recording_file_name", "") or ""
        if rec_url and not rec_url.startswith("http"):
            if rec_url.startswith("/media/"):
                rec_url = request.build_absolute_uri(rec_url)
            else:
                rec_url = f"https://voice-bot.on-forge.com/recordings/{rec_url}"

        duration = getattr(cdr, "duration", 0) or 0
        disposition = getattr(cdr, "disposition", "ANSWERED") or "ANSWERED"
        caller_phone = getattr(cdr, "phone_number", "") or (t.conversation.user_number if t.conversation else t.registered_mobile)

        data.append({
            "id": t.id,
            "ticket_number": t.ticket_number,
            "customer_name": t.customer_name or "Not Provided",
            "registered_mobile": t.registered_mobile or "Not Provided",
            "caller_phone": caller_phone or t.registered_mobile or "Not Provided",
            "city_state": t.city_state or "Not Provided",
            "company_name": t.company_name or "Not Provided",
            "machine_model_no": t.machine_model_no or "Not Provided",
            "issue_type": t.issue_type or "Other",
            "issue_description": t.issue_description or "Not Provided",
            "language": t.language,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "",
            "google_sheet_synced": t.google_sheet_synced,
            "recording_url": rec_url,
            "call_duration": duration,
            "call_status": disposition,
        })

    return Response({"tickets": data})


@api_view(["GET"])
def proxy_audio(request):
    """
    Proxies external audio recording URLs so HTML5 audio element can stream them
    inline without CORS restrictions or missing auth headers.
    Automatically adds the Sarvam X-API-Key for Sarvam Analytics URLs.
    Converts agents.sarvam.ai/media (session-only) to apps.sarvam.ai analytics API URLs.
    """
    import os
    import requests as _requests
    from urllib.parse import urlparse, parse_qs
    from django.http import StreamingHttpResponse, HttpResponse

    audio_url = request.GET.get("url")
    if not audio_url:
        return HttpResponse("Missing url parameter", status=400)

    try:
        headers = {}

        # ✅ Convert *.sarvam.ai/media URLs (e.g. indus.sarvam.ai or agents.sarvam.ai) → apps.sarvam.ai analytics recording URLs
        # The /media URL requires browser session cookie login; the analytics API accepts X-API-Key header.
        if "sarvam.ai" in audio_url and "/media" in audio_url:
            try:
                from conversations.models import SarvamAgent
                parsed = urlparse(audio_url)
                qs = parse_qs(parsed.query)
                org_id = (qs.get("org_id") or [""])[0]
                ws_id = (qs.get("workspace_id") or [""])[0]
                app_id = (qs.get("app_id") or [""])[0]
                interaction_id = (qs.get("interaction_id") or [""])[0]

                # Look up correct API key from DB for this app_id
                agent = SarvamAgent.objects.filter(app_id=app_id, is_active=True).first() if app_id else None
                api_key = (agent.api_key if agent and agent.api_key else os.getenv("SARVAM_AGENT_API_KEY", "")).strip()

                if org_id and ws_id and app_id and interaction_id:
                    # Build the correct analytics recording API URL
                    audio_url = (
                        f"https://apps.sarvam.ai/api/analytics/v1"
                        f"/{org_id}/{ws_id}/{app_id}/recordings/{interaction_id}"
                    )
                    headers["X-API-Key"] = api_key
                    headers["api-subscription-key"] = api_key
                    print(f"🔄 [PROXY AUDIO] Converted media URL to analytics URL for app_id={app_id} (API key: {'Found' if api_key else 'Missing'})")
            except Exception as conv_err:
                print(f"⚠️ [PROXY AUDIO] URL conversion failed: {conv_err}")

        # ✅ For apps.sarvam.ai analytics URLs, smart API key lookup by app_id
        elif "apps.sarvam.ai" in audio_url or "sarvam.ai" in audio_url:
            api_key = os.getenv("SARVAM_AGENT_API_KEY", "").strip()
            try:
                from conversations.models import SarvamAgent
                url_parts = audio_url.split("/")
                if "recordings" in url_parts:
                    rec_idx = url_parts.index("recordings")
                    if rec_idx >= 1:
                        url_app_id = url_parts[rec_idx - 1]
                        matched_agent = SarvamAgent.objects.filter(
                            app_id=url_app_id, is_active=True
                        ).first()
                        if matched_agent and matched_agent.api_key:
                            api_key = matched_agent.api_key.strip()
            except Exception:
                pass
            headers["X-API-Key"] = api_key
            headers["api-subscription-key"] = api_key

        # Forward Range header if browser sent one (essential for seeking/duration in HTML5 audio)
        range_header = request.META.get("HTTP_RANGE")
        if range_header:
            headers["Range"] = range_header

        req = _requests.get(audio_url, headers=headers, stream=True, timeout=20, allow_redirects=True)
        if req.status_code not in (200, 206):
            return HttpResponse(f"Failed to fetch audio: {req.status_code}", status=req.status_code)

        # Detect login redirect (HTML page returned instead of audio)
        content_type = req.headers.get("Content-Type", "audio/mpeg")
        if "text/html" in content_type:
            return HttpResponse("Recording not accessible (authentication required). Use Sync from Sarvam to refresh.", status=403)

        # Safe chunk generator to prevent ChunkedEncodingError / IncompleteRead crashes in ASGI (Daphne)
        def stream_chunks():
            try:
                for chunk in req.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            except Exception as stream_err:
                print(f"⚠️ [PROXY AUDIO STREAM]: Media stream ended/interrupted: {stream_err}")

        response = StreamingHttpResponse(
            stream_chunks(),
            status=req.status_code,
            content_type=content_type
        )
        response["Content-Disposition"] = "inline"
        response["Access-Control-Allow-Origin"] = "*"
        response["Accept-Ranges"] = "bytes"
        if "Content-Length" in req.headers:
            response["Content-Length"] = req.headers["Content-Length"]
        if "Content-Range" in req.headers:
            response["Content-Range"] = req.headers["Content-Range"]
        return response
    except Exception as e:
        return HttpResponse(f"Error streaming audio: {str(e)}", status=500)


def ranged_media_serve(request, path):
    """
    Serves local media files with HTTP 206 Partial Content (Range request) support
    so HTML5 audio/video elements in Chrome, Edge, and Safari can stream, seek, 
    and play full audio recordings from start to finish without stopping early.
    """
    import os
    import re
    from django.conf import settings
    from django.http import HttpResponse, Http404, FileResponse

    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        raise Http404("Media file not found")

    file_size = os.path.getsize(file_path)
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = re.match(r'bytes=(\d+)-(\d+)?', range_header)

    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        if start >= file_size:
            return HttpResponse(status=416)

        end = min(end, file_size - 1)
        length = end - start + 1

        with open(file_path, 'rb') as f:
            f.seek(start)
            data = f.read(length)

        response = HttpResponse(data, status=206, content_type='audio/mpeg')
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Content-Length'] = str(length)
        response['Accept-Ranges'] = 'bytes'
        return response

    response = FileResponse(open(file_path, 'rb'), content_type='audio/mpeg')
    response['Content-Length'] = str(file_size)
    response['Accept-Ranges'] = 'bytes'
    return response


# ======================================================
# SARVAM AI AGENT LEADS & SCREENING DASHBOARD
# ======================================================

def sarvam_leads_page(request, agent_slug=None):
    """Renders Sarvam AI Agent Leads & Candidate Screening Dashboard."""
    from conversations.models import SarvamAgent
    
    user = request.user if request.user.is_authenticated else None
    
    is_admin = False
    if user:
        if user.is_superuser:
            is_admin = True
        elif hasattr(user, 'profile') and user.profile and user.profile.role:
            perms = user.profile.role.permissions
            if perms.get('is_admin', False):
                is_admin = True
        if hasattr(user, 'profile') and user.profile and user.profile.custom_permissions:
            if user.profile.custom_permissions.get('is_admin', False):
                is_admin = True

    # If user is a regular user with assigned Sarvam agents, restrict to their assigned agents
    if user and not is_admin and hasattr(user, 'profile') and user.profile:
        assigned_qs = user.profile.assigned_sarvam_agents.filter(is_active=True).order_by("name")
        if assigned_qs.exists():
            all_agent_objs = assigned_qs
        else:
            all_agent_objs = SarvamAgent.objects.filter(is_active=True).order_by("name")
    else:
        all_agent_objs = SarvamAgent.objects.filter(is_active=True).order_by("name")

    # Resolve sarvam_agent for this page
    sarvam_agent = None
    if agent_slug:
        sarvam_agent = all_agent_objs.filter(slug=agent_slug).first()
    if not sarvam_agent:
        sarvam_agent = all_agent_objs.first()

    # Build list of active agents for the nav switcher with minutes details
    all_agents = []
    for ag in all_agent_objs:
        all_agents.append({
            "name": ag.name,
            "slug": ag.slug,
            "agent_phone": ag.agent_phone,
            "allocated_minutes": ag.allocated_minutes,
            "remaining_minutes": ag.remaining_minutes,
            "is_exhausted": ag.is_minutes_exhausted,
        })

    context = {
        "agent_slug": sarvam_agent.slug if sarvam_agent else "default",
        "agent_name": sarvam_agent.name if sarvam_agent else "Voice AI Agent",
        "agent_phone": sarvam_agent.agent_phone if sarvam_agent else "",
        "all_agents": all_agents,
        "allocated_minutes": sarvam_agent.allocated_minutes if sarvam_agent else 5000.0,
        "used_minutes": sarvam_agent.total_used_minutes if sarvam_agent else 0.0,
        "remaining_minutes": sarvam_agent.remaining_minutes if sarvam_agent else 5000.0,
        "is_minutes_exhausted": sarvam_agent.is_minutes_exhausted if sarvam_agent else False,
        "usage_percentage": sarvam_agent.usage_percentage if sarvam_agent else 0.0,
    }
    return render(request, "sarvam_leads.html", context)


def classify_sarvam_lead_status(status=None, summary=None, transcript=None, duration_seconds=0):
    """
    Intelligently classifies a Sarvam AI call into standardized CRM lead statuses:
    - 'INTERVIEW': Interested / High Intent / Store Visit / Budget / Upgrade discussed
    - 'CALLBACK': Callback Requested / WhatsApp Offers / Festive Offers Requested / Follow-up
    - 'NOT_INTERESTED': Explicitly declined, not interested, rejected, dropped without interest
    - 'NO_ANSWER': Missed, busy, no answer, dialing failure
    - 'COMPLETED': Engaged completed call
    """
    raw_status = (str(status) if status else "").upper().strip()
    if raw_status in ["NO_ANSWER", "MISSED", "BUSY", "FAILED", "CANCELLED", "TIMEOUT"]:
        return "NO_ANSWER"

    try:
        dur = float(duration_seconds or 0)
    except (ValueError, TypeError):
        dur = 0.0

    if dur <= 0 and raw_status in ["NO_ANSWER", "PENDING", "DIALING"]:
        return "NO_ANSWER"

    text_corpus = [raw_status]
    if isinstance(summary, dict):
        for k, v in summary.items():
            if isinstance(v, str):
                text_corpus.append(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        text_corpus.append(str(item.get("en_text") or item.get("text") or item.get("content") or ""))
                    elif isinstance(item, str):
                        text_corpus.append(item)
    elif isinstance(summary, str):
        text_corpus.append(summary)

    if transcript:
        text_corpus.append(str(transcript))

    text = " ".join(text_corpus).lower()

    # 1. NOT INTERESTED / DECLINED / DROPPED
    not_int_patterns = [
        "not interested", "not_interested", "declined", "rejected", "no need", "wrong number",
        "refused", "hung up immediately", "did not want", "don't want", "not looking for",
        "ended without a response", "stalled before", "no response from",
        "નથી જોઈતું", "જરૂર નથી", "રસ નથી", "રોંગ નંબર", "નહિ જોઈએ", "रुचि नहीं है", "नहीं चाहिए"
    ]
    if any(p in text for p in not_int_patterns):
        return "NOT_INTERESTED"

    # 2. CALLBACK / OFFERS REQUESTED / WHATSAPP
    callback_patterns = [
        "callback", "call back", "call later", "call you later", "talk later", "call tomorrow",
        "busy right now", "not available to talk", "call at a later time", "contact later",
        "whatsapp", "festive offer", "festive offers", "send details", "send info", "share details",
        "send brochure", "send link", "send on whatsapp", "offers via whatsapp",
        "મોકલી દો", "મોકલો", "ઓફર", "પછી ફોન", "પછી વાત", "કાલે ફોન", "કાલે કરજો",
        "હમણાં નહિ", "હમણાં ટાઈમ નથી", "વોટ્સએપ", "भेज देना", "डिटेલ્સ भेजना", "बाद में बात", "कल करना"
    ]
    if any(p in text for p in callback_patterns):
        return "CALLBACK"

    # 3. INTERESTED / HIGH INTENT / STORE VISIT / UPGRADE / BUDGET / MODELS
    high_intent_patterns = [
        "expressed interest", "interested in", "interest in", "interested", "high intent",
        "budget of", "budget is", "looking to buy", "looking for", "upgrade", "upgrading",
        "purchase", "purchased", "visit the store", "store visit", "demo", "available models",
        "models available", "confirmed", "schedule", "scheduled", "interview", "admission",
        "positive", "product inquiry", "new phone", "wants to buy", "ready to visit",
        "મોડેલ", "લેવું છે", "ખરીદવું", "સ્ટોર", "દુકાન", "બજેટ", "રૂપિયા", "આવીશ", "જોવું છે",
        "કયા કયા મોડેલ", "ખરીદના", "लेना है", "रुचि", "दुकान आना", "मॉडल देखना"
    ]
    if any(p in text for p in high_intent_patterns):
        return "INTERVIEW"

    # 4. Short calls with no conversation
    if dur < 10:
        return "NOT_INTERESTED"

    # 5. Fallback for engaged answered calls
    return "INTERVIEW" if dur >= 25 else "COMPLETED"


@api_view(["GET"])
def sarvam_leads_data(request, agent_slug=None):
    """
    Fetches real-time Sarvam AI Agent interactions, applicant leads, screening metrics, and audio links.
    Merges local database records (triggered calls & webhooks) with Sarvam Analytics API.
    Scoped per agent when agent_slug is provided.
    """
    import os
    import requests as http_requests
    from datetime import datetime, timedelta
    from conversations.models import SarvamCallRecord, SarvamAgent
    from conversations.services.kylas_sarvam_bridge import SarvamAgentService

    # Resolve which sarvam agent to use
    slug = agent_slug or request.GET.get("agent")
    user = request.user if request.user.is_authenticated else None
    is_admin = False
    if user:
        if user.is_superuser:
            is_admin = True
        elif hasattr(user, 'profile') and user.profile and user.profile.role:
            perms = user.profile.role.permissions
            if perms.get('is_admin', False):
                is_admin = True
        if hasattr(user, 'profile') and user.profile and user.profile.custom_permissions:
            if user.profile.custom_permissions.get('is_admin', False):
                is_admin = True

    sarvam_agent = None
    if user and not is_admin and hasattr(user, 'profile') and user.profile:
        assigned_qs = user.profile.assigned_sarvam_agents.filter(is_active=True)
        if assigned_qs.exists():
            if slug and assigned_qs.filter(slug=slug).exists():
                sarvam_agent = assigned_qs.filter(slug=slug).first()
            else:
                sarvam_agent = assigned_qs.first()

    if not sarvam_agent:
        if slug:
            sarvam_agent = SarvamAgent.objects.filter(slug=slug, is_active=True).first()
        if not sarvam_agent:
            sarvam_agent = SarvamAgent.objects.filter(is_active=True).first()

    # Use agent credentials (or fall back to env)
    if sarvam_agent:
        org_id = sarvam_agent.org_id
        workspace_id = sarvam_agent.workspace_id
        app_id = sarvam_agent.app_id
        api_key = sarvam_agent.api_key
    else:
        org_id = os.getenv("SARVAM_ORG_ID", "01a03cbf-1bf4-70f0-995f-854d6d2dd105")
        workspace_id = os.getenv("SARVAM_WORKSPACE_ID", "01a03cbf-1bfb-770a-bb91-06baeec9d28e")
        app_id = os.getenv("SARVAM_AGENT_ID", "iiiEM---Rec-136dc7be-adb6")
        api_key = os.getenv("SARVAM_AGENT_API_KEY", "sk_samvaad_9oozxe0h_jqecMJbqT5yaD6gvE4fLPRlO")

    days_back = int(request.GET.get("days", 30))
    now = datetime.utcnow()
    start_dt = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    end_dt = now.strftime("%Y-%m-%dT23:59:59Z")

    sarvam_url = f"https://apps.sarvam.ai/api/analytics/v1/{org_id}/{workspace_id}/{app_id}/interactions"
    headers = {"X-API-Key": api_key}
    params = {"start_datetime": start_dt, "end_datetime": end_dt, "limit": 100}

    remote_items = []
    try:
        res = http_requests.get(sarvam_url, headers=headers, params=params, timeout=10)
        if res.status_code == 200 and res.content:
            remote_items = res.json().get("items", [])
    except Exception as e:
        print(f"⚠️ [SARVAM ANALYTICS API FETCH WARNING]: {e}")

    processed_leads = []
    seen_ids = set()

    # ✅ ANTI-LEAK FIX: Pre-load all phone numbers & interaction_ids from OTHER agents' records.
    # This blocks remote API items from appearing on the wrong agent's dashboard,
    # even when a shared API key returns cross-org data from the Sarvam Analytics API.
    if sarvam_agent:
        other_agent_records = SarvamCallRecord.objects.exclude(sarvam_agent=sarvam_agent)
    else:
        other_agent_records = SarvamCallRecord.objects.none()

    for other_r in other_agent_records.values_list("phone_number", "interaction_id"):
        phone_raw, iid = other_r
        if phone_raw:
            clean_p = "".join(filter(str.isdigit, str(phone_raw)))
            if len(clean_p) >= 10:
                seen_ids.add(clean_p[-10:])
        if iid:
            seen_ids.add(iid)

    # Filter local records scoped to this agent
    if sarvam_agent:
        local_records = SarvamCallRecord.objects.filter(sarvam_agent=sarvam_agent).order_by("-created_at")
    else:
        local_records = SarvamCallRecord.objects.all().order_by("-created_at")

    for r in local_records:
        # 🟥 FIX: Skip and merge orphaned dummy webhook records with unknown phone number into valid sibling records
        if not r.phone_number or r.phone_number in ["unknown", "N/A", "", "none"]:
            from datetime import timedelta
            t_min = r.created_at - timedelta(minutes=30)
            t_max = r.created_at + timedelta(minutes=30)
            valid_sibling = SarvamCallRecord.objects.filter(
                sarvam_agent=r.sarvam_agent,
                created_at__range=(t_min, t_max)
            ).exclude(id=r.id).exclude(phone_number__in=["unknown", "N/A", "", "none"]).first()
            if valid_sibling:
                if r.transcript and not valid_sibling.transcript:
                    valid_sibling.transcript = r.transcript
                    valid_sibling.save(update_fields=["transcript"])
                if r.summary and not valid_sibling.summary:
                    valid_sibling.summary = r.summary
                    valid_sibling.save(update_fields=["summary"])
                if r.audio_url and not valid_sibling.audio_url:
                    valid_sibling.audio_url = r.audio_url
                    valid_sibling.save(update_fields=["audio_url"])
                if r.interaction_id and not valid_sibling.interaction_id:
                    valid_sibling.interaction_id = r.interaction_id
                    valid_sibling.save(update_fields=["interaction_id"])
                print(f"🧹 [AUTO-CLEANUP]: Merged and deleted orphaned dummy record #{r.id} into valid call #{valid_sibling.id} ({valid_sibling.phone_number})")
                r.delete()
                continue

        # 🟥 FIX: Reset any interaction_id that is a bare UUID (no slash) — it was assigned incorrectly
        if r.interaction_id and "/" not in r.interaction_id:
            r.interaction_id = None
            r.audio_url = None
            r.save(update_fields=["interaction_id", "audio_url"])

        age_sec = (now - r.created_at.replace(tzinfo=None)).total_seconds()

        if not r.interaction_id and r.phone_number and r.phone_number != "unknown":
            matched_item = None
            # Priority 1: Match by attempt_id == job_id (exact unique match for API calls)
            if r.attempt_id:
                for item in remote_items:
                    ijob = item.get("job_id") or item.get("jobId") or item.get("attempt_id") or item.get("attemptId")
                    if ijob and str(ijob).strip() == str(r.attempt_id).strip():
                        matched_item = item
                        break

            # Priority 2: Match by phone number ONLY IF within 15 minutes of record creation
            if not matched_item and not r.attempt_id:
                clean_r_phone = "".join(filter(str.isdigit, str(r.phone_number)))[-10:]
                for item in remote_items:
                    icontact = item.get("user_contact") or item.get("user_phone_number") or item.get("phone_number") or ""
                    clean_item_phone = "".join(filter(str.isdigit, str(icontact)))[-10:]
                    if clean_r_phone and clean_item_phone and clean_r_phone == clean_item_phone:
                        item_start = item.get("start_datetime") or item.get("attempted_at")
                        if item_start:
                            try:
                                from django.utils.dateparse import parse_datetime
                                dt_val = parse_datetime(str(item_start))
                                if dt_val:
                                    diff_sec = abs((r.created_at.replace(tzinfo=None) - dt_val.replace(tzinfo=None)).total_seconds())
                                    if diff_sec <= 900:  # Within 15 minutes
                                        matched_item = item
                                        break
                            except Exception:
                                pass

            if matched_item:
                agent_vars = matched_item.get("agent_variables", {}) or {}
                call_sum = agent_vars.get("call_summary") or {}
                r.interaction_id = matched_item.get("interaction_id")
                
                final_status = call_sum.get("final_status") if isinstance(call_sum, dict) and call_sum.get("final_status") else "COMPLETED"
                r.status = final_status
                
                r.duration_seconds = float(matched_item.get("duration_in_seconds", 0)) or r.duration_seconds
                r.audio_url = matched_item.get("audio_url") or r.audio_url
                
                if isinstance(call_sum, dict) and call_sum:
                    if not r.summary or len(str(r.summary)) < len(str(call_sum)):
                        r.summary = call_sum

                # Auto fetch transcript if missing
                if r.interaction_id and not r.transcript:
                    t_res = SarvamAgentService.fetch_interaction_transcript(interaction_id=r.interaction_id)
                    if isinstance(t_res, list):
                        r.transcript = "\n\n".join([f"{t.get('role', 'Speaker').upper()}: {t.get('text', '') or t.get('content', '')}" for t in t_res])
                    elif isinstance(t_res, dict):
                        if "messages" in t_res:
                            msgs = t_res.get("messages") or []
                            r.transcript = "\n\n".join([f"{m.get('role', 'Speaker').upper()}: {m.get('content', '') or m.get('text', '')}" for m in msgs])
                        else:
                            r.transcript = t_res.get("transcript") or t_res.get("text") or t_res.get("raw_text") or ""
                        
                r.save()
                print(f"✅ [AUTO-SYNC]: Mapped {r.interaction_id} to call #{r.id} ({r.candidate_name})")
            elif age_sec > 90 and r.status in ["DIALING", "PENDING"]:
                r.status = "NO_ANSWER"
                r.save(update_fields=["status"])

        if r.interaction_id and not r.audio_url and "/" in r.interaction_id:
            rec_result = SarvamAgentService.fetch_interaction_recording(r.interaction_id)
            if rec_result:
                if isinstance(rec_result, str) and rec_result.startswith("http"):
                    r.audio_url = rec_result
                elif isinstance(rec_result, dict):
                    r.audio_url = rec_result.get("recording_url") or rec_result.get("audio_url") or rec_result.get("url")
                if r.audio_url:
                    r.save(update_fields=["audio_url"])

        rec_id = r.interaction_id or r.attempt_id or f"local_{r.id}"
        seen_ids.add(rec_id)
        if r.phone_number:
            seen_ids.add(r.phone_number)

        # Ensure detected_language from summary updates r.language if present
        if isinstance(r.summary, dict) and r.summary.get("detected_language"):
            det_lang = r.summary.get("detected_language")
            if det_lang and det_lang != r.language:
                r.language = det_lang
                r.save(update_fields=["language"])

        # Determine call direction
        c_type_str = str(getattr(r, "call_type", "") or "")
        if "inbound" in c_type_str.lower():
            direction = "inbound"
            call_dir_display = "Inbound Call"
        elif r.campaign or "campaign" in c_type_str.lower():
            direction = "outbound"
            call_dir_display = f"Outbound (Stage {r.campaign_stage})" if r.campaign_stage else "Outbound Campaign"
        else:
            direction = "outbound"
            call_dir_display = "Outbound Call"

        # Helper function for universal requirement resolution
        def _get_requirement_str(summary_dict, raw_pos=None):
            if isinstance(summary_dict, dict):
                for key in ["car_model", "product_interest", "product_name", "flat_type", "loan_type", "course_name", "requirement", "interest"]:
                    v = summary_dict.get(key)
                    if v and str(v).strip() and str(v).strip().lower() not in ["none", "null", "unknown", "n/a", "candidate", "customer"]:
                        return str(v).strip()
            if raw_pos and str(raw_pos).strip() and str(raw_pos).strip().lower() not in ["none", "null", "unknown", "n/a", "candidate", "customer", "admission counselor"]:
                return str(raw_pos).strip()
            return "General Inquiry"

        lead_cand_name = r.candidate_name
        if not lead_cand_name or lead_cand_name.lower() in ["candidate", "unknown candidate", "unknown", "none", "null", ""]:
            lead_cand_name = "Customer"

        processed_leads.append({
            "interaction_id": rec_id,
            "contact": r.phone_number,
            "candidate_name": lead_cand_name,
            "applied_position": _get_requirement_str(r.summary or {}, r.applied_position),
            "call_type": getattr(r, "call_type", "Live Call") or "Live Call",
            "direction": direction,
            "call_direction_display": call_dir_display,
            "duration_seconds": round(r.duration_seconds, 1),
            "billed_seconds": r.billed_seconds or int(math.ceil(float(r.duration_seconds or 0) / 30.0) * 30),
            "language": r.language or "Hindi",
            "attempted_at": r.start_time.strftime("%Y-%m-%dT%H:%M:%SZ") if getattr(r, "start_time", None) else r.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "audio_url": r.audio_url,
            "final_status": r.status,
            "summary": r.summary or {},
            "transcript": r.transcript or "",
        })

    # Determine retail agent (agent-level flag, used in both local and remote loops)
    is_retail = bool(sarvam_agent and (sarvam_agent.slug in ["vtech", "samsung"] or "samsung" in sarvam_agent.slug or "samsung" in sarvam_agent.name.lower()))

    def _normalize_phone(raw):
        if not raw:
            return ""
        digits = "".join(filter(str.isdigit, str(raw)))
        return digits[-10:] if len(digits) >= 10 else digits

    local_contacts = set()
    if sarvam_agent:
        local_recs_for_agent = SarvamCallRecord.objects.filter(sarvam_agent=sarvam_agent)
    else:
        local_recs_for_agent = SarvamCallRecord.objects.all()
    for lr in local_recs_for_agent.values_list("phone_number", flat=True):
        norm = _normalize_phone(lr)
        if norm:
            local_contacts.add(norm)

    # Collect remote items that pass the anti-leak filter
    new_remote_to_persist = []

    for item in remote_items:
        iid = item.get("interaction_id")
        if not iid:
            continue

        raw_phone = item.get("user_phone_number") or item.get("phone_number") or ""
        clean_item_p = _normalize_phone(raw_phone)
        item_user_id = item.get("user_identifier") or ""
        item_agent_p = item.get("agent_phone_number") or ""

        # ANTI-LEAK FILTER: Match by interaction_id prefix, agent phone, user_identifier, or known contact
        is_owner = False
        if sarvam_agent:
            if sarvam_agent.agent_phone and item_agent_p and sarvam_agent.agent_phone in item_agent_p:
                is_owner = True
            elif sarvam_agent.app_id and item.get("app_id") and sarvam_agent.app_id == item.get("app_id"):
                is_owner = True
            elif clean_item_p and clean_item_p in local_contacts:
                is_owner = True
            elif item_user_id and _normalize_phone(item_user_id) in local_contacts:
                is_owner = True
            elif not local_contacts:
                # If no local records exist yet, accept items from this agent's API response
                is_owner = True
        else:
            is_owner = True

        if not is_owner:
            continue

        if iid in seen_ids or (clean_item_p and clean_item_p in seen_ids):
            continue
        seen_ids.add(iid)
        if clean_item_p:
            seen_ids.add(clean_item_p)

        call_summary = item.get("call_summary") or {}
        candidate_name = (
            item.get("user_name")
            or item.get("candidate_name")
            or (call_summary.get("candidate_name") if isinstance(call_summary, dict) else None)
            or (call_summary.get("user_name") if isinstance(call_summary, dict) else None)
            or (call_summary.get("customer_name") if isinstance(call_summary, dict) else None)
            or "Customer"
        )
        if not candidate_name or candidate_name.lower() in ["candidate", "unknown candidate", "unknown", "none", "null", ""]:
            candidate_name = "Customer"

        contact = item.get("user_phone_number") or item.get("phone_number") or item_user_id or ""
        final_status = item.get("status") or "COMPLETED"

        # Determine remote call direction
        remote_dir = "inbound" if (item.get("direction") == "inbound" or not item.get("attempt_id")) else "outbound"
        remote_dir_display = "Inbound Call" if remote_dir == "inbound" else "Outbound Call"

        remote_dur = float(item.get("duration_in_seconds", 0))
        processed_leads.append({
            "interaction_id": iid,
            "contact": contact or "N/A",
            "candidate_name": candidate_name,
            "applied_position": _get_requirement_str(call_summary, call_summary.get("applied_position") if isinstance(call_summary, dict) else None),
            "call_type": "Inbound Call" if (remote_dir == "inbound") else "Outbound Call",
            "direction": remote_dir,
            "call_direction_display": remote_dir_display,
            "duration_seconds": round(remote_dur, 1),
            "billed_seconds": int(math.ceil(remote_dur / 30.0) * 30) if remote_dur > 0 else 0,
            "language": item.get("language_name", "Hindi"),
            "attempted_at": item.get("attempted_at") or item.get("start_datetime"),
            "audio_url": item.get("audio_url"),
            "final_status": final_status or "COMPLETED",
            "summary": call_summary,
            "transcript": "",
        })
        # Queue for DB persistence
        new_remote_to_persist.append((item, call_summary, candidate_name, final_status, clean_item_p))

    # ✅ AUTO-PERSIST: Save all remote API items to local DB in a background thread
    # This ensures every call shown on the dashboard is also permanently stored.
    def _persist_remote_items(items_to_save, agent):
        """Background thread: upsert each remote Sarvam item into SarvamCallRecord."""
        import django
        for item, call_summary, candidate_name, final_status, clean_phone in items_to_save:
            iid = item.get("interaction_id")
            if not iid:
                continue
            try:
                # Build transcript from conversation_log if present
                conv_log = item.get("conversation_log") or []
                transcript_text = ""
                if conv_log and isinstance(conv_log, list):
                    transcript_text = "\n\n".join([
                        f"{m.get('role', 'speaker').upper()}: {m.get('en_text') or m.get('text') or ''}"
                        for m in conv_log
                    ])

                # Parse start_time
                from datetime import datetime as dt
                start_time_raw = item.get("attempted_at") or item.get("start_datetime")
                start_time_val = None
                if start_time_raw:
                    try:
                        from django.utils.dateparse import parse_datetime
                        start_time_val = parse_datetime(str(start_time_raw))
                    except Exception:
                        pass

                defaults = {
                    "sarvam_agent": agent,
                    "candidate_name": candidate_name or "Unknown Candidate",
                    "applied_position": call_summary.get("applied_position", "Admission Counselor") if isinstance(call_summary, dict) else "Admission Counselor",
                    "language": item.get("language_name", "hi-IN"),
                    "status": final_status or "COMPLETED",
                    "duration_seconds": round(float(item.get("duration_in_seconds", 0)), 1),
                    "audio_url": item.get("audio_url") or "",
                    "summary": call_summary if isinstance(call_summary, dict) else {},
                    "call_type": "Sarvam API",
                }
                if start_time_val:
                    defaults["start_time"] = start_time_val
                if transcript_text:
                    defaults["transcript"] = transcript_text
                if clean_phone:
                    defaults["phone_number"] = clean_phone

                # Upsert by interaction_id
                obj, created = SarvamCallRecord.objects.update_or_create(
                    interaction_id=iid,
                    defaults=defaults
                )
                if created:
                    print(f"✅ [AUTO-PERSIST] Saved new call to DB: {iid} | {candidate_name} | {clean_phone}")
                else:
                    # Patch any missing fields on existing record
                    needs_save = False
                    if not obj.audio_url and item.get("audio_url"):
                        obj.audio_url = item.get("audio_url")
                        needs_save = True
                    if not obj.transcript and transcript_text:
                        obj.transcript = transcript_text
                        needs_save = True
                    if not obj.sarvam_agent and agent:
                        obj.sarvam_agent = agent
                        needs_save = True
                    if needs_save:
                        obj.save()
            except Exception as ex:
                print(f"⚠️ [AUTO-PERSIST] Failed for {iid}: {ex}")

    if new_remote_to_persist:
        import threading
        t = threading.Thread(
            target=_persist_remote_items,
            args=(new_remote_to_persist, sarvam_agent),
            daemon=True
        )
        t.start()

    stats = {
        "total_calls": len(processed_leads),
        "interview_scheduled": 0,
        "high_intent": 0,
        "callback_required": 0,
        "not_interested": 0,
        "role_mismatch": 0,
        "completed": 0,
        "incomplete": 0
    }
    for lead in processed_leads:
        final_st = classify_sarvam_lead_status(
            lead.get("final_status"),
            lead.get("summary"),
            lead.get("transcript"),
            lead.get("duration_seconds")
        )
        lead["final_status"] = final_st

        if final_st == "INTERVIEW":
            stats["interview_scheduled"] += 1
            stats["high_intent"] += 1
        elif final_st == "CALLBACK":
            stats["callback_required"] += 1
        elif final_st == "NOT_INTERESTED":
            stats["not_interested"] += 1
        elif final_st == "NO_ANSWER":
            stats["not_interested"] += 1
        elif final_st == "MISMATCH":
            stats["role_mismatch"] += 1
            stats["not_interested"] += 1
        else:
            stats["completed"] += 1

    agent_minutes_info = {
        "allocated_minutes": sarvam_agent.allocated_minutes if sarvam_agent else 5000.0,
        "used_minutes": sarvam_agent.total_used_minutes if sarvam_agent else 0.0,
        "remaining_minutes": sarvam_agent.remaining_minutes if sarvam_agent else 5000.0,
        "is_exhausted": sarvam_agent.is_minutes_exhausted if sarvam_agent else False,
        "usage_percentage": sarvam_agent.usage_percentage if sarvam_agent else 0.0,
    }

    return Response({
        "total": len(processed_leads),
        "stats": stats,
        "agent_minutes": agent_minutes_info,
        "leads": processed_leads
    }, status=200)


@api_view(["GET"])
def sarvam_transcript_detail(request, interaction_id, agent_slug=None):
    """Fetches transcript for a specific interaction_id.
    Priority: 1) Local DB transcript (from CDR webhook) → 2) Sarvam Analytics API
    Accepts optional agent_slug from per-agent URL routes.
    """
    import os
    import requests
    from urllib.parse import unquote
    from conversations.models import SarvamCallRecord, SarvamAgent
    from conversations.services.kylas_sarvam_bridge import SarvamAgentService

    # Resolve agent for per-agent API calls (used if we fall back to Sarvam API)
    sarvam_agent = None
    if agent_slug:
        sarvam_agent = SarvamAgent.objects.filter(slug=agent_slug, is_active=True).first()
    if not sarvam_agent:
        sarvam_agent = SarvamAgent.objects.filter(is_active=True).first()

    clean_id = unquote(interaction_id).strip()

    rec = SarvamCallRecord.objects.filter(interaction_id=clean_id).first()
    if not rec:
        rec = SarvamCallRecord.objects.filter(attempt_id=clean_id).first()
    if not rec and clean_id.startswith("local_"):
        try:
            local_pk = int(clean_id.replace("local_", ""))
            rec = SarvamCallRecord.objects.filter(id=local_pk).first()
        except ValueError:
            pass

    if rec:
        if not rec.interaction_id and rec.attempt_id:
            res = SarvamAgentService.list_interactions()
            for item in res.get("items", []):
                ijob = item.get("job_id") or item.get("jobId") or item.get("attempt_id") or item.get("attemptId")
                if ijob and str(ijob).strip() == str(rec.attempt_id).strip():
                    rec.interaction_id = item.get("interaction_id")
                    rec.audio_url = item.get("audio_url") or rec.audio_url
                    rec.duration_seconds = float(item.get("duration_in_seconds", 0)) or rec.duration_seconds
                    agent_vars = item.get("agent_variables", {}) or {}
                    call_sum = agent_vars.get("call_summary") or {}
                    if isinstance(call_sum, dict) and call_sum.get("final_status"):
                        rec.status = call_sum.get("final_status")
                        rec.summary = call_sum
                    rec.save()
                    break

        # ✅ Priority 1: If transcript already exists in local DB (from CDR webhook), return it immediately
        if rec.transcript:
            raw = rec.transcript
            messages = []
            if isinstance(raw, str) and "\n\n" in raw:
                for line in raw.strip().split("\n\n"):
                    if ": " in line:
                        role_part, _, text_part = line.partition(": ")
                        messages.append({
                            "role": role_part.strip().lower(),
                            "en_text": text_part.strip(),
                            "text": text_part.strip()
                        })
            if messages:
                return Response({"messages": messages, "transcript": raw}, status=200)
            return Response({"transcript": raw, "messages": []}, status=200)

        # Priority 2: Fetch from Sarvam API using this agent's credentials
        if rec.interaction_id and not rec.transcript:
            t_res = SarvamAgentService.fetch_interaction_transcript(
                interaction_id=rec.interaction_id, sarvam_agent=sarvam_agent
            )
            if isinstance(t_res, list):
                rec.transcript = "\n\n".join([f"{t.get('role', 'Speaker').upper()}: {t.get('text', '') or t.get('content', '')}" for t in t_res])
                rec.save(update_fields=["transcript"])
            elif isinstance(t_res, dict):
                if "messages" in t_res:
                    msgs = t_res.get("messages") or []
                    rec.transcript = "\n\n".join([f"{m.get('role', 'Speaker').upper()}: {m.get('content', '') or m.get('text', '')}" for m in msgs])
                else:
                    rec.transcript = t_res.get("transcript") or t_res.get("text") or t_res.get("raw_text") or ""
                rec.save(update_fields=["transcript"])

        if rec.transcript:
            raw = rec.transcript
            messages = []
            if isinstance(raw, str) and "\n\n" in raw:
                for line in raw.strip().split("\n\n"):
                    if ": " in line:
                        role_part, _, text_part = line.partition(": ")
                        messages.append({
                            "role": role_part.strip().lower(),
                            "en_text": text_part.strip(),
                            "text": text_part.strip()
                        })
            if messages:
                return Response({"messages": messages, "transcript": raw}, status=200)
            return Response({"transcript": raw, "messages": []}, status=200)

    target_id = rec.interaction_id if (rec and rec.interaction_id) else clean_id
    if "/" in target_id:
        t_res = SarvamAgentService.fetch_interaction_transcript(
            interaction_id=target_id, sarvam_agent=sarvam_agent
        )
        if isinstance(t_res, list):
            messages = [
                {"role": t.get("role", "speaker").lower(), "en_text": t.get("text", "") or t.get("content", ""), "text": t.get("text", "") or t.get("content", "")}
                for t in t_res
            ]
            raw_text = "\n\n".join([f"{t.get('role', 'Speaker').upper()}: {t.get('text', '') or t.get('content', '')}" for t in t_res])
            if rec:
                rec.transcript = raw_text
                rec.save(update_fields=["transcript"])
            return Response({"messages": messages, "transcript": raw_text}, status=200)
        elif isinstance(t_res, dict):
            if "messages" in t_res:
                msgs = t_res.get("messages") or []
                messages = [
                    {"role": m.get("role", "speaker").lower(), "en_text": m.get("content", "") or m.get("text", ""), "text": m.get("content", "") or m.get("text", "")}
                    for m in msgs
                ]
                raw_text = "\n\n".join([f"{m.get('role', 'Speaker').upper()}: {m.get('content', '') or m.get('text', '')}" for m in msgs])
                if rec:
                    rec.transcript = raw_text
                    rec.save(update_fields=["transcript"])
                return Response({"messages": messages, "transcript": raw_text}, status=200)
            return Response(t_res, status=200)

    return Response({"transcript": "Transcript not available for this session yet.", "messages": []}, status=200)


@api_view(["POST"])
def sarvam_trigger_call_api(request, agent_slug=None):
    """Triggers an outbound call directly from the Sarvam AI Agent dashboard."""
    import os
    from conversations.models import SarvamCallRecord, SarvamAgent

    data = request.data or {}
    phone_number = data.get("phone_number") or data.get("phone")
    candidate_name = data.get("candidate_name") or data.get("name") or "Candidate"
    language = data.get("language") or "hi-IN"

    # Resolve which sarvam agent to use
    slug = agent_slug or data.get("agent_slug")
    user = request.user if request.user.is_authenticated else None
    is_admin = False
    if user:
        if user.is_superuser:
            is_admin = True
        elif hasattr(user, 'profile') and user.profile and user.profile.role:
            perms = user.profile.role.permissions
            if perms.get('is_admin', False):
                is_admin = True
        if hasattr(user, 'profile') and user.profile and user.profile.custom_permissions:
            if user.profile.custom_permissions.get('is_admin', False):
                is_admin = True

    sarvam_agent = None
    if user and not is_admin and hasattr(user, 'profile') and user.profile:
        assigned_qs = user.profile.assigned_sarvam_agents.filter(is_active=True)
        if assigned_qs.exists():
            if slug and assigned_qs.filter(slug=slug).exists():
                sarvam_agent = assigned_qs.filter(slug=slug).first()
            else:
                sarvam_agent = assigned_qs.first()

    if not sarvam_agent:
        if slug:
            sarvam_agent = SarvamAgent.objects.filter(slug=slug, is_active=True).first()
        if not sarvam_agent:
            sarvam_agent = SarvamAgent.objects.filter(is_active=True).first()

    if not phone_number:
        return Response({"error": "Phone number is required"}, status=400)

    if sarvam_agent and getattr(sarvam_agent, "is_minutes_exhausted", False):
        return Response({
            "status": "error",
            "code": "MINUTES_EXHAUSTED",
            "error": "Call minutes limit is over for this agent. To continue service, please add minutes.",
            "message": "Call minutes limit is over for this agent. To continue service, please add minutes.",
            "remaining_minutes": 0,
        }, status=400)

    from conversations.services.kylas_sarvam_bridge import SarvamAgentService
    result = SarvamAgentService.trigger_outbound_call(
        phone_number=str(phone_number),
        lead_id=0,
        customer_name=candidate_name,
        language=language,
        sarvam_agent=sarvam_agent,
    )

    if isinstance(result, dict) and (result.get("code") == "MINUTES_EXHAUSTED" or result.get("status") == "error"):
        return Response({
            "status": "error",
            "code": "MINUTES_EXHAUSTED",
            "error": result.get("error") or "Call minutes limit is over for this agent. To continue service, please add minutes.",
            "message": result.get("message") or "Call minutes limit is over for this agent. To continue service, please add minutes.",
            "remaining_minutes": 0,
        }, status=400)

    attempt_id = result.get("attempt_id") if isinstance(result, dict) else None

    rec = SarvamCallRecord.objects.create(
        sarvam_agent=sarvam_agent,
        attempt_id=attempt_id,
        phone_number=str(phone_number),
        candidate_name=candidate_name,
        language=language,
        status="DIALING",
        applied_position="Admission Counselor",
    )
    agent_label = sarvam_agent.name if sarvam_agent else "default"
    print(f"✅ [SARVAM OUTBOUND TRIGGERED]: Agent='{agent_label}' | Record #{rec.id} for {phone_number} (Attempt: {attempt_id})")

    agent_phone = sarvam_agent.agent_phone if sarvam_agent else os.getenv("SARVAM_AGENT_PHONE_NUMBER", "+917971414121")

    return Response({
        "status": "success",
        "message": f"Outbound call triggered to {phone_number} from Agent line ({agent_phone})",
        "agent_phone_number": agent_phone,
        "agent": agent_label,
        "trigger_result": result
    }, status=200)


@csrf_exempt
@api_view(["POST"])
def sarvam_sync_from_api(request, agent_slug=None):
    """
    Syncs ALL call data from Sarvam AI Analytics API into the local dashboard.
    POST /api/sarvam/<slug>/leads/sync/ or /api/sarvam/leads/sync/
    Optional body: {"days": 30, "agent_slug": "raahi-iiiem"}
    """
    try:
        from conversations.models import SarvamAgent
        days = int((request.data or {}).get("days", 30))
        days = max(1, min(days, 90))

        # Resolve agent
        slug = agent_slug or (request.data or {}).get("agent_slug")
        sarvam_agent = None
        if slug:
            sarvam_agent = SarvamAgent.objects.filter(slug=slug, is_active=True).first()
        if not sarvam_agent:
            sarvam_agent = SarvamAgent.objects.filter(is_active=True).first()

        from conversations.services.kylas_sarvam_bridge import SarvamAgentService
        agent_label = sarvam_agent.name if sarvam_agent else "default"
        print(f"\n🔄 [SARVAM SYNC API] Syncing last {days} days for agent '{agent_label}'...")
        result = SarvamAgentService.sync_all_interactions(days=days, sarvam_agent=sarvam_agent)
        print(f"✅ [SARVAM SYNC API DONE]: {result}")
        return Response({
            "status": "success",
            "message": f"Sync complete for last {days} days (agent: {agent_label})",
            **result
        }, status=200)
    except Exception as e:
        print(f"❌ [SARVAM SYNC API ERROR]: {e}")
        return Response({"status": "error", "message": str(e)}, status=500)


@api_view(["GET"])
def sarvam_user_agents_api(request):
    """
    Returns the list of Sarvam AI agents accessible by the current authenticated user.
    If ?all=true or user is admin/superuser, returns all Sarvam agents (including inactive).
    If the user has specifically assigned Sarvam agents in UserProfile, returns those.
    """
    from conversations.models import SarvamAgent
    
    user = request.user if request.user.is_authenticated else None
    assigned = []
    
    is_admin = False
    if user:
        if user.is_superuser:
            is_admin = True
        elif hasattr(user, 'profile') and user.profile and user.profile.role:
            perms = user.profile.role.permissions
            if perms.get('is_admin', False):
                is_admin = True
        if hasattr(user, 'profile') and user.profile and user.profile.custom_permissions:
            if user.profile.custom_permissions.get('is_admin', False):
                is_admin = True

    fetch_all = (request.GET.get("all") in ["true", "1"]) and is_admin
    
    if not fetch_all and user and not is_admin and hasattr(user, 'profile') and user.profile:
        assigned_qs = user.profile.assigned_sarvam_agents.filter(is_active=True).order_by("name")
        if assigned_qs.exists():
            for a in assigned_qs:
                assigned.append({
                    "id": a.id,
                    "name": a.name,
                    "slug": a.slug,
                    "agent_phone": a.agent_phone,
                    "description": a.description or "Outbound Calling & Screening",
                    "allocated_minutes": a.allocated_minutes,
                    "used_minutes": a.total_used_minutes,
                    "remaining_minutes": a.remaining_minutes,
                    "is_exhausted": a.is_minutes_exhausted,
                    "is_active": a.is_active,
                    "type": "sarvam",
                })
            return Response({
                "status": "success",
                "total": len(assigned),
                "agents": assigned
            }, status=200)

    # For admin or unrestricted requests
    if request.GET.get("all") in ["true", "1"] or is_admin:
        all_agents = SarvamAgent.objects.all().order_by("name")
    else:
        all_agents = SarvamAgent.objects.filter(is_active=True).order_by("name")
        
    for a in all_agents:
        assigned.append({
            "id": a.id,
            "name": a.name,
            "slug": a.slug,
            "agent_phone": a.agent_phone,
            "description": a.description or "Outbound Calling & Screening",
            "allocated_minutes": a.allocated_minutes,
            "used_minutes": a.total_used_minutes,
            "remaining_minutes": a.remaining_minutes,
            "is_exhausted": a.is_minutes_exhausted,
            "is_active": a.is_active,
            "type": "sarvam",
        })
        
    return Response({
        "status": "success",
        "total": len(assigned),
        "agents": assigned
    }, status=200)


def _sync_lead_call_outcome(lead, stage_num, sarvam_agent):
    """
    Accurately evaluates whether a lead's call attempt was ANSWERED or MISSED.
    1. Checks local SarvamCallRecord (updated in real-time by webhook).
    2. If still pending, queries remote Sarvam Analytics API with STRICT attempt_id match.
    3. If matching by proximity, enforces that:
       - The interaction started AFTER call_rec.created_at - 20s.
       - The interaction is NOT already attached to another SarvamCallRecord.
    4. Categorizes calls as ANSWERED only if duration >= 3s and not in MISSED statuses.
    Returns True for Answered/Picked Up, False for Missed.
    """
    from datetime import datetime, timezone as dt_tz, timedelta
    from conversations.services.kylas_sarvam_bridge import SarvamAgentService
    from conversations.models import SarvamCallRecord

    call_rec = None
    if stage_num == 1:
        call_rec = lead.stage_1_call
    elif stage_num == 2:
        call_rec = lead.stage_2_call
    elif stage_num == 3:
        call_rec = lead.stage_3_call

    if not call_rec:
        return False

    call_rec.refresh_from_db()
    status_upper = str(call_rec.status or "").upper()

    MISSED_STATUSES = {
        "NO_ANSWER", "BUSY", "FAILED", "UNREACHABLE", "CANCELLED", "MISSED",
        "QUEUED", "DIALING", "UNANSWERED", "REJECTED", "NOT_ANSWERED", "TIMEOUT", "IN_PROGRESS", "PENDING"
    }

    # If call record has valid completed duration >= 3 seconds and is not in missed status -> Answered
    if call_rec.duration_seconds >= 3.0 and status_upper not in MISSED_STATUSES:
        return True

    # Try matching with remote Sarvam Analytics API with strict checks
    try:
        res = SarvamAgentService.list_interactions(sarvam_agent=sarvam_agent)
        remote_items = res.get("items", []) if isinstance(res, dict) else []
        clean_rec_p = "".join(filter(str.isdigit, str(call_rec.phone_number)))[-10:]

        matched_item = None
        for item in remote_items:
            ijob = item.get("job_id") or item.get("jobId") or item.get("attempt_id") or item.get("attemptId")
            
            # Rule 1: Exact attempt_id match (preferred)
            if call_rec.attempt_id and ijob and str(ijob).strip() == str(call_rec.attempt_id).strip():
                matched_item = item
                break

        # Rule 2: Strict Proximity fallback ONLY if attempt_id didn't match
        if not matched_item and clean_rec_p:
            for item in remote_items:
                item_iid = item.get("interaction_id") or item.get("id")
                # Do NOT match an interaction that is already linked to another CallRecord
                if item_iid and SarvamCallRecord.objects.filter(interaction_id=item_iid).exclude(id=call_rec.id).exists():
                    continue

                icontact = item.get("user_contact") or item.get("user_phone_number") or item.get("phone_number") or ""
                clean_item_p = "".join(filter(str.isdigit, str(icontact)))[-10:]
                if clean_rec_p == clean_item_p:
                    item_start = item.get("start_datetime") or item.get("attempted_at")
                    if item_start:
                        try:
                            from django.utils.dateparse import parse_datetime
                            dt_val = parse_datetime(str(item_start))
                            if dt_val:
                                rec_created_naive = call_rec.created_at.replace(tzinfo=None)
                                item_start_naive = dt_val.replace(tzinfo=None)
                                sec_diff = (item_start_naive - rec_created_naive).total_seconds()
                                if -20 <= sec_diff <= 300:
                                    matched_item = item
                                    break
                        except Exception:
                            pass

        if matched_item:
            dur = float(matched_item.get("duration_in_seconds", 0))
            call_rec.duration_seconds = dur
            call_rec.interaction_id = matched_item.get("interaction_id") or call_rec.interaction_id
            call_rec.audio_url = matched_item.get("audio_url") or call_rec.audio_url
            agent_vars = matched_item.get("agent_variables", {}) or {}
            call_sum = agent_vars.get("call_summary") or {}
            
            remote_status = str(matched_item.get("status") or (call_sum.get("final_status") if isinstance(call_sum, dict) else "") or "").upper()
            if remote_status and remote_status not in ["DIALING", "IN_PROGRESS", "PENDING"]:
                call_rec.status = remote_status
            elif dur >= 3.0:
                call_rec.status = "COMPLETED"
            else:
                call_rec.status = "NO_ANSWER"
                
            if isinstance(call_sum, dict) and call_sum:
                call_rec.summary = call_sum
            call_rec.save()
    except Exception as e:
        print(f"⚠️ [SARVAM OUTCOME SYNC WARNING]: {e}")

    # Re-evaluate
    call_rec.refresh_from_db()
    status_upper = str(call_rec.status or "").upper()
    if call_rec.duration_seconds >= 3.0 and status_upper not in MISSED_STATUSES:
        return True

    # Mark as NO_ANSWER if still unsettled or 0s duration
    if call_rec.status in ["DIALING", "PENDING", "IN_PROGRESS", ""]:
        call_rec.status = "NO_ANSWER"
        if call_rec.duration_seconds < 3.0:
            call_rec.duration_seconds = 0.0
        call_rec.save(update_fields=["status", "duration_seconds"])

    return False


def _run_multi_stage_campaign(campaign_id):
    """
    Background worker orchestrating the 3-Stage Campaign Lifecycle:
      - Stage 1: Dispatches Main Batch (all candidate leads).
      - Settle & Sync: Identifies leads that were missed/unanswered.
      - Stage 2: Dispatches Auto-Retry #1 for missed leads only.
      - Settle & Sync: Identifies still-missed leads.
      - Stage 3: Dispatches Auto-Retry #2 (Final Retry) for still-missed leads.
      - Settle & Sync: Marks final outcomes (Answered vs Missed All 3 Retries).
      - Sets campaign status to COMPLETED.
    """
    import time
    from conversations.models import SarvamCampaign, SarvamCampaignLead, SarvamCallRecord
    from conversations.services.kylas_sarvam_bridge import SarvamAgentService

    MISSED_STATUSES = {
        "NO_ANSWER", "BUSY", "FAILED", "UNREACHABLE", "CANCELLED", "MISSED",
        "QUEUED", "DIALING", "UNANSWERED", "REJECTED", "NOT_ANSWERED", "TIMEOUT", "IN_PROGRESS", "PENDING"
    }

    try:
        campaign = SarvamCampaign.objects.get(id=campaign_id)
    except SarvamCampaign.DoesNotExist:
        print(f"❌ [CAMPAIGN WORKER]: Campaign #{campaign_id} not found.")
        return

    agent = campaign.sarvam_agent
    delay = max(2, min(campaign.delay_seconds if campaign.delay_seconds else 10, 60))
    agent_label = agent.name if agent else "default"

    print(f"\n🚀 [CAMPAIGN #{campaign.id} STARTED]: '{campaign.name}' | Total Leads: {campaign.total_leads} | Agent: {agent_label}")

    def _poll_stage_settlement(stage_leads, stage_num):
        """Polls until calls finish ringing or webhooks arrive (up to max timeout)."""
        max_wait = min(45, max(15, len(stage_leads) * 4))
        elapsed = 0
        poll_interval = 3
        print(f"⏳ [STAGE {stage_num} SETTLING]: Polling for call completions (max {max_wait}s)...")
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            all_done = True
            for lead in stage_leads:
                rec = getattr(lead, f"stage_{stage_num}_call", None)
                if rec:
                    rec.refresh_from_db()
                    if rec.status in ["DIALING", "PENDING", "IN_PROGRESS"]:
                        all_done = False
                        break
            if all_done and elapsed >= 6:
                print(f"✅ [STAGE {stage_num} SETTLED]: All {len(stage_leads)} calls completed after {elapsed}s.")
                break

    def _wait_stage_cooldown(wait_seconds=300, next_stage_name="Retry #1", waiting_status=None):
        """Waits for cooldown (5 min) while remaining responsive to campaign cancellation."""
        if waiting_status:
            campaign.status = waiting_status
            campaign.save(update_fields=["status"])
        print(f"\n⏳ [CAMPAIGN #{campaign.id} COOLDOWN]: Waiting 5 minutes ({wait_seconds}s) before starting {next_stage_name}...")
        elapsed = 0
        poll_sec = 2
        while elapsed < wait_seconds:
            time.sleep(poll_sec)
            elapsed += poll_sec
            campaign.refresh_from_db()
            if campaign.status == "CANCELLED":
                print(f"🛑 [CAMPAIGN #{campaign.id}]: Cancelled by user during 5-minute cooldown before {next_stage_name}.")
                return False
            if elapsed % 30 == 0 or elapsed == wait_seconds:
                remaining = max(0, wait_seconds - elapsed)
                print(f"⏳ [CAMPAIGN #{campaign.id}]: {remaining}s remaining in 5-minute cooldown before {next_stage_name} starts...")
        return True

    # ==========================================
    # STAGE 1: MAIN CAMPAIGN
    # ==========================================
    campaign.status = "RUNNING_MAIN"
    campaign.current_stage = 1
    campaign.save(update_fields=["status", "current_stage"])

    all_leads = list(campaign.leads.all().order_by("id"))
    print(f"📞 [STAGE 1 - MAIN]: Dispatching {len(all_leads)} calls (Delay: {delay}s)...")

    for lead in all_leads:
        campaign.refresh_from_db()
        if campaign.status == "CANCELLED":
            print(f"🛑 [CAMPAIGN #{campaign.id}]: Cancelled by user during Stage 1.")
            return

        if agent and getattr(agent, "is_minutes_exhausted", False):
            print(f"🛑 [CAMPAIGN #{campaign.id}]: Halted because agent '{agent.name}' call minutes limit is exhausted.")
            campaign.status = "CANCELLED"
            campaign.save(update_fields=["status"])
            return

        try:
            call_rec = SarvamCallRecord.objects.create(
                sarvam_agent=agent,
                campaign=campaign,
                campaign_stage=1,
                phone_number=lead.phone_number,
                candidate_name=lead.candidate_name,
                applied_position=lead.applied_position,
                status="DIALING",
                call_type=f"Campaign #{campaign.id}: Main (Stage 1)",
                summary=dict(lead.extra_data) if lead.extra_data else {}
            )
            lead.stage_1_call = call_rec
            lead.last_call_record = call_rec
            lead.total_attempts = 1
            lead.stage_1_status = "PENDING"
            lead.save()

            extra_vars_combined = {}
            if hasattr(lead, "extra_variables") and isinstance(lead.extra_variables, dict):
                extra_vars_combined.update(lead.extra_variables)
            if hasattr(lead, "extra_data") and isinstance(lead.extra_data, dict):
                extra_vars_combined.update(lead.extra_data)

            res = SarvamAgentService.trigger_outbound_call(
                phone_number=lead.phone_number,
                lead_id=0,
                customer_name=lead.candidate_name,
                language=getattr(lead, "language", "hi-IN"),
                extra_variables=extra_vars_combined,
                sarvam_agent=agent,
            )
            attempt_id = res.get("attempt_id") if isinstance(res, dict) else None
            if attempt_id:
                call_rec.attempt_id = attempt_id
                call_rec.save(update_fields=["attempt_id"])
                print(f"  ✅ [STAGE 1 CALL]: #{call_rec.id} -> {lead.phone_number} ({lead.candidate_name}) | Attempt: {attempt_id}")
            else:
                print(f"  ⚠️ [STAGE 1 CALL WARN]: {lead.phone_number} -> {res}")
        except Exception as ex:
            print(f"  ❌ [STAGE 1 ERROR]: {lead.phone_number} -> {ex}")

        time.sleep(delay)

    # Allow Stage 1 calls to finish and sync
    _poll_stage_settlement(all_leads, 1)

    s1_answered = 0
    s1_missed = 0
    for lead in all_leads:
        answered = _sync_lead_call_outcome(lead, 1, agent)
        if answered:
            lead.stage_1_status = "ANSWERED"
            lead.stage_2_status = "SKIPPED"
            lead.stage_3_status = "SKIPPED"
            lead.final_status = "ANSWERED"
            s1_answered += 1
        else:
            lead.stage_1_status = "MISSED"
            lead.final_status = "IN_PROGRESS"
            s1_missed += 1
        lead.save()

    campaign.stage_1_dispatched = len(all_leads)
    campaign.stage_1_answered = s1_answered
    campaign.stage_1_missed = s1_missed
    campaign.answered_count = s1_answered
    campaign.missed_count = s1_missed
    campaign.save()
    print(f"📊 [STAGE 1 RESULTS]: Answered: {s1_answered} | Missed: {s1_missed}")

    # ==========================================
    # STAGE 2: RETRY #1 (For Missed Calls)
    # ==========================================
    missed_s1_leads = list(campaign.leads.filter(stage_1_status="MISSED").order_by("id"))
    if not missed_s1_leads:
        print(f"🎉 [CAMPAIGN #{campaign.id} COMPLETED]: All leads answered in Stage 1!")
        campaign.status = "COMPLETED"
        campaign.current_stage = 4
        campaign.save()
        return

    # Cooldown 5 minutes before Stage 2
    if not _wait_stage_cooldown(wait_seconds=300, next_stage_name="Stage 2 (Retry #1)", waiting_status="WAITING_RETRY_1"):
        return

    # Re-sync and verify Stage 1 outcomes after cooldown (in case webhooks or calls finished during 5-minute cooldown)
    print(f"\n🔍 [STAGE 2 PRE-CHECK]: Re-evaluating Stage 1 outcomes after 5-minute cooldown...")
    for lead in all_leads:
        lead.refresh_from_db()
        if lead.stage_1_status != "ANSWERED":
            if lead.stage_1_call:
                lead.stage_1_call.refresh_from_db()
                if lead.stage_1_call.duration_seconds >= 3.0 and str(lead.stage_1_call.status).upper() not in MISSED_STATUSES:
                    lead.stage_1_status = "ANSWERED"
                    lead.stage_2_status = "SKIPPED"
                    lead.stage_3_status = "SKIPPED"
                    lead.final_status = "ANSWERED"
                    lead.save()
                    print(f"  ✅ [STAGE 1 RE-SYNC]: Lead {lead.phone_number} ({lead.candidate_name}) answered ({lead.stage_1_call.duration_seconds:.1f}s) during cooldown!")
                else:
                    if _sync_lead_call_outcome(lead, 1, agent):
                        lead.stage_1_status = "ANSWERED"
                        lead.stage_2_status = "SKIPPED"
                        lead.stage_3_status = "SKIPPED"
                        lead.final_status = "ANSWERED"
                        lead.save()
                        print(f"  ✅ [STAGE 1 RE-SYNC]: Lead {lead.phone_number} ({lead.candidate_name}) verified as ANSWERED.")

    campaign.stage_1_answered = campaign.leads.filter(stage_1_status="ANSWERED").count()
    campaign.stage_1_missed = campaign.leads.filter(stage_1_status="MISSED").count()
    campaign.answered_count = campaign.leads.filter(final_status="ANSWERED").count()
    campaign.missed_count = campaign.leads.filter(stage_1_status="MISSED").count()
    campaign.save()

    missed_s1_leads = list(campaign.leads.filter(stage_1_status="MISSED").order_by("id"))
    if not missed_s1_leads:
        print(f"🎉 [CAMPAIGN #{campaign.id} COMPLETED]: All leads answered after Stage 1!")
        campaign.status = "COMPLETED"
        campaign.current_stage = 4
        campaign.save()
        return

    campaign.status = "RUNNING_RETRY_1"
    campaign.current_stage = 2
    campaign.save(update_fields=["status", "current_stage"])
    print(f"\n🔄 [STAGE 2 - RETRY #1]: Retrying {len(missed_s1_leads)} missed numbers (Delay: {delay}s)...")

    for lead in missed_s1_leads:
        campaign.refresh_from_db()
        if campaign.status == "CANCELLED":
            print(f"🛑 [CAMPAIGN #{campaign.id}]: Cancelled during Stage 2.")
            return

        if agent and getattr(agent, "is_minutes_exhausted", False):
            print(f"🛑 [CAMPAIGN #{campaign.id}]: Halted because agent '{agent.name}' call minutes limit is exhausted.")
            campaign.status = "CANCELLED"
            campaign.save(update_fields=["status"])
            return

        try:
            call_rec = SarvamCallRecord.objects.create(
                sarvam_agent=agent,
                campaign=campaign,
                campaign_stage=2,
                phone_number=lead.phone_number,
                candidate_name=lead.candidate_name,
                applied_position=lead.applied_position,
                status="DIALING",
                call_type=f"Campaign #{campaign.id}: Retry #1 (Stage 2)",
                summary=dict(lead.extra_data) if lead.extra_data else {}
            )
            lead.stage_2_call = call_rec
            lead.last_call_record = call_rec
            lead.total_attempts = 2
            lead.stage_2_status = "PENDING"
            lead.save()

            extra_vars_combined = {}
            if hasattr(lead, "extra_variables") and isinstance(lead.extra_variables, dict):
                extra_vars_combined.update(lead.extra_variables)
            if hasattr(lead, "extra_data") and isinstance(lead.extra_data, dict):
                extra_vars_combined.update(lead.extra_data)

            res = SarvamAgentService.trigger_outbound_call(
                phone_number=lead.phone_number,
                lead_id=0,
                customer_name=lead.candidate_name,
                language=getattr(lead, "language", "hi-IN"),
                extra_variables=extra_vars_combined,
                sarvam_agent=agent,
            )
            attempt_id = res.get("attempt_id") if isinstance(res, dict) else None
            if attempt_id:
                call_rec.attempt_id = attempt_id
                call_rec.save(update_fields=["attempt_id"])
                print(f"  ✅ [STAGE 2 CALL]: #{call_rec.id} -> {lead.phone_number} ({lead.candidate_name}) | Attempt: {attempt_id}")
        except Exception as ex:
            print(f"  ❌ [STAGE 2 ERROR]: {lead.phone_number} -> {ex}")

        time.sleep(delay)

    _poll_stage_settlement(missed_s1_leads, 2)

    s2_answered = 0
    s2_missed = 0
    for lead in missed_s1_leads:
        answered = _sync_lead_call_outcome(lead, 2, agent)
        if answered:
            lead.stage_2_status = "ANSWERED"
            lead.stage_3_status = "SKIPPED"
            lead.final_status = "ANSWERED"
            s2_answered += 1
        else:
            lead.stage_2_status = "MISSED"
            lead.final_status = "IN_PROGRESS"
            s2_missed += 1
        lead.save()

    campaign.stage_2_dispatched = len(missed_s1_leads)
    campaign.stage_2_answered = s2_answered
    campaign.stage_2_missed = s2_missed
    campaign.answered_count = campaign.leads.filter(final_status="ANSWERED").count()
    campaign.missed_count = s2_missed
    campaign.save()
    print(f"📊 [STAGE 2 RESULTS]: Answered: {s2_answered} | Missed: {s2_missed}")

    # ==========================================
    # STAGE 3: RETRY #2 (Final Retry)
    # ==========================================
    missed_s2_leads = list(campaign.leads.filter(stage_2_status="MISSED").order_by("id"))
    if not missed_s2_leads:
        print(f"🎉 [CAMPAIGN #{campaign.id} COMPLETED]: All remaining leads answered in Stage 2!")
        campaign.status = "COMPLETED"
        campaign.current_stage = 4
        campaign.save()
        return

    # Cooldown 5 minutes before Stage 3
    if not _wait_stage_cooldown(wait_seconds=300, next_stage_name="Stage 3 (Final Retry #2)", waiting_status="WAITING_RETRY_2"):
        return

    # Re-sync and verify Stage 2 outcomes after cooldown
    print(f"\n🔍 [STAGE 3 PRE-CHECK]: Re-evaluating Stage 2 outcomes after 5-minute cooldown...")
    for lead in missed_s1_leads:
        lead.refresh_from_db()
        if lead.stage_2_status != "ANSWERED":
            if lead.stage_2_call:
                lead.stage_2_call.refresh_from_db()
                if lead.stage_2_call.duration_seconds >= 3.0 and str(lead.stage_2_call.status).upper() not in MISSED_STATUSES:
                    lead.stage_2_status = "ANSWERED"
                    lead.stage_3_status = "SKIPPED"
                    lead.final_status = "ANSWERED"
                    lead.save()
                    print(f"  ✅ [STAGE 2 RE-SYNC]: Lead {lead.phone_number} ({lead.candidate_name}) answered ({lead.stage_2_call.duration_seconds:.1f}s) during cooldown!")
                else:
                    if _sync_lead_call_outcome(lead, 2, agent):
                        lead.stage_2_status = "ANSWERED"
                        lead.stage_3_status = "SKIPPED"
                        lead.final_status = "ANSWERED"
                        lead.save()
                        print(f"  ✅ [STAGE 2 RE-SYNC]: Lead {lead.phone_number} ({lead.candidate_name}) verified as ANSWERED.")

    campaign.stage_2_answered = campaign.leads.filter(stage_2_status="ANSWERED").count()
    campaign.stage_2_missed = campaign.leads.filter(stage_2_status="MISSED").count()
    campaign.answered_count = campaign.leads.filter(final_status="ANSWERED").count()
    campaign.missed_count = campaign.leads.filter(stage_2_status="MISSED").count()
    campaign.save()

    missed_s2_leads = list(campaign.leads.filter(stage_2_status="MISSED").order_by("id"))
    if not missed_s2_leads:
        print(f"🎉 [CAMPAIGN #{campaign.id} COMPLETED]: All remaining leads answered after Stage 2!")
        campaign.status = "COMPLETED"
        campaign.current_stage = 4
        campaign.save()
        return

    campaign.status = "RUNNING_RETRY_2"
    campaign.current_stage = 3
    campaign.save(update_fields=["status", "current_stage"])
    print(f"\n🔄 [STAGE 3 - RETRY #2 FINAL]: Retrying {len(missed_s2_leads)} remaining missed numbers (Delay: {delay}s)...")

    for lead in missed_s2_leads:
        campaign.refresh_from_db()
        if campaign.status == "CANCELLED":
            print(f"🛑 [CAMPAIGN #{campaign.id}]: Cancelled during Stage 3.")
            return

        if agent and getattr(agent, "is_minutes_exhausted", False):
            print(f"🛑 [CAMPAIGN #{campaign.id}]: Halted because agent '{agent.name}' call minutes limit is exhausted.")
            campaign.status = "CANCELLED"
            campaign.save(update_fields=["status"])
            return

        try:
            call_rec = SarvamCallRecord.objects.create(
                sarvam_agent=agent,
                campaign=campaign,
                campaign_stage=3,
                phone_number=lead.phone_number,
                candidate_name=lead.candidate_name,
                applied_position=lead.applied_position,
                status="DIALING",
                call_type=f"Campaign #{campaign.id}: Final Retry #2 (Stage 3)",
                summary=dict(lead.extra_data) if lead.extra_data else {}
            )
            lead.stage_3_call = call_rec
            lead.last_call_record = call_rec
            lead.total_attempts = 3
            lead.stage_3_status = "PENDING"
            lead.save()

            extra_vars_combined = {}
            if hasattr(lead, "extra_variables") and isinstance(lead.extra_variables, dict):
                extra_vars_combined.update(lead.extra_variables)
            if hasattr(lead, "extra_data") and isinstance(lead.extra_data, dict):
                extra_vars_combined.update(lead.extra_data)

            res = SarvamAgentService.trigger_outbound_call(
                phone_number=lead.phone_number,
                lead_id=0,
                customer_name=lead.candidate_name,
                language=getattr(lead, "language", "hi-IN"),
                extra_variables=extra_vars_combined,
                sarvam_agent=agent,
            )
            attempt_id = res.get("attempt_id") if isinstance(res, dict) else None
            if attempt_id:
                call_rec.attempt_id = attempt_id
                call_rec.save(update_fields=["attempt_id"])
                print(f"  ✅ [STAGE 3 CALL]: #{call_rec.id} -> {lead.phone_number} ({lead.candidate_name}) | Attempt: {attempt_id}")
        except Exception as ex:
            print(f"  ❌ [STAGE 3 ERROR]: {lead.phone_number} -> {ex}")

        time.sleep(delay)

    _poll_stage_settlement(missed_s2_leads, 3)

    s3_answered = 0
    s3_missed = 0
    for lead in missed_s2_leads:
        answered = _sync_lead_call_outcome(lead, 3, agent)
        if answered:
            lead.stage_3_status = "ANSWERED"
            lead.final_status = "ANSWERED"
            s3_answered += 1
        else:
            lead.stage_3_status = "MISSED"
            lead.final_status = "MISSED_ALL_RETRIES"
            s3_missed += 1
        lead.save()

    campaign.stage_3_dispatched = len(missed_s2_leads)
    campaign.stage_3_answered = s3_answered
    campaign.stage_3_missed = s3_missed
    campaign.answered_count = campaign.leads.filter(final_status="ANSWERED").count()
    campaign.missed_count = campaign.leads.filter(final_status="MISSED_ALL_RETRIES").count()
    campaign.status = "COMPLETED"
    campaign.current_stage = 4
    campaign.save()

    print(f"\n🏁 [CAMPAIGN #{campaign.id} FULLY COMPLETED]:")
    print(f"   Total Leads: {campaign.total_leads}")
    print(f"   Total Answered Across All 3 Stages: {campaign.answered_count}")
    print(f"   Total Missed After All 3 Retries: {campaign.missed_count}")


@csrf_exempt
@api_view(["POST"])
def sarvam_upload_campaign_api(request, agent_slug=None):
    """
    Uploads an Excel or CSV file containing candidate records and launches a 3-Stage
    multi-retry campaign with live tracking and automated follow-up.
    POST /api/sarvam/<slug>/leads/upload-campaign/ or /api/sarvam/leads/upload-campaign/
    """
    import threading
    import pandas as pd
    from datetime import datetime
    from conversations.models import SarvamAgent, SarvamCampaign, SarvamCampaignLead

    # Resolve agent
    slug = agent_slug or request.data.get("agent_slug")
    user = request.user if request.user.is_authenticated else None
    is_admin = False
    if user:
        if user.is_superuser:
            is_admin = True
        elif hasattr(user, 'profile') and user.profile and user.profile.role:
            perms = user.profile.role.permissions
            if perms.get('is_admin', False):
                is_admin = True
        if hasattr(user, 'profile') and user.profile and user.profile.custom_permissions:
            if user.profile.custom_permissions.get('is_admin', False):
                is_admin = True

    sarvam_agent = None
    if user and not is_admin and hasattr(user, 'profile') and user.profile:
        assigned_qs = user.profile.assigned_sarvam_agents.filter(is_active=True)
        if assigned_qs.exists():
            if slug and assigned_qs.filter(slug=slug).exists():
                sarvam_agent = assigned_qs.filter(slug=slug).first()
            else:
                sarvam_agent = assigned_qs.first()

    if not sarvam_agent:
        if slug:
            sarvam_agent = SarvamAgent.objects.filter(slug=slug, is_active=True).first()
        if not sarvam_agent:
            sarvam_agent = SarvamAgent.objects.filter(is_active=True).first()

    if sarvam_agent and getattr(sarvam_agent, "is_minutes_exhausted", False):
        return Response({
            "status": "error",
            "code": "MINUTES_EXHAUSTED",
            "error": f"Campaign cannot be started: Call minutes limit ({sarvam_agent.allocated_minutes}m) is exhausted for '{sarvam_agent.name}'. To continue service, please add minutes.",
            "message": f"Campaign cannot be started: Call minutes limit ({sarvam_agent.allocated_minutes}m) is exhausted for '{sarvam_agent.name}'. To continue service, please add minutes.",
            "remaining_minutes": 0,
        }, status=400)

    if "file" not in request.FILES and "excel_file" not in request.FILES:
        return Response({"error": "No file uploaded. Please select an Excel or CSV file."}, status=400)

    file_obj = request.FILES.get("file") or request.FILES.get("excel_file")
    campaign_name = request.data.get("campaign_name") or f"Campaign {datetime.now().strftime('%d %b %Y %H:%M')}"
    raw_delay = request.data.get("delay_sec")
    try:
        delay_sec = int(raw_delay) if raw_delay is not None and str(raw_delay).strip() != "" else 10
    except (ValueError, TypeError):
        delay_sec = 10
    delay_sec = max(2, min(delay_sec, 60))

    file_name = file_obj.name.lower()
    try:
        if file_name.endswith(".csv"):
            df = pd.read_csv(file_obj)
        elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
            df = pd.read_excel(file_obj)
        else:
            return Response({"error": "Unsupported file format. Please upload a .xlsx, .xls, or .csv file."}, status=400)
    except Exception as e:
        return Response({"error": f"Failed to parse spreadsheet: {str(e)}"}, status=400)

    if df.empty:
        return Response({"error": "Uploaded file contains no rows."}, status=400)

    # Flexible column header mapping (matches only Phone and Name)
    cols = {str(c).strip().lower(): c for c in df.columns}

    phone_col = None
    for p_key in ["phone", "phone number", "phone_number", "contact", "mobile", "number", "mobile_number", "contact_number"]:
        if p_key in cols:
            phone_col = cols[p_key]
            break

    if not phone_col:
        return Response({"error": "Could not find a valid Phone Number column. Headers found: " + ", ".join(list(df.columns))}, status=400)

    name_col = None
    for n_key in [
        "user_name", "user name", "username", "customer_name", "customer name", 
        "customer", "client_name", "client name", "client", "person_name", 
        "person name", "person", "name", "candidate name", "candidate_name", 
        "full name", "full_name", "first_name", "first name", "lead_name", "lead name"
    ]:
        if n_key in cols:
            name_col = cols[n_key]
            break

    if not name_col:
        for key in cols:
            if "name" in key or "user" in key or "customer" in key or "client" in key:
                name_col = cols[key]
                break

    # Find Position Column
    pos_col = None
    for r_key in ["position", "applied position", "applied_position", "role", "job"]:
        if r_key in cols:
            pos_col = cols[r_key]
            break

    # Find Language Column
    lang_col = None
    for l_key in ["language", "lang", "preferred_language"]:
        if l_key in cols:
            lang_col = cols[l_key]
            break
    parsed_records = []
    for idx, row in df.iterrows():
        raw_phone = str(row.get(phone_col, "") or "").strip()
        if not raw_phone or raw_phone.lower() in ["nan", "none", "null"]:
            continue

        if raw_phone.endswith(".0"):
            raw_phone = raw_phone[:-2]
        digits = "".join(filter(str.isdigit, raw_phone))
        if len(digits) < 10:
            continue

        c_name = str(row.get(name_col, "Candidate") if name_col else "Candidate").strip()
        if not c_name or c_name.lower() in ["nan", "none", "null"]:
            c_name = f"Candidate #{idx+1}"

        # Dynamically capture all additional columns (e.g. model, car_model, vehicle, city, area, budget, etc.)
        extra_vars = {}
        for orig_col in df.columns:
            if orig_col not in [phone_col, name_col]:
                val = row.get(orig_col)
                if val is not None and not pd.isna(val):
                    val_str = str(val).strip()
                    if val_str and val_str.lower() not in ["nan", "none", "null"]:
                        norm_key = str(orig_col).strip().lower().replace(" ", "_")
                        extra_vars[norm_key] = val_str
                        extra_vars[str(orig_col).strip()] = val_str

        # If a model or product column is detected, use it as applied_position / product interest
        model_name = (
            extra_vars.get("car_model")
            or extra_vars.get("model")
            or extra_vars.get("vehicle")
            or extra_vars.get("product")
            or extra_vars.get("product_interest")
            or extra_vars.get("product_name")
        )

        if model_name:
            c_pos = model_name
        else:
            pos_candidate = (
                extra_vars.get("applied_position")
                or extra_vars.get("position")
                or extra_vars.get("role")
                or extra_vars.get("job")
                or extra_vars.get("designation")
            )
            if pos_candidate:
                c_pos = pos_candidate
            else:
                c_pos = "Samsung Product Inquiry" if (sarvam_agent and "vtech" in sarvam_agent.slug) else "Admission Counselor"

        c_lang = str(row.get(lang_col, "hi-IN") if lang_col else "hi-IN").strip()
        if not c_lang or c_lang.lower() in ["nan", "none", "null"]:
            c_lang = "hi-IN"

        # Capture all extra columns (car_model, car_name, model, city, product, etc.)
        extra_vars = {}
        for col_name in df.columns:
            clean_k = str(col_name).strip().lower().replace(" ", "_")
            if clean_k not in ["phone", "phone_number", "phone number", "contact", "mobile", "number"]:
                val_str = str(row[col_name]).strip()
                if val_str and val_str.lower() not in ["nan", "none", "null"]:
                    extra_vars[clean_k] = val_str

        # Automotive alias helpers: map car_name or model to car_model automatically
        if "car_name" in extra_vars and "car_model" not in extra_vars:
            extra_vars["car_model"] = extra_vars["car_name"]
        elif "model" in extra_vars and "car_model" not in extra_vars:
            extra_vars["car_model"] = extra_vars["model"]
        elif "car" in extra_vars and "car_model" not in extra_vars:
            extra_vars["car_model"] = extra_vars["car"]

        parsed_records.append({
            "phone": digits,
            "name": c_name,
            "position": c_pos,
            "language": c_lang,
            "extra_vars": extra_vars,
            "extra_data": extra_vars,
        })

    if not parsed_records:
        return Response({"error": "No valid phone numbers found in the uploaded file."}, status=400)

    # Create SarvamCampaign in DB
    user = request.user if request.user.is_authenticated else None
    campaign = SarvamCampaign.objects.create(
        name=campaign_name,
        sarvam_agent=sarvam_agent,
        created_by=user,
        excel_file_name=file_obj.name,
        total_leads=len(parsed_records),
        delay_seconds=delay_sec,
        status="RUNNING_MAIN",
        current_stage=1,
    )

    # Bulk create leads with dynamic extra_data
    lead_objs = [
        SarvamCampaignLead(
            campaign=campaign,
            candidate_name=item["name"],
            phone_number=item["phone"],
            applied_position=item["position"],
            language=item.get("language", "hi-IN"),
            extra_variables=item.get("extra_vars", {}),
            extra_data=item.get("extra_data", {}),
            stage_1_status="PENDING",
            final_status="IN_PROGRESS",
        )
        for item in parsed_records
    ]
    SarvamCampaignLead.objects.bulk_create(lead_objs)

    # Spawn background thread to run 3 stages
    t = threading.Thread(target=_run_multi_stage_campaign, args=(campaign.id,), daemon=True)
    t.start()

    return Response({
        "status": "success",
        "message": f"3-Stage Campaign '{campaign_name}' launched with {len(parsed_records)} leads.",
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "total_leads": campaign.total_leads,
        "delay_sec": delay_sec,
        "agent": sarvam_agent.name if sarvam_agent else "default",
    }, status=200)


@api_view(["GET"])
def sarvam_campaigns_list_api(request, agent_slug=None):
    """
    Returns list of all Sarvam campaigns with their stage breakdown, progress, and metrics.
    GET /api/sarvam/campaigns/list/ or /api/sarvam/<slug>/campaigns/list/
    """
    from conversations.models import SarvamCampaign, SarvamAgent

    slug = agent_slug or request.GET.get("agent")
    user = request.user if request.user.is_authenticated else None
    is_admin = False
    if user:
        if user.is_superuser:
            is_admin = True
        elif hasattr(user, 'profile') and user.profile and user.profile.role:
            perms = user.profile.role.permissions
            if perms.get('is_admin', False):
                is_admin = True
        if hasattr(user, 'profile') and user.profile and user.profile.custom_permissions:
            if user.profile.custom_permissions.get('is_admin', False):
                is_admin = True

    sarvam_agent = None
    qs = SarvamCampaign.objects.all().order_by("-created_at")
    if user and not is_admin and hasattr(user, 'profile') and user.profile:
        assigned_qs = user.profile.assigned_sarvam_agents.filter(is_active=True)
        if assigned_qs.exists():
            if slug and assigned_qs.filter(slug=slug).exists():
                sarvam_agent = assigned_qs.filter(slug=slug).first()
                qs = qs.filter(sarvam_agent=sarvam_agent)
            else:
                qs = qs.filter(sarvam_agent__in=assigned_qs)
        else:
            if slug:
                sarvam_agent = SarvamAgent.objects.filter(slug=slug, is_active=True).first()
            if sarvam_agent:
                qs = qs.filter(sarvam_agent=sarvam_agent)
    else:
        if slug:
            sarvam_agent = SarvamAgent.objects.filter(slug=slug, is_active=True).first()
        if sarvam_agent:
            qs = qs.filter(sarvam_agent=sarvam_agent)

    campaigns_data = []
    for c in qs:
        # Compute live progress percent
        prog = 0
        if c.total_leads > 0:
            if c.status == "COMPLETED":
                prog = 100
            elif c.status == "WAITING_RETRY_1":
                prog = 33.3
            elif c.status == "WAITING_RETRY_2":
                prog = 66.6
            elif c.current_stage == 1:
                prog = round((c.stage_1_dispatched / c.total_leads) * 33, 1)
            elif c.current_stage == 2:
                s1_p = 33
                s2_p = (c.stage_2_dispatched / max(1, c.stage_1_missed)) * 33 if c.stage_1_missed > 0 else 33
                prog = round(s1_p + s2_p, 1)
            elif c.current_stage == 3:
                s1_p = 33
                s2_p = 33
                s3_p = (c.stage_3_dispatched / max(1, c.stage_2_missed)) * 34 if c.stage_2_missed > 0 else 34
                prog = round(s1_p + s2_p + s3_p, 1)

        campaigns_data.append({
            "id": c.id,
            "name": c.name,
            "agent_name": c.sarvam_agent.name if c.sarvam_agent else "Default Agent",
            "agent_slug": c.sarvam_agent.slug if c.sarvam_agent else "",
            "excel_file_name": c.excel_file_name,
            "total_leads": c.total_leads,
            "current_stage": c.current_stage,
            "status": c.status,
            "progress_pct": min(100, max(0, prog)),
            "answered_count": c.answered_count,
            "missed_count": c.missed_count,
            "stage_1": {
                "dispatched": c.stage_1_dispatched,
                "answered": c.stage_1_answered,
                "missed": c.stage_1_missed,
            },
            "stage_2": {
                "dispatched": c.stage_2_dispatched,
                "answered": c.stage_2_answered,
                "missed": c.stage_2_missed,
            },
            "stage_3": {
                "dispatched": c.stage_3_dispatched,
                "answered": c.stage_3_answered,
                "missed": c.stage_3_missed,
            },
            "created_at": c.created_at.strftime("%d %b %Y %H:%M"),
        })

    return Response({
        "status": "success",
        "total": len(campaigns_data),
        "campaigns": campaigns_data
    }, status=200)


@api_view(["GET"])
def sarvam_campaign_detail_api(request, campaign_id):
    """
    Returns full details of a single campaign including all leads with 3-stage attempt breakdown.
    GET /api/sarvam/campaigns/<id>/detail/
    """
    from conversations.models import SarvamCampaign

    campaign = SarvamCampaign.objects.filter(id=campaign_id).first()
    if not campaign:
        return Response({"error": "Campaign not found"}, status=404)

    leads_data = []
    for lead in campaign.leads.all().order_by("id"):
        s1_dur = round(lead.stage_1_call.duration_seconds, 1) if lead.stage_1_call else 0.0
        s2_dur = round(lead.stage_2_call.duration_seconds, 1) if lead.stage_2_call else 0.0
        s3_dur = round(lead.stage_3_call.duration_seconds, 1) if lead.stage_3_call else 0.0

        leads_data.append({
            "id": lead.id,
            "candidate_name": lead.candidate_name,
            "phone_number": lead.phone_number,
            "stage_1_status": lead.stage_1_status,
            "stage_1_duration": s1_dur,
            "stage_2_status": lead.stage_2_status,
            "stage_2_duration": s2_dur,
            "stage_3_status": lead.stage_3_status,
            "stage_3_duration": s3_dur,
            "final_status": lead.final_status,
            "total_attempts": lead.total_attempts,
            "last_call_time": lead.last_call_record.created_at.strftime("%d %b %Y %H:%M") if (lead.last_call_record and lead.last_call_record.created_at) else "",
        })

    return Response({
        "status": "success",
        "campaign": {
            "id": campaign.id,
            "name": campaign.name,
            "agent_name": campaign.sarvam_agent.name if campaign.sarvam_agent else "Default",
            "total_leads": campaign.total_leads,
            "current_stage": campaign.current_stage,
            "status": campaign.status,
            "answered_count": campaign.answered_count,
            "missed_count": campaign.missed_count,
            "created_at": campaign.created_at.strftime("%d %b %Y %H:%M"),
        },
        "total_leads": len(leads_data),
        "leads": leads_data
    }, status=200)


@api_view(["POST"])
def sarvam_campaign_cancel_api(request, campaign_id):
    """Cancels an active running campaign."""
    from conversations.models import SarvamCampaign
    campaign = SarvamCampaign.objects.filter(id=campaign_id).first()
    if not campaign:
        return Response({"error": "Campaign not found"}, status=404)

    campaign.status = "CANCELLED"
    campaign.save(update_fields=["status"])
    return Response({"status": "success", "message": f"Campaign #{campaign_id} cancelled."}, status=200)


@api_view(["GET"])
def sarvam_campaign_export_full_api(request, campaign_id):
    """
    Generates and downloads a comprehensive Excel file of the whole campaign,
    including every candidate lead and their status across all 3 stages.
    GET /api/sarvam/campaigns/<id>/export-full/
    """
    from conversations.models import SarvamCampaign
    from django.http import HttpResponse
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    campaign = SarvamCampaign.objects.filter(id=campaign_id).first()
    if not campaign:
        return Response({"error": "Campaign not found"}, status=404)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Full Campaign Report"

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    headers = [
        "S.No",
        "Candidate Name",
        "Phone Number",
        "Stage 1 (Main)",
        "Stage 1 Duration (s)",
        "Stage 2 (Retry 1)",
        "Stage 2 Duration (s)",
        "Stage 3 (Retry 2 - Final)",
        "Stage 3 Duration (s)",
        "Final Outcome",
        "Total Attempts",
        "Last Call Time",
    ]
    ws.append(headers)

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center
        cell.border = thin_border

    ws.row_dimensions[1].height = 28

    leads = campaign.leads.all().order_by("id")
    for idx, lead in enumerate(leads, start=1):
        s1_dur = round(lead.stage_1_call.duration_seconds, 1) if lead.stage_1_call else 0.0
        s2_dur = round(lead.stage_2_call.duration_seconds, 1) if lead.stage_2_call else 0.0
        s3_dur = round(lead.stage_3_call.duration_seconds, 1) if lead.stage_3_call else 0.0

        last_time = ""
        if lead.last_call_record and lead.last_call_record.created_at:
            last_time = lead.last_call_record.created_at.strftime("%d %b %Y %H:%M")
        elif lead.created_at:
            last_time = lead.created_at.strftime("%d %b %Y %H:%M")

        row = [
            idx,
            lead.candidate_name,
            lead.phone_number,
            lead.stage_1_status,
            s1_dur,
            lead.stage_2_status,
            s2_dur,
            lead.stage_3_status,
            s3_dur,
            lead.final_status,
            lead.total_attempts,
            last_time,
        ]
        ws.append(row)
        curr_row = idx + 1
        ws.row_dimensions[curr_row].height = 22
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=curr_row, column=col_num)
            cell.border = thin_border
            cell.alignment = align_left if col_num in [2, 3] else align_center

            # Highlight status column
            if col_num == 10:
                if lead.final_status == "ANSWERED":
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                    cell.font = Font(color="166534", bold=True)
                elif lead.final_status == "MISSED_ALL_RETRIES":
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                    cell.font = Font(color="991B1B", bold=True)

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    clean_cname = "".join(c for c in campaign.name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    filename = f"Campaign_{campaign.id}_{clean_cname}_Full_Report.xlsx"

    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
def sarvam_campaign_export_missed_api(request, campaign_id):
    """
    Generates and downloads an Excel file containing ONLY the candidate numbers
    that missed all 3 retry attempts (Stage 1, Stage 2, Stage 3).
    GET /api/sarvam/campaigns/<id>/export-missed/
    """
    from conversations.models import SarvamCampaign
    from django.http import HttpResponse
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    campaign = SarvamCampaign.objects.filter(id=campaign_id).first()
    if not campaign:
        return Response({"error": "Campaign not found"}, status=404)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Missed Numbers (3 Retries)"

    header_fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    headers = [
        "S.No",
        "Candidate Name",
        "Phone Number",
        "Total Retries Made",
        "Final Outcome",
        "Stage 1 Attempt Time",
        "Stage 2 (Retry 1) Time",
        "Stage 3 (Retry 2) Time",
        "Follow-up Recommendation",
    ]
    ws.append(headers)

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center
        cell.border = thin_border

    ws.row_dimensions[1].height = 28

    missed_leads = campaign.leads.filter(final_status="MISSED_ALL_RETRIES").order_by("id")
    for idx, lead in enumerate(missed_leads, start=1):
        t1 = lead.stage_1_call.created_at.strftime("%d %b %Y %H:%M") if (lead.stage_1_call and lead.stage_1_call.created_at) else "N/A"
        t2 = lead.stage_2_call.created_at.strftime("%d %b %Y %H:%M") if (lead.stage_2_call and lead.stage_2_call.created_at) else "N/A"
        t3 = lead.stage_3_call.created_at.strftime("%d %b %Y %H:%M") if (lead.stage_3_call and lead.stage_3_call.created_at) else "N/A"

        row = [
            idx,
            lead.candidate_name,
            lead.phone_number,
            f"{lead.total_attempts} Attempts",
            "Missed All 3 Retries (No Answer)",
            t1,
            t2,
            t3,
            "WhatsApp message or Manual Sales Call Recommended",
        ]
        ws.append(row)
        curr_row = idx + 1
        ws.row_dimensions[curr_row].height = 22
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=curr_row, column=col_num)
            cell.border = thin_border
            cell.alignment = align_left if col_num in [2, 3, 9] else align_center
            if col_num == 5:
                cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                cell.font = Font(color="991B1B", bold=True)

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    clean_cname = "".join(c for c in campaign.name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    filename = f"Campaign_{campaign.id}_{clean_cname}_Final_Missed_Numbers.xlsx"

    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
def sarvam_sample_template_api(request):
    """Generates and downloads a clean sample Excel template for Sarvam AI Campaign upload."""
    import pandas as pd
    from django.http import HttpResponse
    import io

    sample_data = [
        {
            "Candidate Name": "Rajesh Sharma",
            "Phone Number": "91525XXXXX"
        },
        {
            "Candidate Name": "Priya Patel",
            "Phone Number": "98765XXXXX"
        },
        {
            "Candidate Name": "Amit Kumar",
            "Phone Number": "91234XXXXX"
        }
    ]

    df = pd.DataFrame(sample_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Candidates")
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Sarvam_AI_Campaign_Sample_Template.xlsx"'
    return response


@api_view(["GET"])
def sarvam_agent_minutes_status_api(request, agent_slug=None):
    """
    Returns current call minutes balance, used minutes, and quota for an agent.
    GET /api/sarvam/<slug>/minutes/ or /api/sarvam/agents/<slug>/minutes/
    """
    from conversations.models import SarvamAgent
    slug = agent_slug or request.GET.get("agent_slug") or request.GET.get("agent")
    agent = None
    if slug:
        agent = SarvamAgent.objects.filter(slug=slug).first()
    if not agent:
        agent = SarvamAgent.objects.filter(is_active=True).first()

    if not agent:
        return Response({"error": "No active agent found."}, status=404)

    return Response({
        "status": "success",
        "agent_name": agent.name,
        "agent_slug": agent.slug,
        "allocated_minutes": agent.allocated_minutes,
        "used_minutes": agent.total_used_minutes,
        "used_seconds": agent.total_used_seconds,
        "remaining_minutes": agent.remaining_minutes,
        "remaining_seconds": agent.remaining_seconds,
        "is_exhausted": agent.is_minutes_exhausted,
        "usage_percentage": agent.usage_percentage,
    }, status=200)


@api_view(["POST", "PATCH"])
@permission_classes([IsAuthenticated])
def sarvam_adjust_agent_minutes_api(request, agent_slug=None):
    """
    Admin endpoint to add, subtract, or set call minutes limit and override used minutes for a SarvamAgent.
    POST /api/sarvam/<slug>/adjust-minutes/ or /api/sarvam/agents/<slug>/adjust-minutes/
    Body: {"action": "ADD"|"SUBTRACT"|"SET", "minutes": 500.0, "used_minutes": 10.5, "note": "Recharge"}
    """
    is_admin = False
    if request.user.is_superuser:
        is_admin = True
    elif hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        perms = request.user.profile.role.permissions
        if perms.get('is_admin', False):
            is_admin = True
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.custom_permissions:
        if request.user.profile.custom_permissions.get('is_admin', False):
            is_admin = True

    if not is_admin:
        return Response({"error": "Unauthorized. Only administrators can adjust minutes quota."}, status=403)

    from conversations.models import SarvamAgent, SarvamAgentMinuteAdjustment
    slug = agent_slug or (request.data or {}).get("agent_slug") or (request.data or {}).get("slug")
    agent_id = (request.data or {}).get("agent_id") or (request.data or {}).get("id")
    agent = None
    if slug:
        agent = SarvamAgent.objects.filter(slug=slug).first()
    if not agent and agent_id:
        try:
            agent = SarvamAgent.objects.filter(id=int(agent_id)).first()
        except (ValueError, TypeError):
            pass

    if not agent:
        return Response({"error": f"Agent '{slug or agent_id}' not found."}, status=404)

    action = str((request.data or {}).get("action", "ADD")).upper()
    old_allocated = agent.allocated_minutes
    amount_str = (request.data or {}).get("minutes")

    if amount_str is not None:
        try:
            amount = float(amount_str)
        except (ValueError, TypeError):
            return Response({"error": "Invalid minutes amount."}, status=400)

        if amount < 0:
            return Response({"error": "Minutes amount cannot be negative."}, status=400)

        if action == "ADD":
            agent.allocated_minutes += amount
        elif action == "SUBTRACT":
            agent.allocated_minutes = max(0.0, agent.allocated_minutes - amount)
        elif action == "SET":
            agent.allocated_minutes = max(0.0, amount)
        else:
            return Response({"error": "Invalid action. Choose ADD, SUBTRACT, or SET."}, status=400)

        agent.save(update_fields=["allocated_minutes"])

        note = str((request.data or {}).get("note") or f"Admin API {action} {amount} mins")
        SarvamAgentMinuteAdjustment.objects.create(
            agent=agent,
            action=action,
            minutes_amount=amount,
            previous_allocated_minutes=old_allocated,
            new_allocated_minutes=agent.allocated_minutes,
            adjusted_by=request.user,
            note=note
        )

    # Optional used_minutes override
    used_mins_override = (request.data or {}).get("used_minutes")
    if used_mins_override is not None:
        try:
            from django.db.models import Sum
            target_used_secs = float(used_mins_override) * 60.0
            billed_sum = float(agent.call_records.aggregate(total=Sum('billed_seconds'))['total'] or 0)
            agent.extra_used_seconds = target_used_secs - billed_sum
            agent.save(update_fields=["extra_used_seconds"])
        except (ValueError, TypeError):
            pass

    return Response({
        "status": "success",
        "message": f"Successfully updated minutes for '{agent.name}'.",
        "action": action,
        "allocated_minutes": agent.allocated_minutes,
        "used_minutes": agent.total_used_minutes,
        "remaining_minutes": agent.remaining_minutes,
        "is_exhausted": agent.is_minutes_exhausted,
    }, status=200)


@api_view(["PATCH", "POST"])
@permission_classes([IsAuthenticated])
def sarvam_toggle_agent_active_api(request, agent_id=None, agent_slug=None):
    """
    Admin endpoint to toggle active/inactive status of a SarvamAgent.
    PATCH/POST /api/sarvam/agents/<id>/toggle/ or /api/sarvam/<slug>/toggle/
    """
    is_admin = False
    if request.user.is_superuser:
        is_admin = True
    elif hasattr(request.user, 'profile') and request.user.profile and request.user.profile.role:
        perms = request.user.profile.role.permissions
        if perms.get('is_admin', False):
            is_admin = True
    if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.custom_permissions:
        if request.user.profile.custom_permissions.get('is_admin', False):
            is_admin = True

    if not is_admin:
        return Response({"error": "Unauthorized. Only administrators can change agent status."}, status=403)

    from conversations.models import SarvamAgent
    agent = None
    if agent_id is not None:
        try:
            agent = SarvamAgent.objects.filter(id=int(agent_id)).first()
        except (ValueError, TypeError):
            pass
    elif agent_slug:
        agent = SarvamAgent.objects.filter(slug=agent_slug).first()

    if not agent:
        req_id = (request.data or {}).get("agent_id") or (request.data or {}).get("id")
        req_slug = (request.data or {}).get("agent_slug") or (request.data or {}).get("slug")
        if req_id:
            try:
                agent = SarvamAgent.objects.filter(id=int(req_id)).first()
            except (ValueError, TypeError):
                pass
        elif req_slug:
            agent = SarvamAgent.objects.filter(slug=req_slug).first()

    if not agent:
        return Response({"error": "Sarvam agent not found."}, status=404)

    agent.is_active = not agent.is_active
    agent.save(update_fields=["is_active"])

    return Response({
        "status": "success",
        "agent_id": agent.id,
        "slug": agent.slug,
        "name": agent.name,
        "is_active": agent.is_active,
        "message": f"Agent '{agent.name}' is now {'Active' if agent.is_active else 'Inactive'}."
    }, status=200)

