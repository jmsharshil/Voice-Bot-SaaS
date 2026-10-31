from django.db import models


class AgentWhatsAppConfig(models.Model):
    """
    Stores Meta WhatsApp Cloud API credentials strictly per SarvamAgent.
    Each agent has its own dedicated Meta Business Phone Number, WABA, and Token.
    If an agent has no AgentWhatsAppConfig or is_active=False, WhatsApp automation is 100% bypassed.
    """
    agent = models.OneToOneField(
        'conversations.SarvamAgent',
        on_delete=models.CASCADE,
        related_name='whatsapp_config',
        help_text="Which Voice Agent owns these WhatsApp credentials"
    )
    phone_number_id = models.CharField(
        max_length=60,
        help_text="Meta Phone Number ID from WhatsApp App Dashboard (e.g. 102938475612345)"
    )
    waba_id = models.CharField(
        max_length=60,
        blank=True,
        default="",
        help_text="WhatsApp Business Account ID (WABA ID)"
    )
    access_token = models.TextField(
        help_text="Meta Permanent System User Access Token (Bearer token with whatsapp_business_messaging permission)"
    )
    phone_display_number = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="Sender Phone Number (e.g. +91 98765 43210) for reference"
    )
    api_version = models.CharField(
        max_length=15,
        default="v21.0",
        help_text="Meta Graph API Version (e.g. v21.0)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Enable or disable WhatsApp automation for this agent"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.agent.name} — WhatsApp ({self.phone_display_number or self.phone_number_id}) [{status}]"

    class Meta:
        verbose_name = "Agent WhatsApp Config"
        verbose_name_plural = "Agent WhatsApp Configs"
        ordering = ["agent__name"]


class WhatsAppTemplate(models.Model):
    """
    Represents an approved Meta WhatsApp Business Template belonging to an Agent.
    """
    HEADER_TYPE_CHOICES = [
        ('NONE', 'None'),
        ('DOCUMENT', 'Document (PDF / Brochure)'),
        ('IMAGE', 'Image (JPEG / PNG)'),
        ('VIDEO', 'Video (MP4)'),
        ('TEXT', 'Text Header'),
    ]

    CATEGORY_CHOICES = [
        ('MARKETING', 'Marketing'),
        ('UTILITY', 'Utility'),
        ('AUTHENTICATION', 'Authentication'),
    ]

    agent_config = models.ForeignKey(
        AgentWhatsAppConfig,
        on_delete=models.CASCADE,
        related_name='templates',
        help_text="Agent WhatsApp credentials to which this template belongs"
    )
    template_name = models.CharField(
        max_length=120,
        help_text="Exact template name approved in Meta Business Manager (e.g. 'kia_seltos_brochure')"
    )
    language_code = models.CharField(
        max_length=20,
        default="en",
        help_text="Meta language code (e.g. 'en', 'en_US', 'hi', 'gu')"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='MARKETING'
    )
    header_type = models.CharField(
        max_length=20,
        choices=HEADER_TYPE_CHOICES,
        default='NONE',
        help_text="Type of media header if template has a header"
    )
    header_media_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Default public media URL (e.g. PDF brochure link) or dynamic key"
    )
    header_filename = models.CharField(
        max_length=100,
        blank=True,
        default="Brochure.pdf",
        help_text="Filename displayed on WhatsApp for document attachments"
    )
    variables_schema = models.JSONField(
        default=list,
        blank=True,
        help_text="Default list of variable source keys for {{1}}, {{2}}, etc. (e.g. ['candidate_name', 'summary.car_model'])"
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Human notes explaining what this template sends"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.agent_config.agent.name} — {self.template_name} ({self.language_code})"

    class Meta:
        verbose_name = "WhatsApp Template"
        verbose_name_plural = "WhatsApp Templates"
        unique_together = [('agent_config', 'template_name', 'language_code')]
        ordering = ["agent_config__agent__name", "template_name"]


class WhatsAppRule(models.Model):
    """
    Conditional logic defining WHEN and WHAT WhatsApp message to dispatch.
    Fully customizable per agent from Django Admin without writing code.
    """
    agent_config = models.ForeignKey(
        AgentWhatsAppConfig,
        on_delete=models.CASCADE,
        related_name='rules',
        help_text="Which agent this rule applies to"
    )
    rule_name = models.CharField(
        max_length=150,
        help_text="e.g. 'Send Brochure on High Intent' or 'Send Appointment Confirmation'"
    )
    template = models.ForeignKey(
        WhatsAppTemplate,
        on_delete=models.CASCADE,
        related_name='rules',
        help_text="Which Meta template to dispatch"
    )

    # ── CONDITIONS ──
    trigger_statuses = models.CharField(
        max_length=255,
        default="INTERESTED,INTERVIEW,CONFIRMED",
        help_text="Comma-separated statuses to trigger on, or 'ANY' (e.g. INTERESTED, CALLBACK, NOT_INTERESTED, ANY)"
    )
    required_tag = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional required tag in summary (e.g. 'Test Drive Request', 'High Intent')"
    )
    required_keyword = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional keyword inside transcript or summary (case-insensitive)"
    )
    min_duration_seconds = models.PositiveIntegerField(
        default=5,
        help_text="Minimum call duration in seconds required to trigger (prevents spam on missed/failed calls)"
    )

    # ── DYNAMIC VARIABLE MAPPINGS ──
    variable_mappings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Map of template variables. E.g. {'1': 'candidate_name', '2': 'summary.product_interest', '3': 'agent_name'}"
    )
    header_media_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Optional override header media URL (e.g. specific car brochure PDF link)"
    )

    delay_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Optional delay in seconds before sending (e.g. 5 or 10s)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Toggle this rule ON or OFF"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "Active" if self.is_active else "Disabled"
        return f"[{self.agent_config.agent.name}] {self.rule_name} -> {self.template.template_name} ({status})"

    class Meta:
        verbose_name = "WhatsApp Automation Rule"
        verbose_name_plural = "WhatsApp Automation Rules"
        ordering = ["agent_config__agent__name", "rule_name"]


