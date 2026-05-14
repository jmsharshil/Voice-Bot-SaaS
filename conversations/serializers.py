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
    user_number = serializers.CharField(source="conversation.user_number")
    agent_name = serializers.CharField(source="agent.name")
    call_started_at = serializers.DateTimeField(source="conversation.started_at")
    call_ended_at = serializers.DateTimeField(source="conversation.ended_at")
    
    # Telecom CDR fields
    customer_number = serializers.CharField(source="conversation.cdr.phone_number", read_only=True, allow_null=True)
    bot_number = serializers.CharField(source="conversation.cdr.did", read_only=True, allow_null=True)
    actual_duration = serializers.IntegerField(source="conversation.cdr.duration", read_only=True, allow_null=True)
    disposition = serializers.CharField(source="conversation.cdr.disposition", read_only=True, allow_null=True)
    recording_url = serializers.SerializerMethodField()

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

    class Meta:
        model = LeadAnalysis
        fields = [
            "id", "session_id", "user_number", "agent_name",
            "lead_level", "user_name", "user_email", "user_phone",
            "interest_topic", "summary", "raw_analysis",
            "call_started_at", "call_ended_at", "analyzed_at",
            "customer_number", "bot_number", "actual_duration", 
            "disposition", "recording_url",
        ]