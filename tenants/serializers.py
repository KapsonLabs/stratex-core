from rest_framework import serializers

from .models import Module, SubModule, SystemModulePermission, Licence, Tenant, TenantSettings


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ["id", "code", "name", "description", "is_active"]


class SystemModulePermissionSerializer(serializers.ModelSerializer):
    resource = serializers.SlugRelatedField(slug_field="name", queryset=SubModule.objects.all())

    class Meta:
        model = SystemModulePermission
        fields = ["id","name","codename","description","resource","action","is_active","created_at","updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class LicenceSerializer(serializers.ModelSerializer):
    modules = serializers.SlugRelatedField(slug_field="code", many=True, queryset=Module.objects.all())

    class Meta:
        model = Licence
        fields = ["id","name","modules","start_date","end_date","max_users","is_active","created_at","updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class TenantSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSettings
        fields = ["timezone", "locale", "theme", "metadata"]


class TenantSerializer(serializers.ModelSerializer):
    licence = serializers.PrimaryKeyRelatedField(queryset=Licence.objects.all())
    settings = TenantSettingsSerializer(required=False)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "slug",
            "licence",
            "is_active",
            "created_at",
            "updated_at",
            "settings",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def create(self, validated_data):
        settings_data = validated_data.pop("settings", None)
        tenant = Tenant.objects.create(**validated_data)
        if settings_data:
            TenantSettings.objects.create(tenant=tenant, **settings_data)
        return tenant

    def update(self, instance, validated_data):
        settings_data = validated_data.pop("settings", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if settings_data is not None:
            if hasattr(instance, "settings"):
                for attr, value in settings_data.items():
                    setattr(instance.settings, attr, value)
                instance.settings.save()
            else:
                TenantSettings.objects.create(tenant=instance, **settings_data)
        return instance


