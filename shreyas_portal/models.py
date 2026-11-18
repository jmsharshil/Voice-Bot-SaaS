from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class ShreyasDepartment(models.Model):
    """
    Departments / Interest Categories for Shreyas Foundation
    (e.g., School, Library, Outreach & Sports, Camping, etc.)
    Can be dynamically added, edited, or removed by the Main User.
    """
    name = models.CharField(max_length=100, unique=True, help_text="e.g. School, Library, Outreach, Sports")
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default="")
    keywords = models.TextField(
        help_text="Comma-separated trigger keywords for auto-routing (e.g. school, admission, class, cbse, syllabus)"
    )
    icon = models.CharField(max_length=50, default="fa-graduation-cap", help_text="FontAwesome icon class")
    badge_color = models.CharField(max_length=30, default="#2563eb", help_text="Hex color code for badge/theme")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_keywords_list(self):
        """Returns normalized list of keywords (lowercase, trimmed)."""
        if not self.keywords:
            return []
        return [k.strip().lower() for k in self.keywords.split(",") if k.strip()]

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} [{status}]"

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Shreyas Department"
        verbose_name_plural = "Shreyas Departments"


class ShreyasUserProfile(models.Model):
    """
    Extends standard Django user for Shreyas Portal:
    - MAIN_ADMIN (Superadmin): Can create Main Users and Sub-Users, full system control.
    - MAIN_USER (Foundation Master): Created by Main Admin. Sees all departments, can create Sub-Users, manage departments.
    - SUB_USER (Department Staff): Created by Main Admin or Main User. Scoped strictly to assigned department(s).
    """
    USER_TYPE_CHOICES = [
        ("MAIN_ADMIN", "Main Admin (Superadmin)"),
        ("MAIN_USER", "Main User (Foundation Master)"),
        ("SUB_USER", "Sub-User (Department Staff)"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="shreyas_profile")
    user_type = models.CharField(
        max_length=30,
        choices=USER_TYPE_CHOICES,
        default="SUB_USER",
        help_text="Role hierarchy level"
    )
    is_master_admin = models.BooleanField(
        default=False,
        help_text="Legacy flag: True if user has master access to all departments"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shreyas_created_users",
        help_text="Tracks who created this user (Main Admin or Main User)"
    )
    assigned_departments = models.ManyToManyField(
        ShreyasDepartment,
        blank=True,
        related_name="assigned_subusers",
        help_text="Departments visible to this sub-user"
    )
    phone_number = models.CharField(max_length=30, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_system_admin(self):
        return self.user.is_superuser or self.user_type == "MAIN_ADMIN"

    @property
    def is_main_user_or_higher(self):
        return self.is_system_admin or self.user_type == "MAIN_USER" or self.is_master_admin

    def can_create_main_users(self):
        return self.is_system_admin

    def can_create_sub_users(self):
        return self.is_main_user_or_higher

    def can_view_all_departments(self):
        return self.is_main_user_or_higher

    def get_allowed_department_ids(self):
        if self.can_view_all_departments():
            return list(ShreyasDepartment.objects.values_list("id", flat=True))
        return list(self.assigned_departments.values_list("id", flat=True))

    def __str__(self):
        return f"{self.user.username} [{self.get_user_type_display()}]"


class ShreyasCallLead(models.Model):
    """
    Stores calls & leads for Shreyas Foundation with automatic department mapping.
    """
    STATUS_CHOICES = [
        ("COMPLETED", "Completed"),
        ("DIALING", "Dialing"),
        ("MISSED", "Missed"),
        ("BUSY", "Busy"),
        ("NO_ANSWER", "No Answer"),
        ("FAILED", "Failed"),
    ]

    SENTIMENT_CHOICES = [
        ("HOT", "Hot (High Interest)"),
        ("WARM", "Warm (Moderate Interest)"),
        ("COLD", "Cold (Low / No Interest)"),
    ]

    STAGE_CHOICES = [
        ("NEW", "New Lead"),
        ("QUALIFIED", "Qualified"),
        ("CALLBACK_SCHEDULED", "Callback Scheduled"),
        ("VISIT_BOOKED", "Campus Visit Booked"),
        ("ENROLLED", "Enrolled / Converted"),
        ("CLOSED", "Closed / Not Interested"),
    ]

    sarvam_call_record = models.ForeignKey(
        'conversations.SarvamCallRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shreyas_leads"
    )
    department = models.ForeignKey(
        ShreyasDepartment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
        help_text="Mapped department based on caller interest"
    )
    phone_number = models.CharField(max_length=30, db_index=True)
    caller_name = models.CharField(max_length=150, default="Caller")
    interaction_id = models.CharField(max_length=150, blank=True, default="", db_index=True)
    call_type = models.CharField(max_length=50, default="Inbound Call")
    duration_seconds = models.FloatField(default=0.0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="COMPLETED")
    lead_sentiment = models.CharField(max_length=30, choices=SENTIMENT_CHOICES, default="WARM")
    pipeline_stage = models.CharField(max_length=50, choices=STAGE_CHOICES, default="NEW")
    
    audio_url = models.TextField(blank=True, default="")
    summary = models.TextField(blank=True, default="")
    transcript = models.TextField(blank=True, default="")
    detected_intent = models.CharField(max_length=200, blank=True, default="")
    matched_keywords = models.CharField(max_length=255, blank=True, default="")
    
    notes = models.TextField(blank=True, default="")
    callback_datetime = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def formatted_duration(self):
        secs = int(self.duration_seconds or 0)
        mins = secs // 60
        rem = secs % 60
        return f"{mins}m {rem}s" if mins > 0 else f"{rem}s"

    def __str__(self):
        dept_name = self.department.name if self.department else "Unassigned"
        return f"{self.caller_name} ({self.phone_number}) -> {dept_name}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Shreyas Call Lead"
        verbose_name_plural = "Shreyas Call Leads"
