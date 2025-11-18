from django.db import models
from django.contrib.auth.models import AbstractUser, Permission


class Role(models.Model):
    """Tenant-scoped role that aggregates Django and custom permissions."""

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=64)
    permissions = models.ManyToManyField("tenants.SystemModulePermission", blank=True, related_name="roles")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("code",)
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name

    def has_permission_code(self, module_code: str, permission_code: str) -> bool:
        # permission_code expected to be the ModulePermission.codename or action; support both
        # First check codename exact match on resource
        if self.permissions.filter(resource__code=module_code, codename=permission_code, is_active=True).exists():
            return True
        # Fallback: if permission_code is an action (e.g., 'create'), check by action
        return self.permissions.filter(resource__code=module_code, action=permission_code, is_active=True).exists()



class User(AbstractUser):
    """Custom user scoped to a tenant with a single role assignment."""

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="users", null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="users", null=True, blank=True)
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

        # Check role-based permissions
        if not self.role_id:
            return False

        try:
            app_label, codename = perm.split(".")
        except ValueError:
            # Invalid perm format; deny
            return False

        return self.role.permissions.filter(content_type__app_label=app_label, codename=codename).exists()

    def has_module_perms(self, app_label):
        if self.is_superuser:
            return True
        if super().has_module_perms(app_label):
            return True
        if not self.role_id:
            return False
        return self.role.permissions.filter(content_type__app_label=app_label).exists()

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
