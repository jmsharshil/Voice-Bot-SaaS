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

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions"]

class UserProfileSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source="role", write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = UserProfile
        fields = ["role", "role_id", "custom_permissions"]

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source="profile.role", write_only=True, required=False, allow_null=True
    )

    custom_permissions = serializers.JSONField(source="profile.custom_permissions", write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "profile", "role_id", "custom_permissions"]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        if 'role' in profile_data:
            instance.profile.role = profile_data['role']
        if 'custom_permissions' in profile_data:
            instance.profile.custom_permissions = profile_data['custom_permissions']
        instance.profile.save()
        return super().update(instance, validated_data)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "role_id"]

    def create(self, validated_data):
        role = validated_data.pop("role_id", None)
        user = User.objects.create_user(**validated_data)
        if role:
            # profile is auto-created by signals, so we just update it
            user.profile.role = role
            user.profile.save()
        return user