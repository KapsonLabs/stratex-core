from rest_framework import serializers
from .models import KPI, KPIValue, KPIScore


# KPI Serializers
class KPICreateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating KPIs."""
    class Meta:
        model = KPI
        fields = [
            "code", "name", "description", "owner", "unit", "direction", 
            "indicator_type", "reporting_period", "weight", "scoring_config", 
            "formula", "dependencies", "is_composite", "metadata",
            "objective", "department_objective", "team_objective", "financial_year"
        ]

    def validate(self, attrs):
        """Validate that composite KPIs have dependencies and formula."""
        is_composite = attrs.get("is_composite", False)
        formula = attrs.get("formula", "")
        dependencies = attrs.get("dependencies", [])
        
        if is_composite:
            if not formula:
                raise serializers.ValidationError("formula is required for composite KPIs")
            if not dependencies:
                raise serializers.ValidationError("dependencies are required for composite KPIs")
        
        return attrs


class KPIDetailSerializer(serializers.ModelSerializer):
    """Serializer for KPI detail view with related data."""
    owner = serializers.SerializerMethodField()
    objective = serializers.StringRelatedField(read_only=True)
    department_objective = serializers.StringRelatedField(read_only=True)
    team_objective = serializers.StringRelatedField(read_only=True)
    financial_year = serializers.StringRelatedField(read_only=True)
    dependencies = serializers.SerializerMethodField()
    values_count = serializers.SerializerMethodField()
    latest_value = serializers.SerializerMethodField()
    latest_score = serializers.SerializerMethodField()

    class Meta:
        model = KPI
        fields = [
            "id", "code", "name", "description", "owner", "unit", "direction",
            "indicator_type", "reporting_period", "weight", "scoring_config",
            "formula", "dependencies", "is_composite", "metadata",
            "objective", "department_objective", "team_objective", "financial_year",
            "values_count", "latest_value", "latest_score",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_owner(self, obj):
        """Return owner details."""
        if obj.owner:
            return {
                "id": obj.owner.id,
                "username": obj.owner.username,
                "email": obj.owner.email,
                "full_name": obj.owner.get_full_name() or obj.owner.username,
            }
        return None

    def get_dependencies(self, obj):
        """Return list of dependency KPI codes."""
        return [dep.code for dep in obj.dependencies.all()]

    def get_values_count(self, obj):
        """Return count of KPI values."""
        return obj.values.count()

    def get_latest_value(self, obj):
        """Return the latest KPI value."""
        latest = obj.values.order_by("-period_end").first()
        if latest:
            return KPIValueSerializer(latest).data
        return None

    def get_latest_score(self, obj):
        """Return the latest KPI score."""
        latest_value = obj.values.order_by("-period_end").first()
        if latest_value:
            try:
                score = latest_value.score
                return KPIScoreSerializer(score).data
            except KPIScore.DoesNotExist:
                return None
        return None


# KPIValue Serializers
class KPIValueCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating KPI values."""
    class Meta:
        model = KPIValue
        fields = [
            "kpi", "period_start", "period_end", "actual", "target", 
            "baseline", "notes", "created_by"
        ]

    def validate(self, attrs):
        """Validate period dates."""
        period_start = attrs.get("period_start")
        period_end = attrs.get("period_end")
        
        if period_start and period_end and period_start > period_end:
            raise serializers.ValidationError(
                "period_start must be before or equal to period_end"
            )
        
        return attrs


class KPIValueSerializer(serializers.ModelSerializer):
    """Serializer for KPI value detail view."""
    kpi = serializers.StringRelatedField(read_only=True)
    kpi_code = serializers.CharField(source="kpi.code", read_only=True)
    created_by = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    class Meta:
        model = KPIValue
        fields = [
            "id", "kpi", "kpi_code", "period_start", "period_end",
            "actual", "target", "baseline", "notes", "created_by",
            "score", "created_at"
        ]
        read_only_fields = ["id", "created_at"]

    def get_created_by(self, obj):
        """Return created_by user details."""
        if obj.created_by:
            return {
                "id": obj.created_by.id,
                "username": obj.created_by.username,
                "email": obj.created_by.email,
                "full_name": obj.created_by.get_full_name() or obj.created_by.username,
            }
        return None

    def get_score(self, obj):
        """Return associated score if exists."""
        try:
            return KPIScoreSerializer(obj.score).data
        except KPIScore.DoesNotExist:
            return None


# KPIScore Serializers
class KPIScoreSerializer(serializers.ModelSerializer):
    """Serializer for KPI Score."""
    kpi_value = serializers.StringRelatedField(read_only=True)
    kpi_code = serializers.SerializerMethodField()
    period_start = serializers.SerializerMethodField()
    period_end = serializers.SerializerMethodField()

    class Meta:
        model = KPIScore
        fields = [
            "id", "kpi_value", "kpi_code", "period_start", "period_end",
            "score", "weighted_score", "details", "computed_at"
        ]
        read_only_fields = ["id", "computed_at"]

    def get_kpi_code(self, obj):
        """Return KPI code from associated KPI value."""
        return obj.kpi_value.kpi.code

    def get_period_start(self, obj):
        """Return period start from associated KPI value."""
        return obj.kpi_value.period_start

    def get_period_end(self, obj):
        """Return period end from associated KPI value."""
        return obj.kpi_value.period_end
