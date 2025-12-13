from django.urls import path
from .views import KPIListCreateAPIView, KPIDetailAPIView


urlpatterns = [
    # KPIs (can be scoped to objective or team_objective via query params)
    path("<int:organization_id>/kpis/", KPIListCreateAPIView.as_view(), name="kpi-list"),
    path("<int:organization_id>/kpis/<int:pk>/", KPIDetailAPIView.as_view(), name="kpi-detail"),
]

