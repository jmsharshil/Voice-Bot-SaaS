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
class RegisterView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

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
    if hasattr(user, 'profile'):
        if user.profile.role:
            role_name = user.profile.role.name
            permissions = dict(user.profile.role.permissions)
        
        # Merge custom permissions if they exist
        if user.profile.custom_permissions:
            permissions.update(user.profile.custom_permissions)

        if user.profile.assigned_agent:
            assigned_agent_id = str(user.profile.assigned_agent.id)
    
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
            "can_manage_team": False
        }
        # Inherit role (e.g. Kia Client/Hospital Client) but ensure they can't manage team
        user.profile.role = profile.role
        user.profile.created_by = request.user
        user.profile.save()

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class TeamDetailView(APIView):
    permission_classes = [IsAuthenticated]

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


def login_page(request):
    return render(request, "login.html")

def signup_page(request):
    return render(request, "signup.html")

def admin_management_page(request):
    return render(request, "admin_management.html")

def team_management_page(request):
    return render(request, "team_management.html")