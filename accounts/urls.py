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
    RoleListView, RoleDetailView, UserListView, UserDetailView
)

urlpatterns = [
    # Pages
    path("login/", login_page, name="login"),
    path("admin-management/", admin_management_page, name="admin-management"),


    # Auth APIs
    path("register/", RegisterView.as_view(), name="register"),
    path("login-api/", login_view, name="login-api"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    
    # Admin / Role Management APIs
    path("roles/", RoleListView.as_view(), name="role-list"),
    path("roles/<int:pk>/", RoleDetailView.as_view(), name="role-detail"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
]