class WhatsAppMessageLog(models.Model):
    """
    Audit log of all sent, delivered, or failed WhatsApp messages.
    Guarantees idempotency — prevents duplicate sends for the same call record and rule.
    """
    STATUS_CHOICES = [
        ('QUEUED', 'Queued'),
        ('SENT', 'Sent to Meta'),
        ('DELIVERED', 'Delivered'),
        ('READ', 'Read by Customer'),
        ('FAILED', 'Failed'),
        ('SKIPPED', 'Skipped (Did Not Match Conditions)'),
    ]

    agent = models.ForeignKey(
        'conversations.SarvamAgent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_logs',
        help_text="Which agent sent this WhatsApp message"
    )
    call_record = models.ForeignKey(
        'conversations.SarvamCallRecord',
        on_delete=models.CASCADE,
        related_name='whatsapp_logs',
        help_text="The call record that triggered this message"
    )
    rule = models.ForeignKey(
        WhatsAppRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    template_name = models.CharField(max_length=120)
    recipient_phone = models.CharField(max_length=30)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='QUEUED',
        db_index=True
    )
    meta_message_id = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
        help_text="WhatsApp Message ID returned by Meta (e.g. wamid.HBg...)"
    )
    payload_sent = models.JSONField(
        default=dict,
        blank=True,
        help_text="The exact JSON payload dispatched to Meta"
    )
    meta_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="The response received from Meta API"
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error message if send or delivery failed"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.agent.name if self.agent else 'N/A'} -> {self.recipient_phone} ({self.template_name}) [{self.status}]"

    class Meta:
        verbose_name = "WhatsApp Message Log"
        verbose_name_plural = "WhatsApp Message Logs"
        # Anti-duplicate lock: A call record will never trigger the same rule twice!
        unique_together = [('call_record', 'rule')]
        ordering = ["-created_at"]

