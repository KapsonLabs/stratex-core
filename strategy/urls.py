from django.urls import path

from .views import (
    OrganizationListCreateAPIView,
    OrganizationDetailAPIView,
    VisionListCreateAPIView,
    VisionDetailAPIView,
    MissionListCreateAPIView,
    MissionDetailAPIView,
    StrategicPlanPeriodListCreateAPIView,
    StrategicPlanPeriodDetailAPIView,
    FinancialYearListCreateAPIView,
    FinancialYearDetailAPIView,
    PerspectiveListCreateAPIView,
    PerspectiveDetailAPIView,
    ObjectiveListCreateAPIView,
    ObjectiveDetailAPIView,
)


urlpatterns = [
    # Organizations
    path("organizations/", OrganizationListCreateAPIView.as_view(), name="organization-list"),
    path("organizations/<int:pk>/", OrganizationDetailAPIView.as_view(), name="organization-detail"),
    
    # Visions (scoped to organization)
    path("organizations/<int:organization_id>/visions/", VisionListCreateAPIView.as_view(), name="vision-list"),
    path("organizations/<int:organization_id>/visions/<int:pk>/", VisionDetailAPIView.as_view(), name="vision-detail"),
    
    # Missions (scoped to organization)
    path("organizations/<int:organization_id>/missions/", MissionListCreateAPIView.as_view(), name="mission-list"),
    path("organizations/<int:organization_id>/missions/<int:pk>/", MissionDetailAPIView.as_view(), name="mission-detail"),
    
    # Strategic Plan Periods (scoped to organization)
    path("organizations/<int:organization_id>/strategic-plan-periods/", StrategicPlanPeriodListCreateAPIView.as_view(), name="strategic-plan-period-list"),
    path("organizations/<int:organization_id>/strategic-plan-periods/<int:pk>/", StrategicPlanPeriodDetailAPIView.as_view(), name="strategic-plan-period-detail"),
    
    # Financial Years (scoped to strategic plan period within organization)
    path("organizations/<int:organization_id>/strategic-plan-periods/<int:strategic_plan_period_id>/financial-years/", FinancialYearListCreateAPIView.as_view(), name="financial-year-list"),
    path("organizations/<int:organization_id>/strategic-plan-periods/<int:strategic_plan_period_id>/financial-years/<int:pk>/", FinancialYearDetailAPIView.as_view(), name="financial-year-detail"),
    
    # Perspectives (scoped to strategic plan period within organization)
    path("organizations/<int:organization_id>/strategic-plan-periods/<int:strategic_plan_period_id>/perspectives/", PerspectiveListCreateAPIView.as_view(), name="perspective-list"),
    path("organizations/<int:organization_id>/strategic-plan-periods/<int:strategic_plan_period_id>/perspectives/<int:pk>/", PerspectiveDetailAPIView.as_view(), name="perspective-detail"),
    
    # Objectives (scoped to perspective and financial year within organization)
    path("organizations/<int:organization_id>/financial-years/<int:financial_year_id>/perspectives/<int:perspective_id>/objectives/", ObjectiveListCreateAPIView.as_view(), name="objective-list"),
    path("organizations/<int:organization_id>/financial-years/<int:financial_year_id>/perspectives/<int:perspective_id>/objectives/<int:pk>/", ObjectiveDetailAPIView.as_view(), name="objective-detail"),
]
