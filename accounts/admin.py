from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, Role, RolePermission


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission", "is_active", "granted_at", "granted_by")
    list_filter = ("is_active", "role", "granted_at")
    search_fields = ("role__name", "permission__name", "permission__codename")
    raw_id_fields = ("role", "permission", "granted_by")
    readonly_fields = ("granted_at",)


class RolePermissionInline(admin.TabularInline):
    """Inline admin for managing role permissions."""
    model = RolePermission
    extra = 1
    fields = ("permission", "is_active", "granted_at", "granted_by")
    readonly_fields = ("granted_at",)
    autocomplete_fields = ("permission", "granted_by")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "permission_count")
    search_fields = ("name", "code")
    inlines = [RolePermissionInline]
    
    def permission_count(self, obj):
        """Display count of active permissions for this role."""
        return obj.role_permissions.filter(is_active=True).count()
    permission_count.short_description = "Active Permissions"



@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "tenant", "role", "is_tenant_admin", "is_active")
    list_filter = ("tenant", "role", "is_tenant_admin", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Tenant", {"fields": ("tenant", "role", "is_tenant_admin")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "tenant", "role", "is_tenant_admin", "password1", "password2"),
            },
        ),
    )
