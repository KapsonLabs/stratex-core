from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Module, SystemModulePermission, Licence, Tenant, TenantSettings
from .serializers import (
    ModuleSerializer,
    SystemModulePermissionSerializer,
    LicenceSerializer,
    TenantSerializer,
)


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ["1", "true", "t", "yes", "y"]
    return False


class ModuleListCreateAPIView(APIView):
    def get(self, request):
        queryset = Module.objects.all()
        serializer = ModuleSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ModuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ModuleDetailAPIView(APIView):
    def get(self, request, pk):
        obj = Module.objects.get(pk=pk)
        return Response(ModuleSerializer(obj).data)

    def put(self, request, pk):
        obj = Module.objects.get(pk=pk)
        serializer = ModuleSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = Module.objects.get(pk=pk)
        serializer = ModuleSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = Module.objects.get(pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ModuleStatusAPIView(APIView):
    def post(self, request, pk):
        obj = Module.objects.get(pk=pk)
        is_active = parse_bool(request.data.get("is_active"))
        obj.is_active = is_active
        obj.save(update_fields=["is_active"])
        return Response(ModuleSerializer(obj).data)


class ModulePermissionListCreateAPIView(APIView):
    def get(self, request):
        queryset = SystemModulePermission.objects.all()
        serializer = SystemModulePermissionSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SystemModulePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ModulePermissionDetailAPIView(APIView):
    def get(self, request, pk):
        obj = SystemModulePermission.objects.get(pk=pk)
        return Response(SystemModulePermissionSerializer(obj).data)

    def put(self, request, pk):
        obj = SystemModulePermission.objects.get(pk=pk)
        serializer = SystemModulePermissionSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = SystemModulePermission.objects.get(pk=pk)
        serializer = SystemModulePermissionSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = SystemModulePermission.objects.get(pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ModulePermissionStatusAPIView(APIView):
    def post(self, request, pk):
        obj = SystemModulePermission.objects.get(pk=pk)
        is_active = parse_bool(request.data.get("is_active"))
        obj.is_active = is_active
        obj.save(update_fields=["is_active"])
        return Response(SystemModulePermissionSerializer(obj).data)


class LicenceListCreateAPIView(APIView):
    def get(self, request):
        queryset = Licence.objects.all()
        serializer = LicenceSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LicenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LicenceDetailAPIView(APIView):
    def get(self, request, pk):
        obj = Licence.objects.get(pk=pk)
        return Response(LicenceSerializer(obj).data)

    def put(self, request, pk):
        obj = Licence.objects.get(pk=pk)
        serializer = LicenceSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = Licence.objects.get(pk=pk)
        serializer = LicenceSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = Licence.objects.get(pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LicenceStatusAPIView(APIView):
    def post(self, request, pk):
        obj = Licence.objects.get(pk=pk)
        is_active = parse_bool(request.data.get("is_active"))
        obj.is_active = is_active
        obj.save(update_fields=["is_active"])
        return Response(LicenceSerializer(obj).data)


class TenantListCreateAPIView(APIView):
    def get(self, request):
        queryset = Tenant.objects.all()
        serializer = TenantSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TenantDetailAPIView(APIView):
    def get(self, request, pk):
        obj = Tenant.objects.get(pk=pk)
        return Response(TenantSerializer(obj).data)

    def put(self, request, pk):
        obj = Tenant.objects.get(pk=pk)
        serializer = TenantSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = Tenant.objects.get(pk=pk)
        serializer = TenantSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = Tenant.objects.get(pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TenantStatusAPIView(APIView):
    def post(self, request, pk):
        obj = Tenant.objects.get(pk=pk)
        is_active = parse_bool(request.data.get("is_active"))
        obj.is_active = is_active
        obj.save(update_fields=["is_active"])
        return Response(TenantSerializer(obj).data)