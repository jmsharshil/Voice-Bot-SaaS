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




from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import render
from django.contrib.auth import authenticate, login as django_login
from django.contrib.auth.models import User

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated

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
@authentication_classes([])
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

    # Check if the user exists at all (case-insensitive lookup)
    user_obj = User.objects.filter(username__iexact=username).first()
    if not user_obj:
        return Response(
            {
                "error": f"No account found for '{username}'.",
                "code": "user_not_found",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # User exists — check credentials using exact DB username
    user = authenticate(username=user_obj.username, password=password)
    if user is None:
        return Response(
            {
                "error": "Incorrect password. Please try again.",
                "code": "wrong_password",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Establish Django session for page navigations
    try:
        django_login(request, user)
    except Exception:
        pass

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

    # Determine if user is Ice Make specific user
    is_icemake_user = False
    if role_name and "ice make" in role_name.lower():
        is_icemake_user = True
    elif user.username.lower() in ["icemake", "ice_make", "icemake_admin", "icemake_user"]:
        is_icemake_user = True
    elif hasattr(user, 'profile') and user.profile and user.profile.assigned_agent and "ice make" in user.profile.assigned_agent.name.lower():
        is_icemake_user = True

    # Determine if user is Sarvam specific user
    is_sarvam_user = False
    assigned_sarvam_agents = []
    if hasattr(user, 'profile') and user.profile:
        assigned_agents_qs = user.profile.assigned_sarvam_agents.filter(is_active=True)
        # Inherit from creator if not set on sub-user directly
        if not assigned_agents_qs.exists() and user.profile.created_by and hasattr(user.profile.created_by, 'profile'):
            creator_profile = user.profile.created_by.profile
            creator_agents = creator_profile.assigned_sarvam_agents.filter(is_active=True)
            if creator_agents.exists():
                user.profile.assigned_sarvam_agents.set(creator_agents.all())
                assigned_agents_qs = user.profile.assigned_sarvam_agents.filter(is_active=True)

        if assigned_agents_qs.exists():
            is_sarvam_user = True
            assigned_sarvam_agents = [
                {"id": a.id, "name": a.name, "slug": a.slug, "phone": a.agent_phone}
                for a in assigned_agents_qs
            ]

    if role_name and "sarvam" in role_name.lower():
        is_sarvam_user = True
    elif user.username.lower().startswith("sarvam") or "sarvam" in user.username.lower():
        is_sarvam_user = True
    elif permissions.get("is_sarvam_user") or permissions.get("can_view_sarvam"):
        is_sarvam_user = True
    elif hasattr(user, 'profile') and user.profile and user.profile.created_by:
        is_sarvam_user = True

    # If user is superuser and no specific Sarvam agents are assigned, provide all active Sarvam agents
    if user.is_superuser and not assigned_sarvam_agents:
        try:
            from conversations.models import SarvamAgent
            all_s_agents = SarvamAgent.objects.filter(is_active=True)
            assigned_sarvam_agents = [
                {"id": a.id, "name": a.name, "slug": a.slug, "phone": a.agent_phone}
                for a in all_s_agents
            ]
        except Exception:
            pass

    primary_sarvam_slug = (
        assigned_sarvam_agents[0]["slug"]
        if assigned_sarvam_agents
        else None
    )

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "username": user.username,
            "email": user.email,
            "role": role_name,
            "permissions": permissions,
            "assigned_agent_id": assigned_agent_id,
            "assigned_sarvam_agents": assigned_sarvam_agents,
            "primary_sarvam_slug": primary_sarvam_slug,
            "is_superuser": user.is_superuser,
            "is_icemake_user": is_icemake_user,
            "is_sarvam_user": is_sarvam_user,
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


def check_can_manage_team(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'profile', None)
    if not profile:
        return False
    if isinstance(profile.custom_permissions, dict) and "can_manage_team" in profile.custom_permissions:
        return bool(profile.custom_permissions.get("can_manage_team"))
    if profile.role and isinstance(profile.role.permissions, dict) and profile.role.permissions.get("can_manage_team"):
        return True
    if profile.created_by is None:
        return True
    return False


# --- Client Team Management (For client admins managing their sub-users) ---

class TeamListView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not check_can_manage_team(request.user):
            return Response({"error": "You do not have permission to manage team members."}, status=status.HTTP_403_FORBIDDEN)

        profile = getattr(request.user, 'profile', None)
        # Fetch users created by request.user or sharing assigned_agent / assigned_sarvam_agents
        from django.db.models import Q
        q_filter = Q(profile__created_by=request.user)
        if profile and profile.assigned_agent:
            q_filter |= Q(profile__assigned_agent=profile.assigned_agent)
        if profile and profile.assigned_sarvam_agents.exists():
            q_filter |= Q(profile__assigned_sarvam_agents__in=profile.assigned_sarvam_agents.all())

        if request.user.is_superuser:
            team_users = User.objects.exclude(id=request.user.id).order_by('-date_joined')
        else:
            team_users = User.objects.filter(q_filter).exclude(id=request.user.id).exclude(is_superuser=True).distinct().order_by('-date_joined')

        serializer = UserSerializer(team_users, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not check_can_manage_team(request.user):
            return Response({"error": "You do not have permission to manage team members."}, status=status.HTTP_403_FORBIDDEN)

        profile = getattr(request.user, 'profile', None)
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
        if profile:
            user.profile.assigned_agent = profile.assigned_agent
            if profile.assigned_sarvam_agents.exists():
                user.profile.assigned_sarvam_agents.set(profile.assigned_sarvam_agents.all())
            elif profile.created_by and profile.created_by.profile.assigned_sarvam_agents.exists():
                user.profile.assigned_sarvam_agents.set(profile.created_by.profile.assigned_sarvam_agents.all())
            user.profile.role = profile.role

        p_manage = permissions.get("can_manage_team", False)
        p_campaigns = permissions.get("can_view_campaigns", False) or p_manage
        p_leads = permissions.get("can_view_leads", True) or p_campaigns or p_manage
        assigned_stores = permissions.get("assigned_stores", [])

        user.profile.custom_permissions = {
            "can_view_leads": p_leads,
            "can_view_calls": p_leads,
            "can_view_campaigns": p_campaigns,
            "can_manage_team": p_manage,
            "assigned_stores": assigned_stores
        }
        user.profile.created_by = request.user
        user.profile.save()

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class TeamDetailView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        if not check_can_manage_team(request.user):
            return Response({"error": "You do not have permission to manage team members."}, status=status.HTTP_403_FORBIDDEN)

        profile = getattr(request.user, 'profile', None)
        if request.user.is_superuser:
            user_to_edit = User.objects.filter(id=pk).first()
        else:
            from django.db.models import Q
            q_filter = Q(profile__created_by=request.user)
            if profile and profile.assigned_agent:
                q_filter |= Q(profile__assigned_agent=profile.assigned_agent)
            if profile and profile.assigned_sarvam_agents.exists():
                q_filter |= Q(profile__assigned_sarvam_agents__in=profile.assigned_sarvam_agents.all())
            user_to_edit = User.objects.filter(Q(id=pk) & q_filter).first()

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
        if any(k in permissions for k in ["can_view_leads", "can_view_calls", "can_view_campaigns", "can_manage_team", "assigned_stores"]):
            p_manage = permissions.get("can_manage_team", False)
            p_campaigns = permissions.get("can_view_campaigns", False) or p_manage
            p_leads = permissions.get("can_view_leads", True) or p_campaigns or p_manage
            assigned_stores = permissions.get("assigned_stores", user_to_edit.profile.custom_permissions.get("assigned_stores", []))

            user_to_edit.profile.custom_permissions = {
                "can_view_leads": p_leads,
                "can_view_calls": p_leads,
                "can_view_campaigns": p_campaigns,
                "can_manage_team": p_manage,
                "assigned_stores": assigned_stores
            }
            user_to_edit.profile.save()

        serializer = UserSerializer(user_to_edit)
        return Response(serializer.data)

    def delete(self, request, pk):
        if not check_can_manage_team(request.user):
            return Response({"error": "You do not have permission to delete team members."}, status=status.HTTP_403_FORBIDDEN)

        profile = getattr(request.user, 'profile', None)
        if request.user.is_superuser:
            user_to_delete = User.objects.filter(id=pk).first()
        else:
            from django.db.models import Q
            q_filter = Q(profile__created_by=request.user)
            if profile and profile.assigned_agent:
                q_filter |= Q(profile__assigned_agent=profile.assigned_agent)
            if profile and profile.assigned_sarvam_agents.exists():
                q_filter |= Q(profile__assigned_sarvam_agents__in=profile.assigned_sarvam_agents.all())
            user_to_delete = User.objects.filter(Q(id=pk) & q_filter).first()

        if not user_to_delete:
            return Response({"error": "Team member not found or does not belong to your scope."}, status=status.HTTP_404_NOT_FOUND)

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

        # 1. Strict extension check - image files only
        import os
        import time
        import uuid
        from django.conf import settings
        from PIL import Image

        name_lower = (file_obj.name or '').lower()
        ext = os.path.splitext(name_lower)[1]
        ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
        if ext not in ALLOWED_EXTENSIONS:
            return Response({
                "error": f"Invalid file type '{ext}'. Only image files (JPG, JPEG, PNG, WebP, GIF, BMP) are allowed."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 2. Strict MIME type check
        content_type = (file_obj.content_type or '').lower()
        ALLOWED_CONTENT_TYPES = {
            'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif', 'image/bmp', 'image/x-ms-bmp'
        }
        if content_type and content_type not in ALLOWED_CONTENT_TYPES and not content_type.startswith('image/'):
            return Response({
                "error": "Invalid content type. Only genuine image files are allowed."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 3. File size limit (10MB)
        MAX_SIZE = 10 * 1024 * 1024
        if file_obj.size > MAX_SIZE:
            return Response({
                "error": "Image file size exceeds the 10MB limit. Please upload a smaller image."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 4. Deep image verification with PIL (Pillow) to ensure real image data (not disguised script/malware)
        try:
            img = Image.open(file_obj)
            img.verify()
            file_obj.seek(0)
        except Exception:
            return Response({
                "error": "The uploaded file is corrupted or not a valid image file."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 5. Sanitize filename
        clean_filename = f"user_{request.user.id}_{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
        file_obj.name = clean_filename

        profile = request.user.profile

        # 6. Save through model (UserProfile.save automatically uploads to Azure Blob Storage on live server if configured)
        profile.profile_picture = file_obj
        profile.save()

        # 7. Resolve public URL: prefer Azure Blob URL if present, otherwise local media URL
        if profile.profile_picture_url and (profile.profile_picture_url.startswith("http://") or profile.profile_picture_url.startswith("https://")):
            image_url = profile.profile_picture_url
        elif profile.profile_picture and hasattr(profile.profile_picture, 'url'):
            image_url = request.build_absolute_uri(profile.profile_picture.url)
            profile.profile_picture_url = image_url
            profile.save(update_fields=['profile_picture_url'])
        else:
            image_url = profile.profile_picture_url or ''

        return Response({
            "message": "Profile picture updated successfully.",
            "profile_picture": image_url,
            "profile_picture_url": image_url
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

def support_page(request):
    return render(request, "support.html")

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from .models import SupportQuery

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # CSRF check bypassed for support API requests

class SupportSubmitView(APIView):
    authentication_classes = [JWTAuthentication, CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        """
        Returns all previous support queries submitted by the user,
        ordered chronologically with formatted local date and time.
        """
        user = request.user if (request.user and request.user.is_authenticated) else None
        email = (request.GET.get("email") or (user.email if user else "") or "").strip()
        username = (request.GET.get("username") or (user.username if user else "") or "").strip()

        filters = Q()
        if user:
            filters |= Q(user=user)
        if email:
            filters |= Q(email__iexact=email)
        if username and username != "Anonymous User":
            filters |= Q(username__iexact=username)

        if not filters:
            return Response({"queries": []}, status=status.HTTP_200_OK)

        records = SupportQuery.objects.filter(filters).distinct().order_by("created_at")
        queries_data = []
        for r in records:
            loc = timezone.localtime(r.created_at)
            queries_data.append({
                "id": r.id,
                "query": r.query,
                "date": loc.strftime("%d %b %Y"),
                "time": loc.strftime("%I:%M %p"),
                "datetime": loc.strftime("%d %b %Y, %I:%M %p"),
                "status": r.status,
                "email": r.email,
                "username": r.username,
            })
        return Response({"queries": queries_data}, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Stores user query in SupportQuery with date & time,
        dispatches email notification to support team,
        and returns the created query record with date & time.
        """
        query = (request.data.get("query") or request.data.get("description") or request.data.get("message") or "").strip()
        if not query:
            return Response({"error": "Please enter your query or issue description."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if (request.user and request.user.is_authenticated) else None
        username = (user.username if user else None) or request.data.get("username") or "Anonymous User"
        user_email = (request.data.get("email") or (user.email if user else "") or "").strip()
        user_phone = (request.data.get("phone") or (getattr(user, "phone_number", "") or getattr(user, "phone", "") if user else "") or "").strip()
        
        # Determine user role
        role_name = "User"
        if user:
            if getattr(user, "is_superuser", False):
                role_name = "Super Admin"
            elif hasattr(user, "profile") and user.profile.role:
                role_name = user.profile.role.name
            elif getattr(user, "is_staff", False):
                role_name = "Staff / Admin"
        else:
            role_name = request.data.get("role") or "User"

        # Persist to database with date and time
        support_record = SupportQuery.objects.create(
            user=user,
            username=username,
            email=user_email,
            phone=user_phone,
            role=role_name,
            query=query,
            status="received"
        )

        local_dt = timezone.localtime(support_record.created_at)
        submitted_at = local_dt.strftime("%d %b %Y, %I:%M %p IST")
        formatted_date = local_dt.strftime("%d %b %Y")
        formatted_time = local_dt.strftime("%I:%M %p")
        formatted_datetime = local_dt.strftime("%d %b %Y, %I:%M %p")

        recipient = getattr(settings, "SUPPORT_RECIPIENT_EMAIL", "testing251299@gmail.com")
        subject = f"[SUPPORT QUERY] from {username} ({role_name})"

        # Plain text fallback body
        body_text = (
            f"Hello Support Team,\n\n"
            f"A user has submitted a support query through their profile chatbox.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"USER DETAILS:\n"
            f"• Username: {username}\n"
            f"• Email: {user_email or 'Not Provided'}\n"
            f"• Phone: {user_phone or 'Not Provided'}\n"
            f"• Role: {role_name}\n"
            f"• Submitted At: {submitted_at}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"QUERY / MESSAGE:\n"
            f"{query}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"You can reply directly to this email to reach the user ({user_email}).\n"
        )

        # Rich HTML email body
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
                .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 16px rgba(0,0,0,0.06); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #ffffff; padding: 24px 30px; }}
                .header h2 {{ margin: 0; font-size: 20px; font-weight: 700; }}
                .header p {{ margin: 4px 0 0; opacity: 0.85; font-size: 13px; }}
                .content {{ padding: 28px 30px; }}
                .user-table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; background: #f8fafc; border-radius: 10px; overflow: hidden; }}
                .user-table td {{ padding: 10px 16px; font-size: 13.5px; border-bottom: 1px solid #edf2f7; }}
                .user-table td:first-child {{ font-weight: 600; color: #64748b; width: 35%; }}
                .user-table td:last-child {{ font-weight: 600; color: #0f172a; }}
                .query-box {{ background: #f1f5f9; border-left: 4px solid #4f46e5; border-radius: 8px; padding: 18px 20px; font-size: 14.5px; line-height: 1.6; color: #1e293b; white-space: pre-wrap; }}
                .footer {{ background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 30px; text-align: center; font-size: 12px; color: #94a3b8; }}
                .reply-banner {{ margin-top: 20px; padding: 12px; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; color: #065f46; font-size: 13px; text-align: center; font-weight: 500; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <h2>💬 New User Support Query</h2>
                    <p>Submitted via Profile Support Chatbox</p>
                </div>
                <div class="content">
                    <table class="user-table">
                        <tr><td>Username</td><td>{username}</td></tr>
                        <tr><td>Email Address</td><td><a href="mailto:{user_email}" style="color: #4f46e5; text-decoration: none;">{user_email or 'Not Provided'}</a></td></tr>
                        <tr><td>Phone Number</td><td>{user_phone or 'Not Provided'}</td></tr>
                        <tr><td>User Role</td><td>{role_name}</td></tr>
                        <tr><td>Submission Time</td><td>{submitted_at}</td></tr>
                    </table>

                    <h4 style="margin: 0 0 10px; color: #334155; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">User Query Details:</h4>
                    <div class="query-box">{query}</div>

                    {f'<div class="reply-banner">💡 Tip: You can reply directly to this email to contact <strong>{user_email}</strong>.</div>' if user_email and '@' in user_email else ''}
                </div>
                <div class="footer">
                    AI VoiceBot SaaS Platform • Automated Notification
                </div>
            </div>
        </body>
        </html>
        """

        try:
            reply_to_list = [user_email] if (user_email and "@" in user_email) else []
            email_msg = EmailMultiAlternatives(
                subject=subject,
                body=body_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
                reply_to=reply_to_list if reply_to_list else None
            )
            email_msg.attach_alternative(body_html, "text/html")

            # Check optional attachment
            image_file = request.FILES.get("image") or request.FILES.get("file")
            if image_file:
                email_msg.attach(image_file.name, image_file.read(), image_file.content_type)

            email_msg.send(fail_silently=False)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send support email: {e}")

        return Response({
            "status": "success",
            "message": "Your query has been sent to our support team. We will review it and reach out to you shortly.",
            "query": {
                "id": support_record.id,
                "query": support_record.query,
                "date": formatted_date,
                "time": formatted_time,
                "datetime": formatted_datetime,
                "email": support_record.email,
                "username": support_record.username,
                "status": support_record.status,
            }
        }, status=status.HTTP_200_OK)