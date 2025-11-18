from rest_framework import serializers

from .models import Department, DepartmentObjective, Team, TeamObjective, KPI, Initiative


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
        fields = ["department", "objective", "composite_weight", "target", "status"]


class DepartmentObjectiveDetailSerializer(serializers.ModelSerializer):
    department = serializers.StringRelatedField(read_only=True)
    objective = serializers.StringRelatedField(read_only=True)
    team_objectives_count = serializers.SerializerMethodField()

    class Meta:
        model = DepartmentObjective
        fields = ["id", "department", "objective", "composite_weight", "target", "status", "team_objectives_count", "created_at","updated_at"]

    def get_team_objectives_count(self, obj):
        return obj.team_objectives.count()


# Team Serializers
class TeamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["department", "name", "lead_id"]


class TeamDetailSerializer(serializers.ModelSerializer):
    department = serializers.StringRelatedField(read_only=True)
    team_objectives_count = serializers.SerializerMethodField()
    initiatives_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id","department","name","lead_id","team_objectives_count","initiatives_count","created_at","updated_at"]

    def get_team_objectives_count(self, obj):
        return obj.team_objectives.count()

    def get_initiatives_count(self, obj):
        return obj.initiatives.count()


# TeamObjective Serializers
class TeamObjectiveCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamObjective
        fields = ["team", "dept_objective", "status"]


class TeamObjectiveDetailSerializer(serializers.ModelSerializer):
    team = serializers.StringRelatedField(read_only=True)
    dept_objective = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TeamObjective
        fields = ["id", "team", "dept_objective", "status", "created_at", "updated_at"]


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


class KPIDetailSerializer(serializers.ModelSerializer):
    objective = serializers.StringRelatedField(read_only=True)
    department_objective = serializers.StringRelatedField(read_only=True)
    team_objective = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = KPI
        fields = ["id", "name", "description", "formula", "target_value", "current_value", "unit", "frequency", "status", "owner_id","level", "objective", "department_objective", "team_objective", "financial_year", "created_at", "updated_at"]


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

