from django.db import models

# Create your models here.
from django.db import models
from agents.models import VoiceAgent


class ConversationLog(models.Model):
    agent = models.ForeignKey(VoiceAgent, on_delete=models.CASCADE)
    user_message = models.TextField()
    agent_reply = models.TextField()
    source = models.CharField(max_length=20, default="api")
    created_at = models.DateTimeField(auto_now_add=True)

class ConversationSession(models.Model):
    agent = models.ForeignKey(VoiceAgent, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=255)
    current_intent = models.CharField(max_length=100, blank=True, null=True)
    stage = models.CharField(max_length=100, blank=True, null=True)
    state = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.agent.name} - {self.session_id}"
    


class Conversation(models.Model):
    agent = models.ForeignKey(VoiceAgent, on_delete=models.CASCADE)
    campaign_id = models.IntegerField(null=True, blank=True, db_index=True)

    session_id = models.CharField(max_length=100, unique=True)
    stream_sid = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    user_number = models.CharField(max_length=20)

    CALL_TYPE_CHOICES = [
        ("INBOUND", "Inbound"),
        ("OUTBOUND", "Outbound"),
    ]
    call_type = models.CharField(
        max_length=10,
        choices=CALL_TYPE_CHOICES,
        default="OUTBOUND",
        db_index=True
    )

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user_number} - {self.session_id}"


class Message(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("bot", "Bot"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)


class LeadAnalysis(models.Model):
    """Post-call LLM analysis — lead scoring and detail extraction."""
    LEAD_LEVELS = [
        ("hot", "Hot — Interested to buy"),
        ("warm", "Warm — Mid-level interest"),
        ("cold", "Cold — Low interest"),
        ("not_interested", "Not Interested"),
    ]

    conversation = models.OneToOneField(
        Conversation,
        on_delete=models.CASCADE,
        related_name="lead_analysis"
    )
    agent = models.ForeignKey(VoiceAgent, on_delete=models.CASCADE)

    lead_level = models.CharField(max_length=20, choices=LEAD_LEVELS)
    user_name = models.CharField(max_length=255, blank=True, default="")
    user_email = models.CharField(max_length=255, blank=True, default="")
    user_phone = models.CharField(max_length=50, blank=True, default="")
    interest_topic = models.CharField(max_length=255, blank=True, default="")
    summary = models.TextField(blank=True, default="")
    raw_analysis = models.JSONField(default=dict, blank=True)

    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lead_level.upper()} — {self.user_name or 'Unknown'} ({self.conversation.session_id[:8]})"

    class Meta:
        verbose_name = "Lead Analysis"
        verbose_name_plural = "Lead Analyses"
        ordering = ["-analyzed_at"]


class CallDetailRecord(models.Model):
    """Telecom CDR data received via webhook after each call ends."""
    DISPOSITION_CHOICES = [
        ("ANSWERED", "Answered"),
        ("NO ANSWER", "No Answer"),
        ("BUSY", "Busy"),
        ("FAILED", "Failed"),
    ]
    CALL_TYPE_CHOICES = [
        ("INBOUND", "Inbound"),
        ("OUTBOUND", "Outbound"),
    ]

    conversation = models.OneToOneField(
        Conversation,
        on_delete=models.CASCADE,
        related_name="cdr",
        null=True, blank=True,
        help_text="Matched conversation (via recording_file_name → session_id)"
    )

    # Raw telecom fields
    telecom_call_id = models.IntegerField(help_text="Telecom internal call ID")
    phone_number = models.CharField(max_length=20)
    calldate = models.DateTimeField()
    did = models.CharField(max_length=20, help_text="DID number (bot phone number)")
    duration = models.IntegerField(default=0, help_text="Call duration in seconds")
    disposition = models.CharField(max_length=20, choices=DISPOSITION_CHOICES, default="ANSWERED")
    call_type = models.CharField(max_length=10, choices=CALL_TYPE_CHOICES, default="OUTBOUND")
    answer_time = models.DateTimeField(null=True, blank=True)
    uniqueid = models.CharField(max_length=50, unique=True, help_text="Telecom unique ID")
    recording_file_name = models.CharField(max_length=255, blank=True, default="")

    # Internal tracking
    matched = models.BooleanField(default=False, help_text="Whether matched to a Conversation")
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "✅" if self.matched else "❌"
        return f"{status} {self.phone_number} — {self.disposition} ({self.duration}s)"

    class Meta:
        verbose_name = "Call Detail Record"
        verbose_name_plural = "Call Detail Records"
        ordering = ["-received_at"]