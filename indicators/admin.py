from django.contrib import admin
from .models import KPI, KPIValue, KPIScore


@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "indicator_type", "reporting_period", "direction", "owner", "created_at")
    list_filter = ("indicator_type", "reporting_period", "direction", "is_composite")
    search_fields = ("code", "name", "description", "formula")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(KPIValue)
class KPIValueAdmin(admin.ModelAdmin):
    list_display = ("kpi", "period_start", "period_end", "actual", "target", "baseline", "created_by", "created_at")
    list_filter = ("period_start", "period_end", "created_at")
    search_fields = ("kpi__code", "kpi__name", "notes")
    readonly_fields = ("id", "created_at")


@admin.register(KPIScore)
class KPIScoreAdmin(admin.ModelAdmin):
    list_display = ("kpi_value", "score", "weighted_score", "computed_at")
    list_filter = ("computed_at",)
    search_fields = ("kpi_value__kpi__code", "kpi_value__kpi__name")
    readonly_fields = ("id", "computed_at")

