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
    appointment_date = models.CharField(max_length=255, blank=True, default="")
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


import math

def calculate_billed_seconds(duration_seconds):
    """
    Calculates billable seconds based on 30-second telecom pulse:
      - 0 sec => 0 sec
      - 1 to 30 sec => 30 sec
      - 31 to 60 sec => 60 sec
      - 61 to 90 sec => 90 sec
      etc.
    """
    if not duration_seconds or duration_seconds <= 0:
        return 0
    return int(math.ceil(float(duration_seconds) / 30.0) * 30)


class SarvamAgent(models.Model):
    """
    Stores Sarvam AI Agent platform credentials for each configured voice agent.
    Enables multi-agent support — each agent has its own dashboard, calls, and credentials.
    """
    name = models.CharField(max_length=100, help_text="Human-readable agent name, e.g. 'Raahi - iiiEM'")
    slug = models.SlugField(unique=True, help_text="URL-safe identifier, e.g. 'raahi-iiiem', 'new-agent'")
    description = models.TextField(blank=True, default="", help_text="What this agent does")

    # Sarvam AI Platform credentials
    org_id = models.CharField(max_length=150, help_text="SARVAM_ORG_ID")
    workspace_id = models.CharField(max_length=150, help_text="SARVAM_WORKSPACE_ID")
    app_id = models.CharField(max_length=150, help_text="SARVAM_AGENT_ID (app_id on Sarvam platform)")
    api_key = models.CharField(max_length=300, help_text="SARVAM_AGENT_API_KEY (sk_samvaad_...)")
    connection_id = models.CharField(max_length=150, help_text="SARVAM_CONNECTION_ID")
    agent_phone = models.CharField(max_length=25, help_text="Phone number Sarvam dials from, e.g. +917971414121")
    webhook_domain = models.CharField(
        max_length=300,
        default="",
        blank=True,
        help_text="Public domain for CDR webhooks, e.g. https://yourngrok.ngrok-free.dev"
    )

    # Call Minute Allocation & Limits (Configured exclusively by Superadmin)
    allocated_minutes = models.FloatField(
        default=5000.0,
        help_text="Total call minutes limit allocated by Superadmin (e.g. 5000.0 mins)"
    )
    extra_used_seconds = models.FloatField(
        default=0.0,
        help_text="Additional manual seconds used adjustment by Superadmin"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_used_seconds(self):
        """Calculates total billed seconds from all call records using 30s pulse."""
        from django.db.models import Sum
        billed_sum = self.call_records.aggregate(total=Sum('billed_seconds'))['total'] or 0
        return float(billed_sum) + float(self.extra_used_seconds)

    @property
    def total_used_minutes(self):
        """Total billed minutes (used_seconds / 60.0)."""
        return round(self.total_used_seconds / 60.0, 2)

    @property
    def remaining_minutes(self):
        """Remaining minutes available for this agent."""
        return max(0.0, round(float(self.allocated_minutes) - (self.total_used_seconds / 60.0), 2))

    @property
    def remaining_seconds(self):
        """Remaining seconds available."""
        return max(0.0, (float(self.allocated_minutes) * 60.0) - self.total_used_seconds)

    @property
    def is_minutes_exhausted(self):
        """True if agent has no remaining balance for at least 1 pulse (30 sec)."""
        return self.remaining_seconds < 30.0

    @property
    def usage_percentage(self):
        """Percentage of allocated minutes consumed."""
        if self.allocated_minutes <= 0:
            return 100.0 if self.total_used_seconds > 0 else 0.0
        pct = (self.total_used_minutes / float(self.allocated_minutes)) * 100.0
        return min(100.0, round(pct, 1))

    def __str__(self):
        return f"{self.name} ({self.remaining_minutes}m left)"

    class Meta:
        verbose_name = "Sarvam Agent"
        verbose_name_plural = "Sarvam Agents"
        ordering = ["name"]


class SarvamAgentMinuteAdjustment(models.Model):
    """
    Audit log of manual additions/subtractions of minutes by SuperAdmin.
    """
    ACTION_CHOICES = [
        ("ADD", "Add Minutes"),
        ("SUBTRACT", "Subtract Minutes"),
        ("SET", "Set Total Limit"),
    ]

    agent = models.ForeignKey(
        SarvamAgent,
        on_delete=models.CASCADE,
        related_name="minute_adjustments"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    minutes_amount = models.FloatField(help_text="Amount of minutes added/subtracted or new total")
    previous_allocated_minutes = models.FloatField(default=0.0)
    new_allocated_minutes = models.FloatField(default=0.0)
    adjusted_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent.name}: {self.action} {self.minutes_amount}m (Now: {self.new_allocated_minutes}m)"

    class Meta:
        verbose_name = "Sarvam Agent Minute Adjustment"
        verbose_name_plural = "Sarvam Agent Minute Adjustments"
        ordering = ["-created_at"]


class SarvamCallRecord(models.Model):
    """
    Stores all Sarvam AI Agent outbound calls and incoming CDR webhooks.
    """
    # Link to which Sarvam agent made this call
    sarvam_agent = models.ForeignKey(
        SarvamAgent,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="call_records",
        help_text="Which Sarvam voice agent made this call"
    )
    # Link to optional campaign and retry stage
    campaign = models.ForeignKey(
        'SarvamCampaign',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="call_records",
        help_text="Campaign this call belongs to"
    )
    campaign_stage = models.IntegerField(default=1, help_text="1=Main, 2=Retry 1, 3=Retry 2")

    attempt_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    interaction_id = models.CharField(max_length=200, blank=True, null=True, db_index=True)
    phone_number = models.CharField(max_length=50)
    candidate_name = models.CharField(max_length=255, default="Candidate")
    language = models.CharField(max_length=50, default="hi-IN")
    applied_position = models.CharField(max_length=255, default="Admission Counselor")
    status = models.CharField(max_length=100, default="DIALING")
    call_type = models.CharField(max_length=50, default="Live Call")   # e.g. "Live Call", "Test Call", "Excel: Campaign"
    duration_seconds = models.FloatField(default=0.0)
    billed_seconds = models.IntegerField(
        default=0,
        help_text="Billed seconds calculated with 30s pulse (e.g. 20s->30s, 40s->60s)"
    )
    start_time = models.DateTimeField(null=True, blank=True)           # Sarvam start time
    audio_url = models.TextField(blank=True, null=True)
    summary = models.JSONField(default=dict, blank=True)
    transcript = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.billed_seconds = calculate_billed_seconds(self.duration_seconds)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.candidate_name} ({self.phone_number}) - {self.status}"

    class Meta:
        verbose_name = "Sarvam Call Record"
        verbose_name_plural = "Sarvam Call Records"
        ordering = ["-created_at"]


