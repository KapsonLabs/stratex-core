from rest_framework import serializers

from .models import Role, User, RolePermission
from tenants.models import SystemModulePermission


class RolePermissionSerializer(serializers.ModelSerializer):
    """Serializer for RolePermission."""
    permission_name = serializers.CharField(source="permission.name", read_only=True)
    permission_codename = serializers.CharField(source="permission.codename", read_only=True)
    
    class Meta:
        model = RolePermission
        fields = ["id", "permission", "permission_name", "permission_codename", "is_active", "granted_at", "granted_by"]
        read_only_fields = ["granted_at"]


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role with permissions managed through RolePermission."""
    permissions = RolePermissionSerializer(source="role_permissions", many=True, read_only=True)
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of SystemModulePermission IDs to assign to this role"
    )
    
    class Meta:
        model = Role
        fields = ["id", "name", "code", "is_active", "permissions", "permission_ids"]
    
    def create(self, validated_data):
        permission_ids = validated_data.pop("permission_ids", [])
        role = Role.objects.create(**validated_data)
        
        # Create RolePermission entries for each permission ID
        if permission_ids:
            request = self.context.get("request")
            granted_by = request.user if request and hasattr(request, "user") and request.user.is_authenticated else None
            
            RolePermission.objects.bulk_create([
                RolePermission(
                    role=role,
                    permission_id=perm_id,
                    is_active=True,
                    granted_by=granted_by
                )
                for perm_id in permission_ids
            ])
        
        return role
    
    def update(self, instance, validated_data):
        permission_ids = validated_data.pop("permission_ids", None)
        
        # Update role fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update permissions if provided
        if permission_ids is not None:
            # Get current permission IDs
            current_permission_ids = set(
                instance.role_permissions.filter(is_active=True).values_list("permission_id", flat=True)
            )
            new_permission_ids = set(permission_ids)
            
            # Remove permissions that are no longer in the list
            to_remove = current_permission_ids - new_permission_ids
            if to_remove:
                instance.role_permissions.filter(permission_id__in=to_remove).update(is_active=False)
            
            # Add new permissions
            to_add = new_permission_ids - current_permission_ids
            if to_add:
                request = self.context.get("request")
                granted_by = request.user if request and hasattr(request, "user") and request.user.is_authenticated else None
                
                RolePermission.objects.bulk_create([
                    RolePermission(
                        role=instance,
                        permission_id=perm_id,
                        is_active=True,
                        granted_by=granted_by
                    )
                    for perm_id in to_add
                ])
        
        return instance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id","username","email","first_name","last_name","tenant","role","is_tenant_admin","is_active","date_joined","last_login",
        ]
        read_only_fields = ["date_joined", "last_login"]


