from django.db import models
from conversations.models import Conversation

class IcemakeTicket(models.Model):
    COMPLAINT_CHOICES = [
        ("Blast Freezer", "Blast Freezer"),
        ("Chiller", "Chiller"),
        ("Freezer", "Freezer"),
        ("Other", "Other"),
    ]
    
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name="icemake_ticket")
    ticket_number = models.CharField(max_length=50, unique=True)
    language = models.CharField(max_length=10, default="en")
    registered_mobile = models.CharField(max_length=20, blank=True)
    customer_name = models.CharField(max_length=100, blank=True)
    company_name = models.CharField(max_length=100, blank=True)
    city_state = models.CharField(max_length=100, blank=True)
    pin_code = models.CharField(max_length=20, blank=True)
    machine_model_no = models.CharField(max_length=100, blank=True)
    machine_sr_no = models.CharField(max_length=100, blank=True)
    issue_type = models.CharField(max_length=50, choices=COMPLAINT_CHOICES, default="Other")
    issue_description = models.TextField(blank=True)
    google_sheet_synced = models.BooleanField(default=False, help_text="True if ticket has been sent to Google Sheet")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket_number} - {self.customer_name} ({self.issue_type})"
