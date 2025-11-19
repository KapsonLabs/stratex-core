from rest_framework import serializers
from datetime import date
from .models import Department, DepartmentObjective, Team, TeamObjective, KPI, KPIScore, Initiative, Employee, EmployeeReportingLine


# Department Serializers
class DepartmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["name", "head_id", "description", "status"]


class DepartmentDetailSerializer(serializers.ModelSerializer):
    organization = serializers.StringRelatedField(read_only=True)
    teams_count = serializers.SerializerMethodField()
    department_objectives_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "organization", "name", "head_id", "description", "status", "teams_count", "department_objectives_count","created_at", "updated_at"]

    def get_teams_count(self, obj):
        return obj.teams.count()

    def get_department_objectives_count(self, obj):
        return obj.department_objectives.count()


# DepartmentObjective Serializers
class DepartmentObjectiveCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentObjective
        fields = ["department", "department_objective_name", "objective", "composite_weight", "objective_target", "status"]


class DepartmentObjectiveDetailSerializer(serializers.ModelSerializer):
    department = serializers.StringRelatedField(read_only=True)
    objective = serializers.StringRelatedField(read_only=True)
    team_objectives_count = serializers.SerializerMethodField()
    kpis_count = serializers.SerializerMethodField()
    objective_score = serializers.SerializerMethodField()

    class Meta:
        model = DepartmentObjective
        fields = ["id", "department", "department_objective_name", "objective", "composite_weight", "objective_target", "status", "team_objectives_count", "kpis_count", "objective_score", "created_at","updated_at"]

    def get_team_objectives_count(self, obj):
        return obj.team_objectives.count()

    def get_kpis_count(self, obj):
        return obj.kpis.count()

    def get_objective_score(self, obj):
        return 0


# Team Serializers
class TeamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["department", "name", "lead_id"]


class TeamDetailSerializer(serializers.ModelSerializer):
    department = serializers.StringRelatedField(read_only=True)
    team_objectives_count = serializers.SerializerMethodField()
    initiatives_count = serializers.SerializerMethodField()
    team_performance = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id","department","name","lead_id","team_objectives_count","initiatives_count","team_performance","created_at","updated_at"]

    def get_team_objectives_count(self, obj):
        return obj.team_objectives.count()

    def get_initiatives_count(self, obj):
        return obj.initiatives.count()

    def get_team_performance(self, obj):
        return 0


# TeamObjective Serializers
class TeamObjectiveCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamObjective
        fields = ["team", "dept_objective", "team_objective_name", "objective_target", "team_objective_description", "status"]


class TeamObjectiveDetailSerializer(serializers.ModelSerializer):
    team = serializers.StringRelatedField(read_only=True)
    dept_objective = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TeamObjective
        fields = ["id", "team", "dept_objective", "team_objective_name", "objective_target", "team_objective_description", "status", "created_at", "updated_at"]


# KPI Serializers
class KPICreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPI
        fields = ["name", "description", "formula", "target_value", "current_value", "unit", "frequency", "status", "owner_id", "level", "objective", "department_objective", "team_objective", "financial_year"]

    def validate(self, attrs):
        level = attrs.get("level")
        obj = attrs.get("objective")
        dept_obj = attrs.get("department_objective")
        team_obj = attrs.get("team_objective")

        if level == "strategic" and not obj:
            raise serializers.ValidationError("objective is required for strategic level KPI")
        if level == "department" and not dept_obj:
            raise serializers.ValidationError("department_objective is required for department level KPI")
        if level == "team" and not team_obj:
            raise serializers.ValidationError("team_objective is required for team level KPI")
        return attrs


class KPIScoreSerializer(serializers.ModelSerializer):
    """Serializer for KPI Score."""
    class Meta:
        model = KPIScore
        fields = ["id", "period_label", "date", "value", "notes", "created_at"]


