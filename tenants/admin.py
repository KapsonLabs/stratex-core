from django.contrib import admin

from .models import Module, SubModule, Licence, LicenceModule, Tenant, TenantSettings, SystemModulePermission


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(SubModule)
class SubModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "module", "is_active")
    list_filter = ("module", "is_active")
    search_fields = ("name", "description")


class LicenceModuleInline(admin.TabularInline):
    model = LicenceModule
    extra = 0


@admin.register(Licence)
class LicenceAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "start_date", "end_date", "max_users")
    list_filter = ("is_active",)
    search_fields = ("name",)
    inlines = [LicenceModuleInline]


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "licence", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    list_display = ("tenant", "timezone", "locale", "theme")


@admin.register(SystemModulePermission)
class SystemModulePermissionAdmin(admin.ModelAdmin):
    list_display = ("name", "codename", "resource", "action", "is_active")
    list_filter = ("resource", "action", "is_active")
    search_fields = ("name", "codename", "description")
    autocomplete_fields = ("resource",)
