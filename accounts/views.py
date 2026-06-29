# from django.shortcuts import render

# # Create your views here.
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from .serializers import RegisterSerializer


# class RegisterView(APIView):
#     def post(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": "User created"}, status=201)
#         return Response(serializer.errors, status=400)




from django.shortcuts import render
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Role, UserProfile
from .serializers import RegisterSerializer, RoleSerializer, UserSerializer

class IsSuperAdminOrAdmin(IsAuthenticated):
    """
    Custom permission to only allow admins to manage roles and users.
    Checks if the user's role has 'is_admin' permission.
    """
    def has_permission(self, request, view):
        is_auth = super().has_permission(request, view)
        if not is_auth:
            return False
        # If user is django superuser, always allow
        if request.user.is_superuser:
            return True
        # Check custom role permissions
        if hasattr(request.user, 'profile') and request.user.profile.role:
            perms = request.user.profile.role.permissions
            return perms.get('is_admin', False)
        return False
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class RegisterView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created successfully."}, status=201)
        return Response(serializer.errors, status=400)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    Custom login endpoint that distinguishes:
    - user_not_found  → user needs to sign up
    - wrong_password  → password is incorrect
    - success         → returns JWT tokens
    """
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")

    if not username or not password:
        return Response(
            {"error": "Username and password are required.", "code": "missing_fields"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if the user exists at all
    if not User.objects.filter(username=username).exists():
        return Response(
            {
                "error": f"No account found for '{username}'.",
                "code": "user_not_found",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # User exists — check credentials
    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {
                "error": "Incorrect password. Please try again.",
                "code": "wrong_password",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
    # Extract role and permissions
    role_name = None
    permissions = {}
    assigned_agent_id = None
    profile_picture_url = None
    company_logo_url = None

    if hasattr(user, 'profile'):
        if user.profile.role:
            role_name = user.profile.role.name
            permissions = dict(user.profile.role.permissions)
        
        # Merge custom permissions if they exist
        if user.profile.custom_permissions:
            permissions.update(user.profile.custom_permissions)

        if user.profile.assigned_agent:
            assigned_agent_id = str(user.profile.assigned_agent.id)
            
        if user.profile.profile_picture_url:
            profile_picture_url = user.profile.profile_picture_url
        elif user.profile.profile_picture:
            profile_picture_url = request.build_absolute_uri(user.profile.profile_picture.url)

        resolved_logo = user.profile.get_company_logo()
        if resolved_logo:
            if isinstance(resolved_logo, str):
                company_logo_url = resolved_logo
            else:
                company_logo_url = request.build_absolute_uri(resolved_logo.url)
    
    # Also default to is_admin=True if django superuser
    if user.is_superuser:
        permissions['is_admin'] = True

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "username": user.username,
            "email": user.email,
            "role": role_name,
            "permissions": permissions,
            "assigned_agent_id": assigned_agent_id,
            "is_superuser": user.is_superuser,
            "profile_picture": profile_picture_url,
            "company_logo": company_logo_url,
        },
        status=status.HTTP_200_OK,
    )

# --- Role Management (Admin only) ---

class RoleListView(generics.ListCreateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsSuperAdminOrAdmin]

class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsSuperAdminOrAdmin]

# --- User Management (Admin only) ---

class UserListView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperAdminOrAdmin]

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperAdminOrAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


# --- Client Team Management (For client admins managing their sub-users) ---

class TeamListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'profile') or not request.user.profile.assigned_agent:
            return Response({"error": "No voice bot assigned to your account."}, status=status.HTTP_400_BAD_REQUEST)
        
        profile = request.user.profile
        can_manage = profile.custom_permissions.get('can_manage_team', False) or (profile.role and profile.role.permissions.get('can_manage_team', False))
        if not can_manage:
            return Response({"error": "You do not have permission to manage team members."}, status=status.HTTP_403_FORBIDDEN)

        # Fetch other users with the same assigned agent (excluding current user and superusers)
        team_users = User.objects.filter(
            profile__assigned_agent=profile.assigned_agent
        ).exclude(id=request.user.id).exclude(is_superuser=True)

        serializer = UserSerializer(team_users, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not hasattr(request.user, 'profile') or not request.user.profile.assigned_agent:
            return Response({"error": "No voice bot assigned to your account."}, status=status.HTTP_400_BAD_REQUEST)

        profile = request.user.profile
        can_manage = profile.custom_permissions.get('can_manage_team', False) or (profile.role and profile.role.permissions.get('can_manage_team', False))
        if not can_manage:
            return Response({"error": "You do not have permission to manage team members."}, status=status.HTTP_403_FORBIDDEN)

        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        permissions = request.data.get("permissions", {})

        if not username or not password or not email:
            return Response({"error": "Username, email, and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        
        # Configure sub-user profile
        user.profile.assigned_agent = profile.assigned_agent
        user.profile.custom_permissions = {
            "can_view_leads": permissions.get("can_view_leads", False),
            "can_view_calls": permissions.get("can_view_calls", False),
            "can_view_campaigns": permissions.get("can_view_campaigns", False),
            "can_manage_team": permissions.get("can_manage_team", False)
        }
        # Inherit role (e.g. Kia Client/Hospital Client) but ensure they can't manage team
        user.profile.role = profile.role
        user.profile.created_by = request.user
        user.profile.save()

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class TeamDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        if not hasattr(request.user, 'profile') or not request.user.profile.assigned_agent:
            return Response({"error": "No voice bot assigned to your account."}, status=status.HTTP_400_BAD_REQUEST)

        profile = request.user.profile
        can_manage = profile.custom_permissions.get('can_manage_team', False) or (profile.role and profile.role.permissions.get('can_manage_team', False))
        if not can_manage:
            return Response({"error": "You do not have permission to manage team members."}, status=status.HTTP_403_FORBIDDEN)

        # Only allow modifying users assigned to the same agent
        user_to_edit = User.objects.filter(
            id=pk,
            profile__assigned_agent=profile.assigned_agent
        ).first()

        if not user_to_edit:
            return Response({"error": "Team member not found or does not belong to your bot's scope."}, status=status.HTTP_404_NOT_FOUND)

        if user_to_edit.id == request.user.id:
            return Response({"error": "You cannot edit your own permissions/details via this endpoint."}, status=status.HTTP_400_BAD_REQUEST)

        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        permissions = request.data.get("permissions", {})

        if username:
            if User.objects.filter(username=username).exclude(id=pk).exists():
                return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
            user_to_edit.username = username
        
        if email:
            user_to_edit.email = email

        if password:
            user_to_edit.set_password(password)

        user_to_edit.save()

        # Update permissions
        if "can_view_leads" in permissions or "can_view_calls" in permissions or "can_view_campaigns" in permissions or "can_manage_team" in permissions:
            if not user_to_edit.profile.custom_permissions:
                user_to_edit.profile.custom_permissions = {}
            if "can_view_leads" in permissions:
                user_to_edit.profile.custom_permissions["can_view_leads"] = permissions.get("can_view_leads", False)
            if "can_view_calls" in permissions:
                user_to_edit.profile.custom_permissions["can_view_calls"] = permissions.get("can_view_calls", False)
            if "can_view_campaigns" in permissions:
                user_to_edit.profile.custom_permissions["can_view_campaigns"] = permissions.get("can_view_campaigns", False)
            if "can_manage_team" in permissions:
                user_to_edit.profile.custom_permissions["can_manage_team"] = permissions.get("can_manage_team", False)
            user_to_edit.profile.save()

        serializer = UserSerializer(user_to_edit)
        return Response(serializer.data)

    def delete(self, request, pk):
        if not hasattr(request.user, 'profile') or not request.user.profile.assigned_agent:
            return Response({"error": "No voice bot assigned to your account."}, status=status.HTTP_400_BAD_REQUEST)

        profile = request.user.profile
        can_manage = profile.custom_permissions.get('can_manage_team', False) or (profile.role and profile.role.permissions.get('can_manage_team', False))
        if not can_manage:
            return Response({"error": "You do not have permission to delete team members."}, status=status.HTTP_403_FORBIDDEN)

        # Only allow deleting users assigned to the same agent
        user_to_delete = User.objects.filter(
            id=pk,
            profile__assigned_agent=profile.assigned_agent
        ).first()

        if not user_to_delete:
            return Response({"error": "Team member not found or does not belong to your bot's scope."}, status=status.HTTP_404_NOT_FOUND)

        if user_to_delete.id == request.user.id:
            return Response({"error": "You cannot delete yourself."}, status=status.HTTP_400_BAD_REQUEST)

        user_to_delete.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UploadProfilePictureView(APIView):
    permission_classes = [IsAuthenticated]
    from rest_framework.parsers import MultiPartParser, FormParser
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not hasattr(request.user, 'profile'):
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        
        file_obj = request.FILES.get('profile_picture')
        if not file_obj:
            return Response({"error": "No image file provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        profile = request.user.profile
        profile.profile_picture = file_obj
        profile.save()
        
        image_url = request.build_absolute_uri(profile.profile_picture.url)
        return Response({
            "message": "Profile picture updated successfully.",
            "profile_picture": image_url
        }, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role_name = None
        permissions = {}
        assigned_agent_id = None
        profile_picture_url = None
        company_logo_url = None
        if hasattr(user, 'profile'):
            if user.profile.role:
                role_name = user.profile.role.name
                permissions = dict(user.profile.role.permissions)
            
            if user.profile.custom_permissions:
                permissions.update(user.profile.custom_permissions)

            if user.profile.assigned_agent:
                assigned_agent_id = str(user.profile.assigned_agent.id)

            if user.profile.profile_picture_url:
                profile_picture_url = user.profile.profile_picture_url
            elif user.profile.profile_picture:
                profile_picture_url = request.build_absolute_uri(user.profile.profile_picture.url)

            resolved_logo = user.profile.get_company_logo()
            if resolved_logo:
                if isinstance(resolved_logo, str):
                    company_logo_url = resolved_logo
                else:
                    company_logo_url = request.build_absolute_uri(resolved_logo.url)

        if user.is_superuser:
            permissions['is_admin'] = True

        return Response({
            "username": user.username,
            "email": user.email,
            "role": role_name,
            "permissions": permissions,
            "assigned_agent_id": assigned_agent_id,
            "is_superuser": user.is_superuser,
            "profile_picture": profile_picture_url,
            "company_logo": company_logo_url,
        }, status=status.HTTP_200_OK)


def login_page(request):
    return render(request, "login.html")

def signup_page(request):
    return render(request, "signup.html")

def admin_management_page(request):
    return render(request, "admin_management.html")

def team_management_page(request):
    return render(request, "team_management.html")


# --- Forgot / Reset Password ---

import uuid
from django.core.mail import send_mail
from django.conf import settings as django_settings

# In-memory token store (token → {user_id, created_at})
_password_reset_tokens = {}

@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password_view(request):
    """
    Accepts email, looks up the user, generates a token, and sends a reset link.
    """
    email = request.data.get("email", "").strip()
    if not email:
        return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"error": "No account found with this email address."}, status=status.HTTP_404_NOT_FOUND)

    # Generate a unique token
    token = str(uuid.uuid4())
    from django.utils import timezone
    _password_reset_tokens[token] = {
        "user_id": user.id,
        "created_at": timezone.now(),
    }

    # Build the reset link
    reset_url = request.build_absolute_uri(f"/accounts/reset-password/?token={token}")

    # Premium HTML template
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f3f4f6;
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
        }
        .email-wrapper {
            width: 100%;
            background-color: #f3f4f6;
            padding: 40px 0;
        }
        .email-card {
            max-width: 540px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            border: 1px solid #e5e7eb;
        }
        .email-header {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            padding: 32px;
            text-align: center;
        }
        .logo-text {
            color: #ffffff;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
            margin: 0;
        }
        .email-body {
            padding: 40px 32px;
            color: #1f2937;
        }
        .welcome-text {
            font-size: 18px;
            font-weight: 600;
            margin-top: 0;
            margin-bottom: 16px;
            color: #111827;
        }
        .instruction-text {
            font-size: 15px;
            line-height: 24px;
            color: #4b5563;
            margin-bottom: 32px;
        }
        .btn-wrapper {
            text-align: center;
            margin-bottom: 32px;
        }
        .btn-reset {
            display: inline-block;
            background-color: #4f46e5;
            color: #ffffff !important;
            text-decoration: none;
            padding: 14px 30px;
            font-size: 15px;
            font-weight: 600;
            border-radius: 10px;
            box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2), 0 2px 4px -1px rgba(79, 70, 229, 0.1);
        }
        .link-text {
            font-size: 12px;
            color: #9ca3af;
            line-height: 18px;
            word-break: break-all;
            margin-top: 24px;
        }
        .link-url {
            color: #4f46e5;
            text-decoration: none;
        }
        .email-footer {
            background-color: #f9fafb;
            padding: 24px 32px;
            border-top: 1px solid #f3f4f6;
            text-align: center;
            font-size: 13px;
            color: #6b7280;
        }
        .warning-text {
            font-size: 12px;
            color: #9ca3af;
            margin-top: 0;
            line-height: 18px;
        }
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-card">
            <div class="email-header">
                <h1 class="logo-text">AI SalesBot</h1>
            </div>
            <div class="email-body">
                <p class="welcome-text">Hi {username},</p>
                <p class="instruction-text">
                    We received a request to reset the password for your AI SalesBot account. 
                    Click the button below to set a new password. This link will expire in 1 hour.
                </p>
                <div class="btn-wrapper">
                    <a href="{reset_url}" class="btn-reset" target="_blank">Reset Password</a>
                </div>
                <p class="warning-text">
                    If you did not request a password reset, you can safely ignore this email — your account remains secure.
                </p>
                <hr style="border: 0; border-top: 1px solid #f3f4f6; margin: 24px 0;">
                <p class="link-text">
                    If the button above doesn't work, copy and paste this link into your web browser:<br>
                    <a href="{reset_url}" class="link-url">{reset_url}</a>
                </p>
            </div>
            <div class="email-footer">
                &copy; 2026 AI SalesBot Team. All rights reserved.
            </div>
        </div>
    </div>
</body>
</html>
"""

    html_message = html_content.replace("{username}", user.username).replace("{reset_url}", reset_url)
    plain_message = f"Hi {user.username},\n\nYou requested a password reset. Click the link below to set a new password:\n\n{reset_url}\n\nThis link expires in 1 hour.\n\nIf you didn't request this, ignore this email.\n\n— AI SalesBot Team"

    # Send email
    try:
        send_mail(
            subject="Password Reset — AI SalesBot",
            message=plain_message,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        return Response({"error": f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"message": "Password reset link has been sent to your email."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password_view(request):
    """
    Accepts token and new_password. Resets the user's password. No validation.
    """
    token = request.data.get("token", "").strip()
    new_password = request.data.get("new_password", "")

    if not token or not new_password:
        return Response({"error": "Token and new password are required."}, status=status.HTTP_400_BAD_REQUEST)

    token_data = _password_reset_tokens.get(token)
    if not token_data:
        return Response({"error": "Invalid or expired reset token."}, status=status.HTTP_400_BAD_REQUEST)

    # Check token expiry (1 hour)
    from django.utils import timezone
    elapsed = (timezone.now() - token_data["created_at"]).total_seconds()
    if elapsed > 3600:
        del _password_reset_tokens[token]
        return Response({"error": "This reset link has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(id=token_data["user_id"]).first()
    if not user:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    user.set_password(new_password)
    user.save()

    # Invalidate the token
    del _password_reset_tokens[token]

    return Response({"message": "Your password has been reset successfully."}, status=status.HTTP_200_OK)


def forgot_password_page(request):
    return render(request, "forgot_password.html")

def reset_password_page(request):
    return render(request, "reset_password.html")