class KPIDetailSerializer(serializers.ModelSerializer):
    objective = serializers.StringRelatedField(read_only=True)
    department_objective = serializers.StringRelatedField(read_only=True)
    team_objective = serializers.StringRelatedField(read_only=True)
    scores = serializers.SerializerMethodField()

    class Meta:
        model = KPI
        fields = ["id", "name", "description", "formula", "target_value", "current_value", "unit", "frequency", "status", "owner_id","level", "objective", "department_objective", "team_objective", "financial_year", "scores", "created_at", "updated_at"]

    def get_scores(self, obj):
        """Return KPI scores ordered from latest (newest first)."""
        scores = obj.scores.all()  # Already ordered by Meta.ordering: ["-date", "-id"]
        return KPIScoreSerializer(scores, many=True).data


# Initiative Serializers
class InitiativeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Initiative
        fields = ["team", "name", "description", "start_date", "end_date", "status"]


class InitiativeDetailSerializer(serializers.ModelSerializer):
    team = serializers.StringRelatedField(read_only=True)
    team_objectives_count = serializers.SerializerMethodField()

    class Meta:
        model = Initiative
        fields = ["id", "team", "name", "description", "start_date", "end_date", "status", "team_objectives_count", "created_at","updated_at"]

    def get_team_objectives_count(self, obj):
        return obj.team_objectives.count()


# Employee Serializers
class EmployeeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ["related_user", "department", "team", "job_title", "is_department_head"]

    def validate(self, attrs):
        """Ensure only one department head per department."""
        is_department_head = attrs.get("is_department_head", False)
        department = attrs.get("department")
        
        if is_department_head and department:
            existing_head = Employee.objects.filter(
                department=department,
                is_department_head=True
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_head.exists():
                raise serializers.ValidationError(
                    {
                        "is_department_head": f"Department '{department.name}' already has a head assigned. "
                        "Only one employee per department can be designated as department head."
                    }
                )
        
        return attrs


class EmployeeDetailSerializer(serializers.ModelSerializer):
    related_user = serializers.SerializerMethodField()
    department = serializers.StringRelatedField(read_only=True)
    team = serializers.StringRelatedField(read_only=True)
    reporting_lines_count = serializers.SerializerMethodField()
    direct_reports_count = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "related_user",
            "department",
            "team",
            "job_title",
            "is_department_head",
            "reporting_lines_count",
            "direct_reports_count",
            "created_at",
            "updated_at"
        ]

    def get_related_user(self, obj):
        """Return user details."""
        user = obj.related_user
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.get_full_name() or user.username,
        }

    def get_reporting_lines_count(self, obj):
        """Count of reporting relationships for this employee."""
        return obj.reporting_lines.count()

    def get_direct_reports_count(self, obj):
        """Count of employees reporting to this employee."""
        return obj.direct_reports.count()


# EmployeeReportingLine Serializers
class EmployeeReportingLineCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeReportingLine
        fields = ["employee", "reports_to", "relationship_type"]

    def validate(self, attrs):
        """Ensure employee cannot report to themselves."""
        employee = attrs.get("employee")
        reports_to = attrs.get("reports_to")
        
        if employee and reports_to and employee.id == reports_to.id:
            raise serializers.ValidationError(
                {"reports_to": "An employee cannot report to themselves."}
            )
        
        return attrs


class EmployeeReportingLineDetailSerializer(serializers.ModelSerializer):
    employee = serializers.SerializerMethodField()
    reports_to = serializers.SerializerMethodField()
    relationship_type_display = serializers.CharField(source="get_relationship_type_display", read_only=True)

    class Meta:
        model = EmployeeReportingLine
        fields = [
            "id",
            "employee",
            "reports_to",
            "relationship_type",
            "relationship_type_display",
            "created_at",
            "updated_at"
        ]

    def get_employee(self, obj):
        """Return employee details."""
        emp = obj.employee
        user = emp.related_user
        return {
            "id": emp.id,
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
            },
            "job_title": emp.job_title,
            "department": emp.department.name,
        }

    def get_reports_to(self, obj):
        """Return reports_to employee details."""
        emp = obj.reports_to
        user = emp.related_user
        return {
            "id": emp.id,
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
            },
            "job_title": emp.job_title,
            "department": emp.department.name,
        }

