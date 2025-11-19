from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from tenants.models import SystemModulePermission, Tenant
from .models import Role, User, RolePermission
from .serializers import RoleSerializer, UserSerializer, AuthUserSerializer


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ["1", "true", "t", "yes", "y"]
    return False


class RoleListCreateAPIView(APIView):
    def get(self, request):
        queryset = Role.objects.all()
        serializer = RoleSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        serializer = RoleSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RoleDetailAPIView(APIView):
    def get(self, request, pk):
        obj = Role.objects.get(pk=pk)
        return Response(RoleSerializer(obj, context={"request": request}).data)

    def put(self, request, pk):
        obj = Role.objects.get(pk=pk)
        serializer = RoleSerializer(obj, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = Role.objects.get(pk=pk)
        serializer = RoleSerializer(obj, data=request.data, partial=True, context={"request": request})
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
        if not user.role_id:
            return Response([])
        
        # Get permissions through RolePermission
        perms_qs = SystemModulePermission.objects.filter(
            role_permissions__role=user.role,
            role_permissions__is_active=True,
            is_active=True
        ).select_related("resource", "resource__module").distinct()
        
        return Response([
            {
                "module": p.resource.module.code,
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
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AuthUserSerializer(data=request.data)
        is_valid = serializer.is_valid(raise_exception=True)
        if not is_valid:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.validated_data["user"]
            
        permissions = [
            {
                "module": p.resource.module.code,
                "action": p.action,
                "codename": p.codename,
                "name": p.name,
            }
            for p in user.get_permissions()
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
