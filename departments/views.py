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
        return Response({"status": 200, "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = DepartmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=organization)
        return Response({"status": 201, "data": DepartmentDetailSerializer(serializer.instance).data}, status=status.HTTP_201_CREATED)


class DepartmentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Department.objects.select_related("organization").get(pk=pk, organization=organization)
        return Response({"status": 200, "data": DepartmentDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def put(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Department.objects.get(pk=pk, organization=organization)
        serializer = DepartmentCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": DepartmentDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def patch(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Department.objects.get(pk=pk, organization=organization)
        serializer = DepartmentCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": DepartmentDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def delete(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Department.objects.get(pk=pk, organization=organization)
        obj.delete()
        return Response({"status": 204, "message": "Department deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


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
        return Response({"status": 200, "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, organization_id, department_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = DepartmentObjectiveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure department belongs to organization
        if serializer.validated_data.get("department").organization_id != organization.id:
            raise PermissionDenied("Department does not belong to this organization")
        serializer.save()
        return Response({"status": 201, "data": DepartmentObjectiveDetailSerializer(serializer.instance).data}, status=status.HTTP_201_CREATED)


class DepartmentObjectiveDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = DepartmentObjective.objects.select_related("department", "objective").get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        return Response({"status": 200, "data": DepartmentObjectiveDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def put(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = DepartmentObjective.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        serializer = DepartmentObjectiveCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": DepartmentObjectiveDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def patch(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = DepartmentObjective.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        serializer = DepartmentObjectiveCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": DepartmentObjectiveDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def delete(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = DepartmentObjective.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        obj.delete()
        return Response({"status": 204, "message": "Department objective deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


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
        return Response({"status": 200, "data": serializer.data}, status=status.HTTP_200_OK)    

    def post(self, request, organization_id, department_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = TeamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure department belongs to organization
        if serializer.validated_data.get("department").organization_id != organization.id:
            raise PermissionDenied("Department does not belong to this organization")
        serializer.save()
        return Response({"status": 201, "data": TeamDetailSerializer(serializer.instance).data}, status=status.HTTP_201_CREATED)


class TeamDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        try:
            obj = Team.objects.select_related("department").get(
                pk=pk, department_id=department_id, department__organization=organization
            )
            return Response({"status": 200, "data": TeamDetailSerializer(obj).data}, status=status.HTTP_200_OK)
        except Team.DoesNotExist:
            return Response({"status": 404, "message": "Team not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Team.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        serializer = TeamCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": TeamDetailSerializer(obj).data}, status=status.HTTP_200_OK) 

    def patch(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Team.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        serializer = TeamCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": TeamDetailSerializer(obj).data}, status=status.HTTP_200_OK) 

    def delete(self, request, organization_id, department_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Team.objects.get(
            pk=pk, department_id=department_id, department__organization=organization
        )
        obj.delete()
        return Response({"status": 204, "message": "Team deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# TeamObjective Views
class TeamObjectiveListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, team_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = TeamObjective.objects.filter(
            team_id=team_id, team__department__organization=organization
        ).select_related("team", "dept_objective")
        serializer = TeamObjectiveDetailSerializer(queryset, many=True)
        return Response({"status": 200, "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, organization_id, department_id, team_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = TeamObjectiveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 201, "data": TeamObjectiveDetailSerializer(serializer.instance).data}, status=status.HTTP_201_CREATED)


class TeamObjectiveDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = TeamObjective.objects.select_related("team", "dept_objective").get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        return Response({"status": 200, "data": TeamObjectiveDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def put(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = TeamObjective.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        serializer = TeamObjectiveCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": TeamObjectiveDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def patch(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = TeamObjective.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        serializer = TeamObjectiveCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": TeamObjectiveDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def delete(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = TeamObjective.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        obj.delete()
        return Response({"status": 204, "message": "Team objective deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


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
        return Response({"status": 200, "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, organization_id, objective_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = KPICreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure objective belongs to organization
        if serializer.validated_data.get("objective").organization_id != organization.id:
            raise PermissionDenied("Objective does not belong to this organization")
        serializer.save()
        return Response({"status": 201, "data": KPIDetailSerializer(serializer.instance).data}, status=status.HTTP_201_CREATED)


class KPIDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, objective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = KPI.objects.select_related("objective").get(
            pk=pk, objective_id=objective_id, objective__organization=organization
        )
        return Response({"status": 200, "data": KPIDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def put(self, request, organization_id, objective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = KPI.objects.get(
            pk=pk, objective_id=objective_id, objective__organization=organization
        )
        serializer = KPICreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": KPIDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def patch(self, request, organization_id, objective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = KPI.objects.get(
            pk=pk, objective_id=objective_id, objective__organization=organization
        )
        serializer = KPICreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": KPIDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def delete(self, request, organization_id, objective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = KPI.objects.get(
            pk=pk, objective_id=objective_id, objective__organization=organization
        )
        obj.delete()
        return Response({"status": 204, "message": "KPI deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# Initiative Views
class InitiativeListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, team_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        try:
            queryset = Initiative.objects.filter(
                team_id=team_id, team__department__organization=organization
            ).select_related("team")
            serializer = InitiativeDetailSerializer(queryset, many=True)
            return Response({"status": 200, "data": serializer.data}, status=status.HTTP_200_OK)
        except Initiative.DoesNotExist:
            return Response({"status": 404, "message": "Team not found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, organization_id, department_id, team_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = InitiativeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure team belongs to organization
        if serializer.validated_data.get("team").department.organization_id != organization.id:
            raise PermissionDenied("Team does not belong to this organization")
        serializer.save()
        return Response({"status": 201, "data": InitiativeDetailSerializer(serializer.instance).data}, status=status.HTTP_201_CREATED)


class InitiativeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Initiative.objects.select_related("team").get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        return Response({"status": 200, "data": InitiativeDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def put(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Initiative.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        serializer = InitiativeCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": InitiativeDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def patch(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Initiative.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        serializer = InitiativeCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 200, "data": InitiativeDetailSerializer(obj).data}, status=status.HTTP_200_OK)

    def delete(self, request, organization_id, department_id, team_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Initiative.objects.get(
            pk=pk, team_id=team_id, team__department__organization=organization
        )
        obj.delete()
        return Response({"status": 204, "message": "Initiative deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
