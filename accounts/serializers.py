# from django.contrib.auth.models import User
# from rest_framework import serializers


# class RegisterSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True)

#     class Meta:
#         model = User
#         fields = ["username", "email", "password"]

#     def create(self, validated_data):
#         return User.objects.create_user(**validated_data)







from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Role, UserProfile
from agents.models import VoiceAgent

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions"]

class UserProfileSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source="role", write_only=True, required=False, allow_null=True
    )
    assigned_agent_id = serializers.PrimaryKeyRelatedField(
        queryset=VoiceAgent.objects.all(), source="assigned_agent", required=False, allow_null=True
    )
    assigned_agent_name = serializers.CharField(source="assigned_agent.name", read_only=True, allow_null=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, allow_null=True)

    class Meta:
        model = UserProfile
        fields = ["role", "role_id", "custom_permissions", "assigned_agent_id", "assigned_agent_name", "created_by_username", "profile_picture", "company_logo"]

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source="profile.role", write_only=True, required=False, allow_null=True
    )
    assigned_agent_id = serializers.PrimaryKeyRelatedField(
        queryset=VoiceAgent.objects.all(), source="profile.assigned_agent", required=False, allow_null=True
    )

    custom_permissions = serializers.JSONField(source="profile.custom_permissions", write_only=True, required=False, allow_null=True)

    # Add write-only fields for user update details
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    role_name = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    permissions = serializers.JSONField(write_only=True, required=False, allow_null=True)
    company_logo = serializers.ImageField(write_only=True, required=False, allow_null=True)

    is_superuser = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "profile", "role_id", "assigned_agent_id", 
            "custom_permissions", "password", "role_name", "permissions", "company_logo",
            "is_superuser"
        ]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        role_name = validated_data.pop('role_name', None)
        permissions = validated_data.pop('permissions', None)
        company_logo = validated_data.pop('company_logo', None)
        password = validated_data.pop('password', None)

        if 'role' in profile_data:
            instance.profile.role = profile_data['role']
        elif role_name:
            role, created = Role.objects.get_or_create(name=role_name)
            instance.profile.role = role

        if 'custom_permissions' in profile_data:
            instance.profile.custom_permissions = profile_data['custom_permissions']
        elif permissions is not None:
            if isinstance(permissions, str):
                import json
                try:
                    permissions = json.loads(permissions)
                except Exception:
                    pass
            instance.profile.custom_permissions = permissions

        if 'assigned_agent' in profile_data:
            instance.profile.assigned_agent = profile_data['assigned_agent']

        if company_logo:
            instance.profile.company_logo = company_logo

        instance.profile.save()

        if password:
            instance.set_password(password)

        return super().update(instance, validated_data)

# class RegisterSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True)
#     role_id = serializers.PrimaryKeyRelatedField(
#         queryset=Role.objects.all(), write_only=True, required=False, allow_null=True
#     )

#     class Meta:
#         model = User
#         fields = ["username", "email", "password", "role_id"]

#     def create(self, validated_data):
#         role = validated_data.pop("role_id", None)
#         user = User.objects.create_user(**validated_data)
#         if role:
#             # profile is auto-created by signals, so we just update it
#             user.profile.role = role
#             user.profile.save()
#         return user




class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role_name = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    permissions = serializers.JSONField(write_only=True, required=False, allow_null=True)
    assigned_agent_id = serializers.PrimaryKeyRelatedField(
        queryset=VoiceAgent.objects.all(), write_only=True, required=False, allow_null=True
    )
    company_logo = serializers.ImageField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "role_name", "permissions", "assigned_agent_id", "company_logo"]

    def create(self, validated_data):
        role_name = validated_data.pop("role_name", None)
        permissions = validated_data.pop("permissions", None)
        assigned_agent = validated_data.pop("assigned_agent_id", None)
        company_logo = validated_data.pop("company_logo", None)
        user = User.objects.create_user(**validated_data)
        
        # If a role name is provided, get or create it with the specified permissions
        if role_name:
            role, created = Role.objects.get_or_create(name=role_name)
            if created and permissions is not None:
                role.permissions = permissions
                role.save()
            user.profile.role = role
        
        # We also assign the permissions as custom_permissions to the user directly, 
        # just in case the role existed but had different permissions, ensuring this user gets what was checked.
        if permissions is not None:
            user.profile.custom_permissions = permissions
            
        if assigned_agent:
            user.profile.assigned_agent = assigned_agent
            
        if company_logo:
            user.profile.company_logo = company_logo
            
        user.profile.save()
        return user