from rest_framework import serializers

from .models import Role, User
from tenants.models import SystemModulePermission


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "code", "is_active", "permissions"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lazy import to avoid circular import
        # Set the queryset for the permissions field
        if "permissions" in self.fields:
            self.fields["permissions"].queryset = SystemModulePermission.objects.all()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id","username","email","first_name","last_name","tenant","role","is_tenant_admin","is_active","date_joined","last_login",
        ]
        read_only_fields = ["date_joined", "last_login"]


