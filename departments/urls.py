from django.urls import path

from .views import (
    DepartmentListCreateAPIView,
    DepartmentDetailAPIView,
    DepartmentObjectiveListCreateAPIView,
    DepartmentObjectiveDetailAPIView,
    TeamListCreateAPIView,
    TeamDetailAPIView,
    TeamObjectiveListCreateAPIView,
    TeamObjectiveDetailAPIView,
    KPIListCreateAPIView,
    KPIDetailAPIView,
    InitiativeListCreateAPIView,
    InitiativeDetailAPIView,
)


urlpatterns = [
    # Departments (scoped to organization)
    path("<int:organization_id>/departments/", DepartmentListCreateAPIView.as_view(), name="department-list"),
    path("<int:organization_id>/departments/<int:pk>/", DepartmentDetailAPIView.as_view(), name="department-detail"),
    
    # Department Objectives (scoped to department)
    path("<int:organization_id>/departments/<int:department_id>/department-objectives/", DepartmentObjectiveListCreateAPIView.as_view(), name="department-objective-list"),
    path("<int:organization_id>/departments/<int:department_id>/department-objectives/<int:pk>/", DepartmentObjectiveDetailAPIView.as_view(), name="department-objective-detail"),
    
    # Teams (scoped to department)
    path("<int:organization_id>/departments/<int:department_id>/teams/", TeamListCreateAPIView.as_view(), name="team-list"),
    path("<int:organization_id>/departments/<int:department_id>/teams/<int:pk>/", TeamDetailAPIView.as_view(), name="team-detail"),
    
    # Team Objectives (scoped to team)
    path("<int:organization_id>/departments/<int:department_id>/teams/<int:team_id>/team-objectives/", TeamObjectiveListCreateAPIView.as_view(), name="team-objective-list"),
    path("<int:organization_id>/departments/<int:department_id>/teams/<int:team_id>/team-objectives/<int:pk>/", TeamObjectiveDetailAPIView.as_view(), name="team-objective-detail"),
    
    # KPIs (scoped to objective)
    path("<int:organization_id>/objectives/<int:objective_id>/kpis/", KPIListCreateAPIView.as_view(), name="kpi-list"),
    path("<int:organization_id>/objectives/<int:objective_id>/kpis/<int:pk>/", KPIDetailAPIView.as_view(), name="kpi-detail"),
    
    # Initiatives (scoped to team)
    path("<int:organization_id>/departments/<int:department_id>/teams/<int:team_id>/initiatives/", InitiativeListCreateAPIView.as_view(), name="initiative-list"),
    path("<int:organization_id>/departments/<int:department_id>/teams/<int:team_id>/initiatives/<int:pk>/", InitiativeDetailAPIView.as_view(), name="initiative-detail"),
]

