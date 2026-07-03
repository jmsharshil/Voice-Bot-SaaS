

# # Create your models here.
# from django.db import models


# class UploadBatch(models.Model):
#     name = models.CharField(max_length=200)          # original filename
#     uploaded_at = models.DateTimeField(auto_now_add=True)
#     customer_count = models.IntegerField(default=0)

#     def __str__(self):
#         return f"{self.name} ({self.customer_count} contacts)"


# class Customer(models.Model):
#     name = models.CharField(max_length=100)
#     phone = models.CharField(max_length=15)
#     policy_type = models.CharField(max_length=100)
#     expiry_date = models.DateField()
#     reminder_sent = models.BooleanField(default=False)
#     batch = models.ForeignKey('UploadBatch', on_delete=models.CASCADE, null=True, blank=True, related_name='customers')

#     conversation_state = models.CharField(
#         max_length=50,
#         default="initial")

#     def __str__(self):
#         return self.name
    
# # 🔥 NEW MODEL
# class ChatMessage(models.Model):
#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
#     message = models.TextField()
#     sender = models.CharField(max_length=10)  # "user" or "bot"
#     timestamp = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.customer.name} - {self.sender}"
    
# class UploadedFile(models.Model):
#     file = models.FileField(upload_to="uploads/")
#     file_type = models.CharField(max_length=20, blank=True, null=True)
#     uploaded_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.file.name













# ============================================================
#  bot/models.py
# ============================================================

from django.db import models


class UploadBatch(models.Model):
    name            = models.CharField(max_length=200)
    uploaded_at     = models.DateTimeField(auto_now_add=True)
    customer_count  = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.customer_count} contacts)"


class Customer(models.Model):

    # ── Customer type ──────────────────────────────────────
    CUSTOMER_TYPE_CHOICES = [
        ("renewal", "Renewal"),
        ("new",     "New Insurance"),
    ]

    # ── Vehicle type ───────────────────────────────────────
    VEHICLE_TYPE_CHOICES = [
        ("Car",         "Car / SUV / MUV"),
        ("Bike",        "Bike / Scooter / Moped"),
        ("Commercial",  "Commercial Vehicle"),
        ("Auto",        "Auto Rickshaw / E-Rickshaw"),
        ("Tractor",     "Tractor / Farm Equipment"),
    ]

    # ── Source: inbound (walk-in) vs outbound (uploaded) ───
    SOURCE_CHOICES = [
        ("inbound",  "Inbound"),
        ("outbound", "Outbound"),
    ]

    # ── Core fields ────────────────────────────────────────
    name            = models.CharField(max_length=100, default="User")
    phone           = models.CharField(max_length=15)          # NOT unique — unique_together below

    source          = models.CharField(
                        max_length=10,
                        choices=SOURCE_CHOICES,
                        default="outbound",
                      )

    # customer type — renewal or new insurance
    customer_type   = models.CharField(
                        max_length=10,
                        choices=CUSTOMER_TYPE_CHOICES,
                        default="new"
                      )

    # vehicle details
    vehicle_type    = models.CharField(
                        max_length=20,
                        choices=VEHICLE_TYPE_CHOICES,
                        default="Car"
                      )
    vehicle_number  = models.CharField(max_length=20, blank=True, null=True)

    # vehicle model collected during inbound conversation
    vehicle_model   = models.CharField(max_length=100, blank=True, null=True)

    # Kept for backward compatibility
    policy_type     = models.CharField(max_length=100, blank=True, null=True)
    expiry_date     = models.DateField(blank=True, null=True)

    reminder_sent   = models.BooleanField(default=False)

    batch           = models.ForeignKey(
                        'UploadBatch',
                        on_delete=models.CASCADE,
                        null=True, blank=True,
                        related_name='customers'
                      )

    # ── Conversation state machine ─────────────────────────
    # "inactive" → inbound user, hasn't started yet
    # "initial"  → outbound user, received first bot message
    conversation_state = models.CharField(max_length=50, default="inactive")

    # store selections during conversation
    selected_coverage  = models.CharField(max_length=100, blank=True, null=True)
    selected_addons    = models.CharField(max_length=200, blank=True, null=True)
    quoted_premium     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [("phone", "source")]

    def __str__(self):
        return f"{self.name} ({self.vehicle_type} | {self.customer_type} | {self.source})"


class ChatMessage(models.Model):
    customer    = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='chatmessage_set')
    message     = models.TextField()
    sender      = models.CharField(max_length=10)   # "user" or "bot"
    timestamp   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} - {self.sender}"


class UploadedFile(models.Model):
    file        = models.FileField(upload_to="uploads/")
    file_type   = models.CharField(max_length=20, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name


class CampaignStatus(models.Model):
    """Persists the state of the last auto-dialer campaign."""
    total_count     = models.IntegerField(default=0)
    completed_count = models.IntegerField(default=0)
    missed_calls    = models.TextField(default="[]")  # JSON string of phone numbers
    is_active       = models.BooleanField(default=False)
    started_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Campaign Statuses"

    def __str__(self):
        return f"Campaign Started at {self.started_at} (Active: {self.is_active})"


class Campaign(models.Model):
    """Stores the full history of every auto-dialer campaign run."""
    name            = models.CharField(max_length=255, blank=True, default="")
    phone_list      = models.TextField(default="[]")    # JSON array of all dialed phones
    total_count     = models.IntegerField(default=0)
    completed_count = models.IntegerField(default=0)
    answered_count  = models.IntegerField(default=0)
    missed_calls    = models.TextField(default="[]")    # JSON array of no-answer phones
    is_active       = models.BooleanField(default=True)
    started_at      = models.DateTimeField(auto_now_add=True)
    ended_at        = models.DateTimeField(null=True, blank=True)
    created_by      = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns"
    )
    agent           = models.ForeignKey(
        'agents.VoiceAgent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns"
    )
    parent_campaign = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_campaigns"
    )
    retry_count     = models.IntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self):
        status = "Active" if self.is_active else "Completed"
        return f"Campaign #{self.id} — {status} ({self.total_count} calls)"