
# Create your models here.
import uuid
from django.db import models
from django.contrib.auth.models import User


class Industry(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class AgentRoleTemplate(models.Model):
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name="roles")
    role_name = models.CharField(max_length=100)
    description = models.TextField()
    system_prompt_template = models.TextField()
    default_tone = models.CharField(max_length=50)
    default_voice = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.industry.name} - {self.role_name}"


class VoiceAgent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="agents"
    )

    industry = models.ForeignKey(
        Industry,
        on_delete=models.CASCADE,
        related_name="agents"
    )

    role_template = models.ForeignKey(
        AgentRoleTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name="agents"
    )

    name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100, blank=True)
    # ✅ ADD THIS
    summary = models.TextField(blank=True, null=True)

    api_key = models.UUIDField(default=uuid.uuid4, unique=True)
    is_demo = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    # 🔥 Dynamic prompt resolution
    @property
    def resolved_prompt(self):
        if not self.role_template:
            return ""

        return self.role_template.system_prompt_template.format(
            agent_name=self.name,
            company_name=self.company_name or "the organization"
        )

    # 🔒 Validation to prevent wrong role-industry pairing
    def save(self, *args, **kwargs):
        if self.role_template and self.role_template.industry != self.industry:
            raise ValueError("Selected role does not belong to chosen industry")

        super().save(*args, **kwargs)