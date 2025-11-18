from django.contrib import admin

from .models import Department, DepartmentObjective, Team, TeamObjective, KPI, Initiative


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "head_id", "status", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("name", "description")


@admin.register(DepartmentObjective)
class DepartmentObjectiveAdmin(admin.ModelAdmin):
    list_display = ("department", "objective", "status", "created_at")
    list_filter = ("status", "department")
    search_fields = ("target",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "lead_id", "created_at")
    list_filter = ("department",)
    search_fields = ("name",)


@admin.register(TeamObjective)
class TeamObjectiveAdmin(admin.ModelAdmin):
    list_display = ("team", "dept_objective", "status", "created_at")
    list_filter = ("status", "team")
    search_fields = ("team__name",)


@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "objective", "department_objective", "team_objective", "target_value", "current_value", "unit", "frequency", "status", "owner_id", "created_at")
    list_filter = ("level", "status")
    search_fields = ("name", "formula")


@admin.register(Initiative)
class InitiativeAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "start_date", "end_date", "status", "created_at")
    list_filter = ("status", "team")
    search_fields = ("name", "description")
