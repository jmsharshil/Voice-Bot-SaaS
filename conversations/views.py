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
            # Fallback to search by user_number alone if campaign_id is not saved on old logs
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


# ======================================================
# TELECOM CDR WEBHOOK (POST — receives call data after call ends)
# ======================================================

from .models import CallDetailRecord
from datetime import datetime as dt


@api_view(["POST"])
def telecom_cdr_webhook(request):
    """
    Receives Call Detail Record from telecom system after each call ends.
    Matches recording_file_name (minus .wav) to Conversation.session_id.
    No authentication required (as per telecom team agreement).
    """
    data = request.data

    # Validate required fields
    required = ["call_id", "phone_number", "calldate", "did", "uniqueid"]
    missing = [f for f in required if f not in data]
    if missing:
        return Response(
            {"error": f"Missing required fields: {', '.join(missing)}"},
            status=400
        )

    # Check for duplicate (by uniqueid)
    if CallDetailRecord.objects.filter(uniqueid=data["uniqueid"]).exists():
        return Response(
            {"status": "duplicate", "message": "CDR already received for this uniqueid"},
            status=200
        )

    # Parse dates safely
    try:
        calldate = dt.strptime(data["calldate"], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        calldate = None

    answer_time = None
    if data.get("answer_time"):
        try:
            answer_time = dt.strptime(data["answer_time"], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            pass

    # Try to match to existing Conversation
    conversation = None
    matched = False

    # 1. BEST: Match by ws_session_id → Conversation.stream_sid
    ws_sid = data.get("ws_session_id")
    if ws_sid:
        conversation = Conversation.objects.filter(stream_sid=ws_sid).first()
        if conversation:
            print(f"PERFECT MATCH: ws_session_id '{ws_sid}' -> Conversation {conversation.id}")

    # 2. FALLBACK: Match by phone number (last 10 digits)
    if not conversation:
        raw_phone = data.get("phone_number", "")
        if raw_phone:
            clean_phone = "".join(filter(str.isdigit, raw_phone))[-10:]
            if clean_phone:
                conversation = Conversation.objects.filter(
                    user_number__icontains=clean_phone
                ).order_by("-started_at").first()
                if conversation:
                    print(f"FALLBACK MATCH: Phone '{clean_phone}' -> Conversation {conversation.id}")

    if conversation:
        matched = True
    else:
        print(f"NO MATCH: CDR saved but no matching conversation found.")

    # 3. Handle Recording (Download from provider and upload to Azure)
    rec_file = data.get("recording_file_name", "")
    if rec_file:
        # Normalize original URL if needed
        if not rec_file.startswith("http"):
            original_url = f"https://voice-bot.on-forge.com/recordings/{rec_file}"
        else:
            original_url = rec_file
        
        # Upload to Azure
        azure_service = AzureBlobService()
        azure_url = azure_service.download_and_upload(original_url, data.get("phone_number", "unknown"))
        
        # If azure upload worked, use that URL. Otherwise fallback to provider URL.
        if azure_url:
            rec_file = azure_url
        else:
            rec_file = original_url

    # Save CDR
    cdr = CallDetailRecord.objects.create(
        conversation=conversation,
        telecom_call_id=data.get("call_id", 0),
        phone_number=data.get("phone_number", ""),  # Customer Number
        calldate=calldate,
        did=data.get("did", ""),                     # Bot DID Number
        duration=data.get("duration", 0),
        disposition=data.get("disposition", "ANSWERED"),
        call_type=data.get("call_type", "OUTBOUND"),
        answer_time=answer_time,
        uniqueid=data["uniqueid"],
        recording_file_name=rec_file,
        matched=matched,
    )

    result = {
        "status": "success",
        "cdr_id": cdr.id,
        "matched": matched,
    }

    if matched:
        result["conversation_id"] = conversation.id
        result["agent_name"] = conversation.agent.name if conversation.agent else None
        print(f"CDR SUCCESS: {data.get('phone_number')} linked to Conversation {conversation.id}")
    else:
        print(f"CDR STORED (unmatched): {data.get('phone_number')}")

    # 🔄 AUTO-DIALER: Trigger next call if a campaign is active
    try:
        from bot.views import on_call_ended, _campaign_active
        if _campaign_active:
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
    completed = Conversation.objects.filter(
        agent=agent,
        ended_at__isnull=False
    )
    total_billed = 0.0
    for c in completed:
        raw_seconds = (c.ended_at - c.started_at).total_seconds()
        if raw_seconds > 0:
            total_billed += _round_seconds_to_billed_minutes(raw_seconds)
    return round(total_billed, 1)


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