class SarvamCampaign(models.Model):
    """
    Represents a bulk Excel calling campaign with a 3-stage lifecycle:
    Stage 1: Main Campaign (all leads)
    Stage 2: Retry #1 (missed calls from Stage 1)
    Stage 3: Retry #2 / Final (missed calls from Stage 2)
    """
    STAGE_CHOICES = [
        (1, "Stage 1: Main Campaign"),
        (2, "Stage 2: Retry #1"),
        (3, "Stage 3: Final Retry #2"),
        (4, "All Stages Completed"),
    ]

    STATUS_CHOICES = [
        ("QUEUED", "Queued"),
        ("RUNNING_MAIN", "Running Main Campaign"),
        ("WAITING_RETRY_1", "Waiting for Retry #1 (5-Min Gap)"),
        ("RUNNING_RETRY_1", "Running Retry #1"),
        ("WAITING_RETRY_2", "Waiting for Final Retry (5-Min Gap)"),
        ("RUNNING_RETRY_2", "Running Retry #2 (Final)"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    name = models.CharField(max_length=255, default="Excel Campaign")
    sarvam_agent = models.ForeignKey(
        SarvamAgent,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="campaigns",
        help_text="Sarvam voice agent used for this campaign"
    )
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sarvam_campaigns"
    )
    excel_file_name = models.CharField(max_length=255, blank=True, default="")
    total_leads = models.IntegerField(default=0)
    current_stage = models.IntegerField(choices=STAGE_CHOICES, default=1)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="QUEUED")

    # Stage metrics
    stage_1_dispatched = models.IntegerField(default=0)
    stage_1_answered = models.IntegerField(default=0)
    stage_1_missed = models.IntegerField(default=0)

    stage_2_dispatched = models.IntegerField(default=0)
    stage_2_answered = models.IntegerField(default=0)
    stage_2_missed = models.IntegerField(default=0)

    stage_3_dispatched = models.IntegerField(default=0)
    stage_3_answered = models.IntegerField(default=0)
    stage_3_missed = models.IntegerField(default=0)

    answered_count = models.IntegerField(default=0)
    missed_count = models.IntegerField(default=0)
    delay_seconds = models.IntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Campaign #{self.id} — {self.name} ({self.status})"

    class Meta:
        verbose_name = "Sarvam Campaign"
        verbose_name_plural = "Sarvam Campaigns"
        ordering = ["-created_at"]


