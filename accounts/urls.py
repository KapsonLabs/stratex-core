from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RoleListCreateAPIView,
    RoleDetailAPIView,
    RoleStatusAPIView,
    UserListCreateAPIView,
    UserDetailAPIView,
    MyPermissionsAPIView,
    TenantAuthAPIView,
)


urlpatterns = [
    # JWT Authentication endpoints
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Custom Tenant Authentication
    path("auth/login/", TenantAuthAPIView.as_view(), name="tenant_auth"),

    # Roles
    path("roles/", RoleListCreateAPIView.as_view(), name="role-list"),
    path("roles/<int:pk>/", RoleDetailAPIView.as_view(), name="role-detail"),
    path("roles/<int:pk>/status/", RoleStatusAPIView.as_view(), name="role-status"),

    # Users
    path("users/", UserListCreateAPIView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailAPIView.as_view(), name="user-detail"),
    path("users/me/permissions/", MyPermissionsAPIView.as_view(), name="user-my-permissions"),
]


