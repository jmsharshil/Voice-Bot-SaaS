# from django.urls import path
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# from .views import RegisterView

# urlpatterns = [
#     path("register/", RegisterView.as_view()),
#     path("login/", TokenObtainPairView.as_view()),
#     path("token/refresh/", TokenRefreshView.as_view()),
# ]









from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, login_view, login_page, admin_management_page,
    RoleListView, RoleDetailView, UserListView, UserDetailView,
    TeamListView, TeamDetailView, team_management_page,
    forgot_password_view, reset_password_view,
    forgot_password_page, reset_password_page,
    UploadProfilePictureView, CurrentUserView
)

urlpatterns = [
    # Pages
    path("login/", login_page, name="login"),
    path("admin-management/", admin_management_page, name="admin-management"),
    path("team-management/", team_management_page, name="team-management"),
    path("forgot-password/", forgot_password_page, name="forgot-password"),
    path("reset-password/", reset_password_page, name="reset-password"),

    # Auth APIs
    path("register/", RegisterView.as_view(), name="register"),
    path("login-api/", login_view, name="login-api"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("forgot-password-api/", forgot_password_view, name="forgot-password-api"),
    path("reset-password-api/", reset_password_view, name="reset-password-api"),
    path("profile/upload-picture/", UploadProfilePictureView.as_view(), name="profile-upload-picture"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    
    # Admin / Role Management APIs
    path("roles/", RoleListView.as_view(), name="role-list"),
    path("roles/<int:pk>/", RoleDetailView.as_view(), name="role-detail"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),

    # Client Team Management APIs
    path("team/", TeamListView.as_view(), name="team-list"),
    path("team/<int:pk>/", TeamDetailView.as_view(), name="team-detail"),
]