from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Department, DepartmentObjective, Team, TeamObjective, KPI, Initiative
from .serializers import (
    DepartmentCreateSerializer,
    DepartmentDetailSerializer,
    DepartmentObjectiveCreateSerializer,
    DepartmentObjectiveDetailSerializer,
    TeamCreateSerializer,
    TeamDetailSerializer,
    TeamObjectiveCreateSerializer,
    TeamObjectiveDetailSerializer,
    KPICreateSerializer,
    KPIDetailSerializer,
    InitiativeCreateSerializer,
    InitiativeDetailSerializer,
)

# Import for organization access check
from strategy.models import Organization


def check_user_organization_access(user, organization):
    """Check if user's tenant matches the organization's tenant."""
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required")
    if organization.tenant_id != user.tenant_id:
        raise PermissionDenied("You do not have access to this organization")


# Department Views
class DepartmentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = Department.objects.filter(organization=organization).select_related("organization")
        serializer = DepartmentDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = DepartmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=organization)
        return Response(DepartmentDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class DepartmentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Department.objects.select_related("organization").get(pk=pk, organization=organization)
        return Response(DepartmentDetailSerializer(obj).data)

    def put(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Department.objects.get(pk=pk, organization=organization)
        serializer = DepartmentCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DepartmentDetailSerializer(obj).data)

    def patch(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Department.objects.get(pk=pk, organization=organization)
        serializer = DepartmentCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DepartmentDetailSerializer(obj).data)

    def delete(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Department.objects.get(pk=pk, organization=organization)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# DepartmentObjective Views
class DepartmentObjectiveListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = DepartmentObjective.objects.filter(
            department_id=department_id, department__organization=organization
        ).select_related("department", "objective")
        serializer = DepartmentObjectiveDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id, department_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = DepartmentObjectiveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure department belongs to organization
        if serializer.validated_data.get("department").organization_id != organization.id:
            raise PermissionDenied("Department does not belong to this organization")
        serializer.save()
        return Response(DepartmentObjectiveDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class DepartmentObjectiveDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = DepartmentObjective.objects.select_related("department", "objective").get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        return Response(DepartmentObjectiveDetailSerializer(obj).data)

    def put(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = DepartmentObjective.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        serializer = DepartmentObjectiveCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DepartmentObjectiveDetailSerializer(obj).data)

    def patch(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = DepartmentObjective.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        serializer = DepartmentObjectiveCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DepartmentObjectiveDetailSerializer(obj).data)

    def delete(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = DepartmentObjective.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Team Views
class TeamListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = Team.objects.filter(
            department_id=department_id, department__organization=organization
        ).select_related("department")
        serializer = TeamDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id, department_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = TeamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure department belongs to organization
        if serializer.validated_data.get("department").organization_id != organization.id:
            raise PermissionDenied("Department does not belong to this organization")
        serializer.save()
        return Response(TeamDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class TeamDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Team.objects.select_related("department").get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        return Response(TeamDetailSerializer(obj).data)

    def put(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Team.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        serializer = TeamCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TeamDetailSerializer(obj).data)

    def patch(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Team.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        serializer = TeamCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TeamDetailSerializer(obj).data)

    def delete(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Team.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# TeamObjective Views
class TeamObjectiveListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, team_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = TeamObjective.objects.filter(
            team_id=team_id, team__department__organization=organization
        ).select_related("team", "dept_objective", "kpi", "initiative")
        serializer = TeamObjectiveDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id, department_id, team_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = TeamObjectiveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TeamObjectiveDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class TeamObjectiveDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = TeamObjective.objects.select_related("team", "dept_objective", "kpi", "initiative").get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        return Response(TeamObjectiveDetailSerializer(obj).data)

    def put(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = TeamObjective.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        serializer = TeamObjectiveCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TeamObjectiveDetailSerializer(obj).data)

    def patch(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = TeamObjective.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        serializer = TeamObjectiveCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TeamObjectiveDetailSerializer(obj).data)

    def delete(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = TeamObjective.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# KPI Views
class KPIListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, objective_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = KPI.objects.filter(
            objective_id=objective_id, objective__organization=organization
        ).select_related("objective")
        serializer = KPIDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id, objective_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = KPICreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure objective belongs to organization
        if serializer.validated_data.get("objective").organization_id != organization.id:
            raise PermissionDenied("Objective does not belong to this organization")
        serializer.save()
        return Response(KPIDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class KPIDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, objective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = KPI.objects.select_related("objective").get(
            pk=pk, objective_id=objective_id, objective__organization=organization
        )
        return Response(KPIDetailSerializer(obj).data)

    def put(self, request, organization_id, objective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = KPI.objects.get(
            pk=pk, objective_id=objective_id, objective__organization=organization
        )
        serializer = KPICreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(KPIDetailSerializer(obj).data)

    def patch(self, request, organization_id, objective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = KPI.objects.get(
            pk=pk, objective_id=objective_id, objective__organization=organization
        )
        serializer = KPICreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(KPIDetailSerializer(obj).data)

    def delete(self, request, organization_id, objective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = KPI.objects.get(
            pk=pk, objective_id=objective_id, objective__organization=organization
        )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Initiative Views
class InitiativeListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, team_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = Initiative.objects.filter(
            team_id=team_id, team__department__organization=organization
        ).select_related("team")
        serializer = InitiativeDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id, department_id, team_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = InitiativeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure team belongs to organization
        if serializer.validated_data.get("team").department.organization_id != organization.id:
            raise PermissionDenied("Team does not belong to this organization")
        serializer.save()
        return Response(InitiativeDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class InitiativeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Initiative.objects.select_related("team").get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        return Response(InitiativeDetailSerializer(obj).data)

    def put(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Initiative.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        serializer = InitiativeCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(InitiativeDetailSerializer(obj).data)

    def patch(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Initiative.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        serializer = InitiativeCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(InitiativeDetailSerializer(obj).data)

    def delete(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Initiative.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
