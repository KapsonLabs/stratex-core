from django.urls import path

from .views import (
    ModuleListCreateAPIView,
    ModuleDetailAPIView,
    ModuleStatusAPIView,
    ModulePermissionListCreateAPIView,
    ModulePermissionDetailAPIView,
    ModulePermissionStatusAPIView,
    LicenceListCreateAPIView,
    LicenceDetailAPIView,
    LicenceStatusAPIView,
    TenantListCreateAPIView,
    TenantDetailAPIView,
    TenantStatusAPIView,
)


urlpatterns = [
    # Modules
    path("modules/", ModuleListCreateAPIView.as_view(), name="module-list"),
    path("modules/<int:pk>/", ModuleDetailAPIView.as_view(), name="module-detail"),
    path("modules/<int:pk>/status/", ModuleStatusAPIView.as_view(), name="module-status"),

    # Module permissions
    path("module-permissions/", ModulePermissionListCreateAPIView.as_view(), name="module-permission-list"),
    path("module-permissions/<int:pk>/", ModulePermissionDetailAPIView.as_view(), name="module-permission-detail"),
    path("module-permissions/<int:pk>/status/", ModulePermissionStatusAPIView.as_view(), name="module-permission-status"),

    # Licences
    path("licences/", LicenceListCreateAPIView.as_view(), name="licence-list"),
    path("licences/<int:pk>/", LicenceDetailAPIView.as_view(), name="licence-detail"),
    path("licences/<int:pk>/status/", LicenceStatusAPIView.as_view(), name="licence-status"),

    # Tenants
    path("tenants/", TenantListCreateAPIView.as_view(), name="tenant-list"),
    path("tenants/<int:pk>/", TenantDetailAPIView.as_view(), name="tenant-detail"),
    path("tenants/<int:pk>/status/", TenantStatusAPIView.as_view(), name="tenant-status"),
]


