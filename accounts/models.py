from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    permissions = models.JSONField(default=dict, help_text="JSON format permissions e.g., {'can_manage_users': true}")
    
    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    custom_permissions = models.JSONField(default=dict, blank=True, null=True, help_text="Overrides role permissions")
    assigned_agent = models.ForeignKey(
        'agents.VoiceAgent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Limits access to this voice agent's data only"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
        help_text="Tracks which user created this sub-user"
    )
    profile_picture = models.ImageField(upload_to="profile_pics/", null=True, blank=True)
    company_logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)

    def get_company_logo(self):
        """
        Returns the company logo for this profile, or recursively checks
        the creator's profile until a company logo is found.
        """
        if self.company_logo:
            return self.company_logo
            
        current = self
        visited = {current.id}
        while current.created_by:
            try:
                creator_profile = current.created_by.profile
                if creator_profile.id in visited:
                    break
                visited.add(creator_profile.id)
                if creator_profile.company_logo:
                    return creator_profile.company_logo
                current = creator_profile
            except UserProfile.DoesNotExist:
                break
        return None

    def __str__(self):
        return f"{self.user.username} Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()