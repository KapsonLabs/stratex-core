from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from typing import Tuple, Optional
import uuid

from .models import KPI, KPIValue, KPIScore
from .serializers import (
    KPICreateSerializer, KPIDetailSerializer,
    KPIValueCreateSerializer, KPIValueSerializer,
    KPIScoreSerializer
)
from departments.models import DepartmentObjective, TeamObjective
from strategy.models import Organization

def check_user_organization_access(user, organization):
    """Check if user's tenant matches the organization's tenant."""
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required")
    if organization.tenant_id != user.tenant_id:
        raise PermissionDenied("You do not have access to this organization")


def validate_kpi_uuid(pk: str) -> Tuple[Optional[uuid.UUID], Optional[Response]]:
    """
    Validate and convert a KPI primary key string to UUID.
    
    Args:
        pk: Primary key string to validate
        
    Returns:
        Tuple of (uuid_object, error_response):
        - On success: (UUID object, None)
        - On failure: (None, Response with error)
    """
    try:
        kpi_uuid = uuid.UUID(pk)
        return kpi_uuid, None
    except (ValueError, TypeError):
        error_response = Response(
            {"status": 400, "message": "Invalid KPI ID format"},
            status=status.HTTP_400_BAD_REQUEST
        )
        return None, error_response


# KPI Views
class KPIListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        
        # Get query parameters
        filter_type = request.query_params.get("type")  # 'objective' or 'team_objective'
        filter_id = request.query_params.get("id")  # The ID to filter by
        
        if not filter_type or not filter_id:
            return Response(
                {"status": 400, "message": "Both 'type' (objective or team_objective) and 'id' query parameters are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            filter_id = int(filter_id)
        except (ValueError, TypeError):
            return Response(
                {"status": 400, "message": "'id' must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build queryset based on filter type
        if filter_type == "objective":
            # Verify objective belongs to organization
            try:
                department_objective = DepartmentObjective.objects.get(pk=filter_id)
            except DepartmentObjective.DoesNotExist:
                return Response(
                    {"status": 404, "message": "Objective not found or does not belong to this organization"},
                    status=status.HTTP_404_NOT_FOUND
                )
            queryset = KPI.objects.filter(department_objective=filter_id).select_related("department_objective")
        elif filter_type == "team_objective":
            # Verify team_objective belongs to the organization
            try:
                team_objective = TeamObjective.objects.get(pk=filter_id, team__department__organization=organization)
            except TeamObjective.DoesNotExist:
                return Response(
                    {"status": 404, "message": "Team objective not found or does not belong to this organization"},
                    status=status.HTTP_404_NOT_FOUND
                )
            queryset = KPI.objects.filter(team_objective_id=filter_id).select_related("team_objective")
        else:
            return Response(
                {"status": 400, "message": "'type' must be either 'objective' or 'team_objective'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = queryset.prefetch_related("values", "values__score", "dependencies")
        serializer = KPIDetailSerializer(queryset, many=True)
        return Response({"status": 200, "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        
        serializer = KPICreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        serializer.save()
        return Response({"status": 201, "data": KPIDetailSerializer(serializer.instance).data}, status=status.HTTP_201_CREATED)


class KPIDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        
        # Validate UUID format
        kpi_uuid, error_response = validate_kpi_uuid(pk)
        if error_response:
            return error_response
        
        try:
            # Filter by organization through objective, department_objective, or team_objective
            obj = KPI.objects.select_related(
                "objective", "department_objective", "team_objective", "owner"
            ).prefetch_related("values", "values__score", "dependencies").filter(
                Q(objective__organization=organization) |
                Q(department_objective__department__organization=organization) |
                Q(team_objective__team__department__organization=organization)
            ).get(pk=kpi_uuid)
            return Response({"status": 200, "data": KPIDetailSerializer(obj).data}, status=status.HTTP_200_OK)
        except KPI.DoesNotExist:
            return Response({"status": 404, "message": "KPI not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        
        # Validate UUID format
        kpi_uuid, error_response = validate_kpi_uuid(pk)
        if error_response:
            return error_response
        
        try:
            obj = KPI.objects.filter(
                Q(objective__organization=organization) |
                Q(department_objective__department__organization=organization) |
                Q(team_objective__team__department__organization=organization)
            ).get(pk=kpi_uuid)
        except KPI.DoesNotExist:
            return Response({"status": 404, "message": "KPI not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = KPICreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Validate the new objective/team_objective belongs to organization
        objective = serializer.validated_data.get("objective")
        team_objective = serializer.validated_data.get("team_objective")
        
        if objective and objective.organization_id != organization.id:
            raise PermissionDenied("Objective does not belong to this organization")
        if team_objective and team_objective.team.department.organization_id != organization.id:
            raise PermissionDenied("Team objective does not belong to this organization")
        
        serializer.save()
        return Response({"status": 200, "data": KPIDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def patch(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        
        # Validate UUID format
        kpi_uuid, error_response = validate_kpi_uuid(pk)
        if error_response:
            return error_response
        
        try:
            obj = KPI.objects.filter(
                Q(objective__organization=organization) |
                Q(department_objective__department__organization=organization) |
                Q(team_objective__team__department__organization=organization)
            ).get(pk=kpi_uuid)
        except KPI.DoesNotExist:
            return Response({"status": 404, "message": "KPI not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = KPICreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Validate the new objective/team_objective belongs to organization if provided
        objective = serializer.validated_data.get("objective")
        team_objective = serializer.validated_data.get("team_objective")
        
        if objective and objective.organization_id != organization.id:
            raise PermissionDenied("Objective does not belong to this organization")
        if team_objective and team_objective.team.department.organization_id != organization.id:
            raise PermissionDenied("Team objective does not belong to this organization")
        
        serializer.save()
        return Response({"status": 200, "data": KPIDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def delete(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        
        # Validate UUID format
        kpi_uuid, error_response = validate_kpi_uuid(pk)
        if error_response:
            return error_response
        
        try:
            obj = KPI.objects.filter(
                Q(objective__organization=organization) |
                Q(department_objective__department__organization=organization) |
                Q(team_objective__team__department__organization=organization)
            ).get(pk=kpi_uuid)
        except KPI.DoesNotExist:
            return Response({"status": 404, "message": "KPI not found"}, status=status.HTTP_404_NOT_FOUND)
        
        obj.delete()
        return Response({"status": 204, "message": "KPI deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


