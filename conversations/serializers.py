from rest_framework import serializers
from .models import Conversation, Message, LeadAnalysis


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "text", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["session_id", "user_number", "started_at", "ended_at"]


class LeadAnalysisSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(source="conversation.session_id")
    user_number = serializers.SerializerMethodField()
    agent_name = serializers.CharField(source="agent.name")
    call_started_at = serializers.DateTimeField(source="conversation.started_at")
    call_ended_at = serializers.DateTimeField(source="conversation.ended_at")
    call_type = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()
    
    customer_number = serializers.SerializerMethodField()
    bot_number = serializers.SerializerMethodField()
    actual_duration = serializers.IntegerField(source="conversation.cdr.duration", read_only=True, allow_null=True)
    disposition = serializers.CharField(source="conversation.cdr.disposition", read_only=True, allow_null=True)
    recording_url = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()

    def _clean_number(self, num):
        if not num:
            return ""
        num_str = str(num).strip()
        if num_str.startswith("+0"):
            num_str = num_str[2:]
        elif num_str.startswith("0"):
            num_str = num_str[1:]
        elif num_str.startswith("+"):
            num_str = num_str[1:]
        return num_str

    def get_call_type(self, obj):
        try:
            if hasattr(obj.conversation, 'cdr') and obj.conversation.cdr and obj.conversation.cdr.call_type:
                return obj.conversation.cdr.call_type
        except:
            pass
        return obj.conversation.call_type

    def get_user_number(self, obj):
        return self._clean_number(obj.conversation.user_number)

    def get_user_phone(self, obj):
        return self._clean_number(obj.user_phone)

    def get_customer_number(self, obj):
        try:
            if hasattr(obj.conversation, 'cdr') and obj.conversation.cdr and obj.conversation.cdr.phone_number:
                return self._clean_number(obj.conversation.cdr.phone_number)
        except:
            pass
        return self._clean_number(obj.conversation.user_number)

    def get_bot_number(self, obj):
        try:
            if hasattr(obj.conversation, 'cdr') and obj.conversation.cdr and obj.conversation.cdr.did:
                return obj.conversation.cdr.did
        except:
            pass
        return "+917969016753"

    def get_recording_url(self, obj):
        try:
            if hasattr(obj.conversation, 'cdr') and obj.conversation.cdr:
                url = obj.conversation.cdr.recording_file_name
                if url and not url.startswith("http"):
                    return f"https://voice-bot.on-forge.com/recordings/{url}"
                return url
        except:
            pass
        return None

    def get_language(self, obj):
        try:
            # Check conversation messages to detect language
            messages = obj.conversation.messages.all()
            for m in messages:
                text = m.text or ""
                # Check for Gujarati characters (range 0A80 to 0AFF)
                if any(ord(c) >= 0x0A80 and ord(c) <= 0x0AFF for c in text):
                    return "gu"
                # Check for Hindi/Devanagari characters (range 0900 to 097F)
                if any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in text):
                    return "hi"
        except Exception:
            pass
        return "en"

    class Meta:
        model = LeadAnalysis
        fields = [
            "id", "session_id", "user_number", "agent_name", "language",
            "lead_level", "user_name", "user_email", "user_phone",
            "interest_topic", "summary", "raw_analysis",
            "call_started_at", "call_ended_at", "analyzed_at",
            "customer_number", "bot_number", "actual_duration", 
            "disposition", "recording_url", "call_type",
        ]