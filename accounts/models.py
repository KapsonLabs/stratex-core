from django.db import models
from django.contrib.auth.models import AbstractUser, Permission


class Role(models.Model):
    """Tenant-scoped role that aggregates Django and custom permissions."""

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("code",)
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name

    def has_permission_code(self, module_code: str, permission_code: str) -> bool:
        # permission_code expected to be the ModulePermission.codename or action; support both
        # Check through RolePermission relationship
        # First check codename exact match on resource (using module code from SubModule's module)
        if self.role_permissions.filter(
            permission__resource__module__code=module_code, 
            permission__codename=permission_code, 
            permission__is_active=True,
            is_active=True
        ).exists():
            return True
        # Fallback: if permission_code is an action (e.g., 'create'), check by action
        return self.role_permissions.filter(
            permission__resource__module__code=module_code, 
            permission__action=permission_code, 
            permission__is_active=True,
            is_active=True
        ).exists()
    
    def get_permissions(self):
        """Get all active permissions for this role."""
        from tenants.models import SystemModulePermission
        return SystemModulePermission.objects.filter(
            role_permissions__role=self,
            role_permissions__is_active=True,
            is_active=True
        ).distinct()
        

class RolePermission(models.Model):
    """Explicit through table tracking permissions assigned to roles."""
    
    role = models.ForeignKey("Role", on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey("tenants.SystemModulePermission", on_delete=models.CASCADE, related_name="role_permissions")
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="granted_permissions")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = [["role", "permission"]]
        ordering = ["role", "permission"]
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"
        indexes = [
            models.Index(fields=["role", "permission"]),
            models.Index(fields=["role", "is_active"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.role.name} - {self.permission.name}"



class User(AbstractUser):
    """Custom user scoped to a tenant with a single role assignment."""

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="users", null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="users", null=True, blank=True)
    organization = models.ForeignKey("strategy.Organization", on_delete=models.PROTECT, related_name="users", null=True, blank=True)
    is_tenant_admin = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "email"], name="uniq_tenant_email"),
        ]

    def has_perm(self, perm, obj=None):
        # Superuser short-circuit
        if self.is_superuser:
            return True

        # Delegate to default for model-level perms attached directly to user/groups
        base_has = super().has_perm(perm, obj=obj)
        if base_has:
            return True

        # Check role-based permissions through RolePermission
        if not self.role_id:
            return False

        try:
            app_label, codename = perm.split(".")
        except ValueError:
            # Invalid perm format; deny
            return False

        # Note: SystemModulePermission is separate from Django's Permission model
        # For Django permissions, check user's direct permissions or groups
        # Custom RBAC permissions are checked via has_permission_code method
        return False

    def has_module_perms(self, app_label):
        if self.is_superuser:
            return True
        if super().has_module_perms(app_label):
            return True
        if not self.role_id:
            return False
        # Note: SystemModulePermission is separate from Django's Permission model
        # For Django module permissions, check user's direct permissions or groups
        # Custom RBAC permissions are checked via has_permission_code method
        return False

    # Custom RBAC check using RolePermission
    def has_permission_code(self, module_code: str, permission_code: str) -> bool:
        if self.is_superuser:
            return True
        if not self.is_active or not self.role_id or not self.tenant_id:
            return False
        # Gate by licence-enabled module
        if not self.tenant.has_module_enabled(module_code):
            return False
        return self.role.has_permission_code(module_code, permission_code)
