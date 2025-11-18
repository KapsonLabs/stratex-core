from rest_framework import serializers

from .models import Organization, Vision, Mission, StrategicPlanPeriod, FinancialYear, Perspective, Objective


# Organization Serializers
class OrganizationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "location", "contact_email", "contact_phone", "address"]


class OrganizationDetailSerializer(serializers.ModelSerializer):
    tenant = serializers.StringRelatedField(read_only=True)
    visions_count = serializers.SerializerMethodField()
    missions_count = serializers.SerializerMethodField()
    strategic_plans_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id","tenant","name","location","contact_email","contact_phone","address","visions_count","missions_count","strategic_plans_count","created_at","updated_at",
        ]

    def get_visions_count(self, obj):
        return obj.visions.count()

    def get_missions_count(self, obj):
        return obj.missions.count()

    def get_strategic_plans_count(self, obj):
        return obj.strategic_plan_periods.count()


# Vision Serializers
class VisionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vision
        fields = ["statement"]


class VisionDetailSerializer(serializers.ModelSerializer):
    organization = serializers.StringRelatedField(read_only=True)
    mission = serializers.SerializerMethodField()

    class Meta:
        model = Vision
        fields = ["id", "organization", "statement", "created_at", "updated_at", "mission"]

    def get_mission(self, obj):
        if hasattr(obj, "mission"):
            return {
                "id": obj.mission.id,
                "statement": obj.mission.statement,
                "created_at": obj.mission.created_at,
                "updated_at": obj.mission.updated_at,
            }
        return None


# Mission Serializers
class MissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = ["statement", "vision"]


class MissionDetailSerializer(serializers.ModelSerializer):
    organization = serializers.StringRelatedField(read_only=True)
    vision = VisionDetailSerializer(read_only=True)
    strategic_plans_count = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = ["id", "organization", "statement", "vision", "strategic_plans_count", "created_at", "updated_at"]

    def get_strategic_plans_count(self, obj):
        return obj.strategic_plan_periods.count()


# StrategicPlanPeriod Serializers
class StrategicPlanPeriodCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategicPlanPeriod
        fields = ["vision", "mission", "name", "start_year", "end_year", "description", "status"]


class StrategicPlanPeriodDetailSerializer(serializers.ModelSerializer):
    organization = serializers.StringRelatedField(read_only=True)
    vision = serializers.StringRelatedField(read_only=True)
    mission = serializers.StringRelatedField(read_only=True)
    financial_years_count = serializers.SerializerMethodField()
    perspectives_count = serializers.SerializerMethodField()

    class Meta:
        model = StrategicPlanPeriod
        fields = ["id","organization","vision","mission","name","start_year","end_year","description","status","financial_years_count",
        "perspectives_count","created_at","updated_at"]

    def get_financial_years_count(self, obj):
        return obj.financial_years.count()

    def get_perspectives_count(self, obj):
        return obj.perspectives.count()


# FinancialYear Serializers
class FinancialYearCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialYear
        fields = ["strategic_plan_period", "year_label", "start_date", "end_date", "status"]


class FinancialYearDetailSerializer(serializers.ModelSerializer):
    strategic_plan_period = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = FinancialYear
        fields = ["id","strategic_plan_period","year_label","start_date",
        "end_date","status","created_at","updated_at"]


# Perspective Serializers
class PerspectiveCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perspective
        fields = ["strategic_plan_period", "organization", "name", "description"]


class PerspectiveDetailSerializer(serializers.ModelSerializer):
    strategic_plan_period = serializers.StringRelatedField(read_only=True)
    organization = serializers.StringRelatedField(read_only=True)
    objectives_count = serializers.SerializerMethodField()

    class Meta:
        model = Perspective
        fields = ["id","organization","strategic_plan_period","name","description","objectives_count","created_at","updated_at"]

    def get_objectives_count(self, obj):
        return obj.objectives.count()


# Objective Serializers
class ObjectiveCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Objective
        fields = ["perspective", "financial_year", "organization", "name", "description", "target", "owner_id", "start_date", "end_date"]


class ObjectiveDetailSerializer(serializers.ModelSerializer):
    perspective = serializers.StringRelatedField(read_only=True)
    financial_year = serializers.StringRelatedField(read_only=True)
    organization = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Objective
        fields = ["id","organization","perspective","financial_year","name","description","target","owner_id","start_date","end_date","created_at","updated_at"]

