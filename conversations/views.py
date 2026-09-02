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

        # Check if Ice Make Ticket exists for this conversation and re-sync to Google Sheet with REAL POST CALLER NUMBER!
        try:
            from icemake_bot.models import IcemakeTicket
            from icemake_bot.strategy import _append_to_google_sheet
            ticket = IcemakeTicket.objects.filter(conversation=conversation).first()
            if ticket:
                print(f"🎯 [ICEMAKE POST API CDR RECEIVED]: Syncing real SIM caller number '{data.get('phone_number')}' to Google Sheet!")
                _append_to_google_sheet(ticket, force=True)
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
    inline completely without 'Content-Disposition: attachment' or CORS restrictions.
    """
    import requests
    from django.http import StreamingHttpResponse, HttpResponse

    audio_url = request.GET.get("url")
    if not audio_url:
        return HttpResponse("Missing url parameter", status=400)

    try:
        req = requests.get(audio_url, stream=True, timeout=15)
        if req.status_code != 200:
            return HttpResponse("Failed to fetch audio from remote server", status=req.status_code)

        content_type = req.headers.get("Content-Type", "audio/mpeg")
        response = StreamingHttpResponse(
            req.iter_content(chunk_size=8192),
            content_type=content_type
        )
        response["Content-Disposition"] = "inline"
        response["Access-Control-Allow-Origin"] = "*"
        response["Accept-Ranges"] = "bytes"
        if "Content-Length" in req.headers:
            response["Content-Length"] = req.headers["Content-Length"]
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
