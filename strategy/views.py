from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Organization, Vision, Mission, StrategicPlanPeriod, FinancialYear, Perspective, Objective
from .serializers import (
    OrganizationCreateSerializer,
    OrganizationDetailSerializer,
    VisionCreateSerializer,
    VisionDetailSerializer,
    MissionCreateSerializer,
    MissionDetailSerializer,
    StrategicPlanPeriodCreateSerializer,
    StrategicPlanPeriodDetailSerializer,
    FinancialYearCreateSerializer,
    FinancialYearDetailSerializer,
    PerspectiveCreateSerializer,
    PerspectiveDetailSerializer,
    ObjectiveCreateSerializer,
    ObjectiveDetailSerializer,
)


def check_user_organization_access(user, organization):
    """Check if user's tenant matches the organization's tenant."""
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required")
    if organization.tenant_id != user.tenant_id:
        raise PermissionDenied("You do not have access to this organization")


# Organization Views
class OrganizationListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only show organizations for the user's tenant
        queryset = Organization.objects.filter(tenant=request.user.tenant)
        serializer = OrganizationDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Automatically set tenant from authenticated user
        serializer.save(tenant=request.user.tenant)
        return Response(OrganizationDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class OrganizationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        obj = Organization.objects.get(pk=pk)
        check_user_organization_access(request.user, obj)
        return Response(OrganizationDetailSerializer(obj).data)

    def put(self, request, pk):
        obj = Organization.objects.get(pk=pk)
        check_user_organization_access(request.user, obj)
        serializer = OrganizationCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrganizationDetailSerializer(obj).data)

    def patch(self, request, pk):
        obj = Organization.objects.get(pk=pk)
        check_user_organization_access(request.user, obj)
        serializer = OrganizationCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrganizationDetailSerializer(obj).data)

    def delete(self, request, pk):
        obj = Organization.objects.get(pk=pk)
        check_user_organization_access(request.user, obj)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Vision Views
class VisionListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = Vision.objects.filter(organization=organization)
        serializer = VisionDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = VisionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=organization)
        return Response(VisionDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class VisionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Vision.objects.get(pk=pk, organization=organization)
        return Response(VisionDetailSerializer(obj).data)

    def put(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Vision.objects.get(pk=pk, organization=organization)
        serializer = VisionCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(VisionDetailSerializer(obj).data)

    def patch(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Vision.objects.get(pk=pk, organization=organization)
        serializer = VisionCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(VisionDetailSerializer(obj).data)

    def delete(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Vision.objects.get(pk=pk, organization=organization)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Mission Views
class MissionListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = Mission.objects.filter(organization=organization)
        serializer = MissionDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = MissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=organization)
        return Response(MissionDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class MissionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Mission.objects.get(pk=pk, organization=organization)
        return Response(MissionDetailSerializer(obj).data)

    def put(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Mission.objects.get(pk=pk, organization=organization)
        serializer = MissionCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MissionDetailSerializer(obj).data)

    def patch(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Mission.objects.get(pk=pk, organization=organization)
        serializer = MissionCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MissionDetailSerializer(obj).data)

    def delete(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Mission.objects.get(pk=pk, organization=organization)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# StrategicPlanPeriod Views
class StrategicPlanPeriodListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = StrategicPlanPeriod.objects.filter(organization=organization).select_related("vision", "mission")
        serializer = StrategicPlanPeriodDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = StrategicPlanPeriodCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=organization)
        return Response(StrategicPlanPeriodDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class StrategicPlanPeriodDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = StrategicPlanPeriod.objects.select_related("vision", "mission").get(pk=pk, organization=organization)
        return Response(StrategicPlanPeriodDetailSerializer(obj).data)

    def put(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = StrategicPlanPeriod.objects.get(pk=pk, organization=organization)
        serializer = StrategicPlanPeriodCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StrategicPlanPeriodDetailSerializer(obj).data)

    def patch(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = StrategicPlanPeriod.objects.get(pk=pk, organization=organization)
        serializer = StrategicPlanPeriodCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StrategicPlanPeriodDetailSerializer(obj).data)

    def delete(self, request, organization_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = StrategicPlanPeriod.objects.get(pk=pk, organization=organization)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# FinancialYear Views
class FinancialYearListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, strategic_plan_period_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = FinancialYear.objects.filter(
            strategic_plan_period_id=strategic_plan_period_id,
            strategic_plan_period__organization=organization
        ).select_related("strategic_plan_period")
        serializer = FinancialYearDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id, strategic_plan_period_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = FinancialYearCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure strategic_plan_period belongs to organization
        if serializer.validated_data.get("strategic_plan_period").organization_id != organization.id:
            raise PermissionDenied("Strategic plan period does not belong to this organization")
        serializer.save()
        return Response(FinancialYearDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class FinancialYearDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, strategic_plan_period_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = FinancialYear.objects.select_related("strategic_plan_period").get(
            pk=pk, strategic_plan_period_id=strategic_plan_period_id, strategic_plan_period__organization=organization
        )
        return Response(FinancialYearDetailSerializer(obj).data)

    def put(self, request, organization_id, strategic_plan_period_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = FinancialYear.objects.get(
            pk=pk, strategic_plan_period_id=strategic_plan_period_id, strategic_plan_period__organization=organization
        )
        serializer = FinancialYearCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(FinancialYearDetailSerializer(obj).data)

    def patch(self, request, organization_id, strategic_plan_period_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = FinancialYear.objects.get(
            pk=pk, strategic_plan_period_id=strategic_plan_period_id, strategic_plan_period__organization=organization
        )
        serializer = FinancialYearCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(FinancialYearDetailSerializer(obj).data)

    def delete(self, request, organization_id, strategic_plan_period_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = FinancialYear.objects.get(
            pk=pk, strategic_plan_period_id=strategic_plan_period_id, strategic_plan_period__organization=organization
        )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Perspective Views
class PerspectiveListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, strategic_plan_period_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = Perspective.objects.filter(
            strategic_plan_period_id=strategic_plan_period_id,
            organization=organization
        ).select_related("strategic_plan_period", "organization")
        serializer = PerspectiveDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id, strategic_plan_period_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = PerspectiveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure strategic_plan_period belongs to organization
        if serializer.validated_data.get("strategic_plan_period").organization_id != organization.id:
            raise PermissionDenied("Strategic plan period does not belong to this organization")
        serializer.save()
        return Response(PerspectiveDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class PerspectiveDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, strategic_plan_period_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Perspective.objects.select_related("strategic_plan_period", "organization").get(
            pk=pk, strategic_plan_period_id=strategic_plan_period_id, organization=organization
        )
        return Response(PerspectiveDetailSerializer(obj).data)

    def put(self, request, organization_id, strategic_plan_period_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Perspective.objects.get(
            pk=pk, strategic_plan_period_id=strategic_plan_period_id, organization=organization
        )
        serializer = PerspectiveCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PerspectiveDetailSerializer(obj).data)

    def patch(self, request, organization_id, strategic_plan_period_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Perspective.objects.get(
            pk=pk, strategic_plan_period_id=strategic_plan_period_id, organization=organization
        )
        serializer = PerspectiveCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PerspectiveDetailSerializer(obj).data)

    def delete(self, request, organization_id, strategic_plan_period_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Perspective.objects.get(
            pk=pk, strategic_plan_period_id=strategic_plan_period_id, organization=organization
        )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Objective Views
class ObjectiveListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, financial_year_id, perspective_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        queryset = Objective.objects.filter(
            financial_year_id=financial_year_id,
            perspective_id=perspective_id,
            organization=organization
        ).select_related("perspective", "financial_year", "organization")
        serializer = ObjectiveDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, organization_id, financial_year_id, perspective_id):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        serializer = ObjectiveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure perspective and financial_year belong to organization
        perspective = serializer.validated_data.get("perspective")
        financial_year = serializer.validated_data.get("financial_year")
        if perspective.organization_id != organization.id or financial_year.strategic_plan_period.organization_id != organization.id:
            raise PermissionDenied("Perspective and Financial Year must belong to this organization")
        serializer.save()
        return Response(ObjectiveDetailSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class ObjectiveDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, financial_year_id, perspective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Objective.objects.select_related("perspective", "financial_year", "organization").get(
            pk=pk,
            financial_year_id=financial_year_id,
            perspective_id=perspective_id,
            organization=organization
        )
        return Response(ObjectiveDetailSerializer(obj).data)

    def put(self, request, organization_id, financial_year_id, perspective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Objective.objects.get(
            pk=pk,
            financial_year_id=financial_year_id,
            perspective_id=perspective_id,
            organization=organization
        )
        serializer = ObjectiveCreateSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ObjectiveDetailSerializer(obj).data)

    def patch(self, request, organization_id, financial_year_id, perspective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Objective.objects.get(
            pk=pk,
            financial_year_id=financial_year_id,
            perspective_id=perspective_id,
            organization=organization
        )
        serializer = ObjectiveCreateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ObjectiveDetailSerializer(obj).data)

    def delete(self, request, organization_id, financial_year_id, perspective_id, pk):
        organization = Organization.objects.get(pk=organization_id)
        check_user_organization_access(request.user, organization)
        obj = Objective.objects.get(
            pk=pk,
            financial_year_id=financial_year_id,
            perspective_id=perspective_id,
            organization=organization
        )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
