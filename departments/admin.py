from django.contrib import admin

from .models import Department, DepartmentObjective, Team, TeamObjective, Initiative, Employee, EmployeeReportingLine


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "head_id", "status", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("name", "description")


@admin.register(DepartmentObjective)
class DepartmentObjectiveAdmin(admin.ModelAdmin):
    list_display = ("department", "department_objective_name", "objective", "status", "created_at")
    list_filter = ("status", "department")
    search_fields = ("target",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "lead_id", "created_at")
    list_filter = ("department",)
    search_fields = ("name",)


@admin.register(TeamObjective)
class TeamObjectiveAdmin(admin.ModelAdmin):
    list_display = ("team_objective_name", "team", "dept_objective", "status", "created_at")
    list_filter = ("status", "team")
    search_fields = ("team_objective_name", "team__name", "team_objective_target")


@admin.register(Initiative)
class InitiativeAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "start_date", "end_date", "status", "created_at")
    list_filter = ("status", "team")
    search_fields = ("name", "description")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("related_user", "department", "team", "job_title", "is_department_head", "created_at")
    list_filter = ("is_department_head", "department", "team")
    search_fields = ("related_user__username", "related_user__email", "related_user__first_name", "related_user__last_name", "job_title")
    autocomplete_fields = ("related_user", "department", "team")


@admin.register(EmployeeReportingLine)
class EmployeeReportingLineAdmin(admin.ModelAdmin):
    list_display = ("employee", "reports_to", "relationship_type", "created_at")
    list_filter = ("relationship_type",)
    search_fields = ("employee__related_user__username", "reports_to__related_user__username")
    autocomplete_fields = ("employee", "reports_to")