class SarvamCampaignLead(models.Model):
    """
    Individual lead within a SarvamCampaign, tracking call outcome across all 3 stages.
    """
    LEAD_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ANSWERED", "Answered / Picked Up"),
        ("MISSED", "Missed / No Answer"),
        ("FAILED", "Failed"),
        ("SKIPPED", "Skipped (Already Picked Up)"),
    ]

    FINAL_OUTCOME_CHOICES = [
        ("IN_PROGRESS", "In Progress"),
        ("ANSWERED", "Answered / Picked Up"),
        ("MISSED_ALL_RETRIES", "Missed All 3 Attempts"),
        ("FAILED", "Failed"),
    ]

    campaign = models.ForeignKey(
        SarvamCampaign,
        on_delete=models.CASCADE,
        related_name="leads"
    )
    candidate_name = models.CharField(max_length=255, default="Candidate")
    phone_number = models.CharField(max_length=50)
    applied_position = models.CharField(max_length=255, default="Admission Counselor")
    language = models.CharField(max_length=50, default="hi-IN")
    extra_variables = models.JSONField(default=dict, blank=True)

    # Stage 1 (Main)
    stage_1_call = models.ForeignKey(
        SarvamCallRecord,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="stage_1_lead"
    )
    stage_1_status = models.CharField(max_length=50, choices=LEAD_STATUS_CHOICES, default="PENDING")

    # Stage 2 (Retry 1)
    stage_2_call = models.ForeignKey(
        SarvamCallRecord,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="stage_2_lead"
    )
    stage_2_status = models.CharField(max_length=50, choices=LEAD_STATUS_CHOICES, default="SKIPPED")

    # Stage 3 (Retry 2 - Final)
    stage_3_call = models.ForeignKey(
        SarvamCallRecord,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="stage_3_lead"
    )
    stage_3_status = models.CharField(max_length=50, choices=LEAD_STATUS_CHOICES, default="SKIPPED")

    final_status = models.CharField(max_length=50, choices=FINAL_OUTCOME_CHOICES, default="IN_PROGRESS")
    total_attempts = models.IntegerField(default=0)
    last_call_record = models.ForeignKey(
        SarvamCallRecord,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="latest_lead"
    )
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dynamic Excel/CSV variables like car_model, model, city, area, budget"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.candidate_name} ({self.phone_number}) - Final: {self.final_status}"

    class Meta:
        verbose_name = "Sarvam Campaign Lead"
        verbose_name_plural = "Sarvam Campaign Leads"
        ordering = ["id"]
