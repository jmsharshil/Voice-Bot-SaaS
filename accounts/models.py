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
    profile_picture_url = models.CharField(max_length=1000, blank=True, null=True)
    company_logo_url = models.CharField(max_length=1000, blank=True, null=True)

    def get_company_logo(self):
        """
        Returns the company logo for this profile, or recursively checks
        the creator's profile until a company logo is found.
        """
        if self.company_logo_url:
            return self.company_logo_url
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
                if creator_profile.company_logo_url:
                    return creator_profile.company_logo_url
                if creator_profile.company_logo:
                    return creator_profile.company_logo
                current = creator_profile
            except UserProfile.DoesNotExist:
                break
        return None

    def save(self, *args, **kwargs):
        # Automatically upload to Azure Blob Storage if USE_AZURE_MEDIA is True
        from django.conf import settings
        from bot.services.azure_storage import AzureBlobService

        if getattr(settings, 'USE_AZURE_MEDIA', True):
            # 1. Handle company_logo
            if self.company_logo and not str(self.company_logo).startswith("http"):
                try:
                    azure_service = AzureBlobService()
                    # Read the file content
                    self.company_logo.file.seek(0)
                    file_content = self.company_logo.file.read()
                    self.company_logo.file.seek(0)
                    
                    # Generate unique name
                    import uuid
                    ext = self.company_logo.name.split('.')[-1]
                    filename = f"company_logos/logo_{uuid.uuid4().hex}.{ext}"
                    
                    url = azure_service.upload_image(file_content, filename)
                    if url:
                        self.company_logo_url = url
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error uploading company_logo to Azure: {e}")

            # 2. Handle profile_picture
            if self.profile_picture and not str(self.profile_picture).startswith("http"):
                try:
                    azure_service = AzureBlobService()
                    # Read the file content
                    self.profile_picture.file.seek(0)
                    file_content = self.profile_picture.file.read()
                    self.profile_picture.file.seek(0)
                    
                    # Generate unique name
                    import uuid
                    ext = self.profile_picture.name.split('.')[-1]
                    filename = f"profile_pics/pic_{uuid.uuid4().hex}.{ext}"
                    
                    url = azure_service.upload_image(file_content, filename)
                    if url:
                        self.profile_picture_url = url
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error uploading profile_picture to Azure: {e}")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()