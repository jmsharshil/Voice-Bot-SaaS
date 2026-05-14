

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