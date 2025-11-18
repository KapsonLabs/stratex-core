from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Module(models.Model):
    """Feature module that can be enabled via a licence for a tenant."""

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class SubModule(models.Model):
    """A submodule of a module."""
    
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="submodules")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["module__code", "name"]
        
    def __str__(self) -> str:
        return f"{self.module.code} - {self.name}"


class SystemModulePermission(models.Model):
    """
    Permission model to define granular permissions in the system.
    Permissions are actions that can be performed on resources.
    """
    
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('read', 'Read'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('export', 'Export'),
        ('import', 'Import'),
    ]
    
    name = models.CharField(max_length=150, help_text="Human-readable name, e.g. 'Create Product'")
    codename = models.CharField(max_length=120, unique=True, help_text="Machine code, e.g. 'product_create'")
    description = models.TextField(blank=True, help_text="Description of what this permission allows")
    resource = models.ForeignKey("tenants.SubModule", on_delete=models.PROTECT, related_name="permissions")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, help_text="The action this permission allows")
    is_active = models.BooleanField(default=True, help_text="Whether this permission is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('permission')
        verbose_name_plural = _('permissions')
        ordering = ['resource__name', 'action']
        unique_together = [['resource', 'action']]
        indexes = [
            models.Index(fields=["resource", "action"]),
            models.Index(fields=["codename"]),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.resource}.{self.action})"
    
    def save(self, *args, **kwargs):
        # Auto-generate codename if not provided, using resource name
        if not self.codename and self.resource_id:
            resource_slug = slugify(self.resource.name).replace('-', '_')
            self.codename = f"{resource_slug}_{self.action}"
        # Auto-generate name if not provided, using resource.name
        if not self.name and self.resource_id:
            self.name = f"{self.action.title()} {self.resource.name}"
        super().save(*args, **kwargs)


class Licence(models.Model):
    """Commercial licence attached to a tenant, controlling access and limits."""

    name = models.CharField(max_length=128)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    max_users = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Licence"
        verbose_name_plural = "Licences"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class LicenceModule(models.Model):
    licence = models.ForeignKey(Licence, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("licence", "module")

    def __str__(self) -> str:
        return f"{self.licence} -> {self.module}"


class Tenant(models.Model):
    """A customer organization (tenant)."""

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    licence = models.ForeignKey(Licence, on_delete=models.PROTECT, related_name="tenants")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    def has_module_enabled(self, module_code: str) -> bool:
        if not self.licence or not self.licence.is_active:
            return False
        return self.licence.modules.filter(code=module_code).exists()


class TenantSettings(models.Model):
    """Per-tenant settings managed by the tenant's admin user."""

    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="settings")
    timezone = models.CharField(max_length=64, default="UTC")
    locale = models.CharField(max_length=16, default="en-US")
    theme = models.CharField(max_length=32, default="light")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "Tenant settings"

    def __str__(self) -> str:
        return f"Settings for {self.tenant.name}"
