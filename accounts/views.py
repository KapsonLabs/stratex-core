from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from tenants.models import SystemModulePermission, Tenant
from .models import Role, User
from .serializers import RoleSerializer, UserSerializer


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ["1", "true", "t", "yes", "y"]
    return False


class RoleListCreateAPIView(APIView):
    def get(self, request):
        queryset = Role.objects.all()
        serializer = RoleSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RoleDetailAPIView(APIView):
    def get(self, request, pk):
        obj = Role.objects.get(pk=pk)
        return Response(RoleSerializer(obj).data)

    def put(self, request, pk):
        obj = Role.objects.get(pk=pk)
        serializer = RoleSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = Role.objects.get(pk=pk)
        serializer = RoleSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = Role.objects.get(pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleStatusAPIView(APIView):
    def post(self, request, pk):
        obj = Role.objects.get(pk=pk)
        is_active = parse_bool(request.data.get("is_active"))
        obj.is_active = is_active
        obj.save(update_fields=["is_active"])
        return Response(RoleSerializer(obj).data)


class UserListCreateAPIView(APIView):
    def get(self, request):
        queryset = User.objects.all()
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserDetailAPIView(APIView):
    def get(self, request, pk):
        obj = User.objects.get(pk=pk)
        return Response(UserSerializer(obj).data)

    def put(self, request, pk):
        obj = User.objects.get(pk=pk)
        serializer = UserSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = User.objects.get(pk=pk)
        serializer = UserSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = User.objects.get(pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyPermissionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user: User = request.user
        perms_qs = SystemModulePermission.objects.filter(roles__users=user, is_active=True).select_related("resource")
        return Response([
            {
                "module": p.resource.code,
                "action": p.action,
                "codename": p.codename,
                "name": p.name,
            }
            for p in perms_qs
        ])


class TenantAuthAPIView(APIView):
    """
    Custom authentication endpoint that validates tenant-specific login.
    Expects: { "tenant_slug": "...", "username": "...", "password": "..." }
    Returns: User details + permissions + JWT tokens
    """

    def post(self, request):
        tenant_slug = request.data.get("tenant_slug")
        username = request.data.get("username")
        password = request.data.get("password")

        if not all([tenant_slug, username, password]):
            raise ValidationError({"detail": "tenant_slug, username, and password are required"})

        # Verify tenant exists and is active
        try:
            tenant = Tenant.objects.select_related("licence").get(slug=tenant_slug, is_active=True)
        except Tenant.DoesNotExist:
            raise AuthenticationFailed({"detail": "Invalid tenant or inactive tenant"})

        # Authenticate user credentials
        user = authenticate(username=username, password=password)
        if not user:
            raise AuthenticationFailed({"detail": "Invalid username or password"})

        # Verify user belongs to this tenant and is active
        if not isinstance(user, User) or user.tenant_id != tenant.id or not user.is_active:
            raise AuthenticationFailed({"detail": "User does not belong to this tenant or is inactive"})

        # Get user's permissions
        perms_qs = SystemModulePermission.objects.filter(roles__users=user, is_active=True).select_related("resource")
        permissions = [
            {
                "module": p.resource.code,
                "action": p.action,
                "codename": p.codename,
                "name": p.name,
            }
            for p in perms_qs
        ]

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "user": UserSerializer(user).data,
            "permissions": permissions,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
        })
