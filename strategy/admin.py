from django.contrib import admin

from .models import Organization, Vision, Mission, StrategicPlanPeriod, FinancialYear, Perspective, Objective


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "location", "contact_email", "created_at")
    list_filter = ("tenant",)
    search_fields = ("name", "location", "contact_email")


@admin.register(Vision)
class VisionAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "statement", "created_at")
    list_filter = ("organization",)
    search_fields = ("statement",)


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "statement", "created_at")
    list_filter = ("organization",)
    search_fields = ("statement",)


@admin.register(StrategicPlanPeriod)
class StrategicPlanPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "start_year", "end_year", "status", "created_at")
    list_filter = ("status", "start_year", "organization")
    search_fields = ("name", "description")


@admin.register(FinancialYear)
class FinancialYearAdmin(admin.ModelAdmin):
    list_display = ("year_label", "strategic_plan_period", "start_date", "end_date", "status")
    list_filter = ("status", "strategic_plan_period")
    search_fields = ("year_label",)


@admin.register(Perspective)
class PerspectiveAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "strategic_plan_period", "created_at")
    list_filter = ("organization", "strategic_plan_period")
    search_fields = ("name", "description")


@admin.register(Objective)
class ObjectiveAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "perspective", "financial_year", "owner_id", "start_date", "end_date", "created_at")
    list_filter = ("organization", "perspective", "financial_year")
    search_fields = ("name", "description", "target")
