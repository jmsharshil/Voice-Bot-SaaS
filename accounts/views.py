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



def login_page(request):
    return render(request, "login.html")

def signup_page(request):
    return render(request, "signup.html")

def admin_management_page(request):
    return render(request, "admin_management.html")