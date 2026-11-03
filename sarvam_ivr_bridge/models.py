from django.db import models
from conversations.models import SarvamAgent, SarvamCallRecord


class AgentIVRForwardingConfig(models.Model):
    """
    Configuration for Sarvam Voice Agents that receive calls forwarded from an external IVR system.
    If an agent has is_active=True, incoming IVR CDRs and Sarvam CDRs will be correlated
    to resolve the real user caller number.
    """
    sarvam_agent = models.OneToOneField(
        SarvamAgent,
        on_delete=models.CASCADE,
        related_name="ivr_forwarding_config",
        help_text="The Sarvam Agent that receives forwarded calls from the client IVR"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Enable or disable IVR call forwarding and real number resolution for this agent"
    )
    ivr_provider_name = models.CharField(
        max_length=100,
        default="Generic IVR",
        help_text="e.g. Voicelink, Tata Tele, Airtel PBX, Twilio, etc."
    )
    forwarding_dids = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated DID numbers or trunk numbers used by the IVR to forward calls (e.g. +917971019486, 9484959435)"
    )
    time_window_minutes = models.PositiveIntegerField(
        default=10,
        help_text="Time window in minutes to correlate IVR call logs with Sarvam call records"
    )
    match_by_duration = models.BooleanField(
        default=True,
        help_text="Verify that call durations closely match between the IVR log and Sarvam CDR (±15s tolerance)"
    )
    auto_update_sarvam_record = models.BooleanField(
        default=True,
        help_text="Automatically update the SarvamCallRecord phone_number when matched"
    )
    notes = models.TextField(blank=True, default="", help_text="Optional client/routing notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_did_list(self):
        """Returns list of normalized clean DID digits."""
        if not self.forwarding_dids:
            return []
        dids = []
        for raw in self.forwarding_dids.split(","):
            cleaned = "".join(filter(str.isdigit, raw.strip()))
            if cleaned:
                dids.append(cleaned)
                if len(cleaned) == 12 and cleaned.startswith("91"):
                    dids.append(cleaned[2:])
        return list(set(dids))

    def __str__(self):
        status = "Active" if self.is_active else "Disabled"
        return f"{self.sarvam_agent.name} [{status}] ({self.ivr_provider_name})"

    class Meta:
        verbose_name = "Agent IVR Forwarding Config"
        verbose_name_plural = "Agent IVR Forwarding Configs"
        ordering = ["sarvam_agent__name"]


class IVRForwardedCallLog(models.Model):
    """
    Stores raw call events / CDRs received from external IVRs before and after call forwarding.
    """
    MATCH_STATUS_CHOICES = [
        ("PENDING", "Pending Match"),
        ("MATCHED", "Matched to Sarvam Call"),
        ("UNMATCHED", "Unmatched / Expired"),
        ("IGNORED", "Ignored (Agent Inactive)"),
    ]

    agent_config = models.ForeignKey(
        AgentIVRForwardingConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ivr_call_logs"
    )
    sarvam_call_record = models.OneToOneField(
        SarvamCallRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ivr_forwarded_log",
        help_text="Matched Sarvam call record"
    )
    real_caller_number = models.CharField(max_length=50, help_text="Real caller number from the user's SIM")
    forwarded_did = models.CharField(max_length=50, blank=True, default="", help_text="DID / trunk number dialed")
    ivr_call_id = models.CharField(max_length=150, blank=True, default="", help_text="External IVR Call ID / Unique ID")
    call_start_time = models.DateTimeField(null=True, blank=True)
    call_end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(default=0.0)
    disposition = models.CharField(max_length=50, default="ANSWERED")
    recording_url = models.TextField(blank=True, default="")
    raw_payload = models.JSONField(default=dict, blank=True)
    match_status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default="PENDING", db_index=True)
    matched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"IVR Log #{self.id}: {self.real_caller_number} -> {self.forwarded_did} ({self.match_status})"

    class Meta:
        verbose_name = "IVR Forwarded Call Log"
        verbose_name_plural = "IVR Forwarded Call Logs"
        ordering = ["-created_at"]

