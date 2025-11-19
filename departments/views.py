from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

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

    def get(self, request, organization_id, team_id):
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
            # Verify team_objective belongs to organization
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
        
        queryset = queryset.prefetch_related("scores")
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
        try:
            # Filter by organization through objective, department_objective, or team_objective
            obj = KPI.objects.select_related(
                "objective", "department_objective", "team_objective"
            ).prefetch_related("scores").filter(
                Q(objective__organization=organization) |
                Q(department_objective__department__organization=organization) |
                Q(team_objective__team__department__organization=organization)
            ).get(pk=pk)
            return Response({"status": 200, "data": KPIDetailSerializer(obj).data}, status=status.HTTP_200_OK)
        except KPI.DoesNotExist:
            return Response({"status": 404, "message": "KPI not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        try:
            obj = KPI.objects.filter(
                Q(objective__organization=organization) |
                Q(department_objective__department__organization=organization) |
                Q(team_objective__team__department__organization=organization)
            ).get(pk=pk)
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
        try:
            obj = KPI.objects.filter(
                Q(objective__organization=organization) |
                Q(department_objective__department__organization=organization) |
                Q(team_objective__team__department__organization=organization)
            ).get(pk=pk)
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
        try:
            obj = KPI.objects.filter(
                Q(objective__organization=organization) |
                Q(department_objective__department__organization=organization) |
                Q(team_objective__team__department__organization=organization)
            ).get(pk=pk)
        except KPI.DoesNotExist:
            return Response({"status": 404, "message": "KPI not found"}, status=status.HTTP_404_NOT_FOUND)
        
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
