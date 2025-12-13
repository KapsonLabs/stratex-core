import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ReportingPeriod(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    ANNUAL = "annual", "Annual"
    CUSTOM = "custom", "Custom"


class Direction(models.TextChoices):
    HIGHER_BETTER = "higher_is_better", "Higher is better"
    LOWER_BETTER = "lower_is_better", "Lower is better"


class IndicatorType(models.TextChoices):
    INPUT = "input", "Input"
    PROCESS = "process", "Process"
    OUTPUT = "output", "Output"
    OUTCOME = "outcome", "Outcome"


class KPI(models.Model):
    """A Key Performance Indicator for measuring performance across different levels."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True)  # e.g., "KPI-REVENUE-GROWTH"
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True)  # %, UGX, days, etc.
    direction = models.CharField(max_length=32, choices=Direction.choices, default=Direction.HIGHER_BETTER)
    indicator_type = models.CharField(max_length=32, choices=IndicatorType.choices)
    reporting_period = models.CharField(max_length=32, choices=ReportingPeriod.choices, default=ReportingPeriod.MONTHLY)
    
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)
    
    scoring_config = models.JSONField(default=dict)
    
    formula = models.TextField(blank=True, help_text="Optional expression/DSL for composite or computed KPIs")
    
    dependencies = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='dependents')
    is_composite = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)  # free-form

    # Flexible relationships to scope of measurement (kept for backward compatibility)
    financial_year = models.ForeignKey("strategy.FinancialYear", on_delete=models.CASCADE, null=True, blank=True, related_name="kpis")
    objective = models.ForeignKey("strategy.Objective", on_delete=models.CASCADE, null=True, blank=True, related_name="kpis")
    department_objective = models.ForeignKey("departments.DepartmentObjective", on_delete=models.CASCADE, null=True, blank=True, related_name="kpis")
    team_objective = models.ForeignKey("departments.TeamObjective", on_delete=models.CASCADE, null=True, blank=True, related_name="kpis")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["indicator_type"]),
            models.Index(fields=["reporting_period"]),
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.name}"


class KPIValue(models.Model):
    """Actual, target, and baseline values for a KPI over a specific time period."""

    id = models.BigAutoField(primary_key=True)
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE, related_name="values")
    period_start = models.DateField()  # canonical start of period
    period_end = models.DateField()
    actual = models.DecimalField(max_digits=16, decimal_places=6, null=True)
    target = models.DecimalField(max_digits=16, decimal_places=6, null=True)
    baseline = models.DecimalField(max_digits=16, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("kpi", "period_start", "period_end")
        indexes = [
            models.Index(fields=["kpi", "period_start"]),
        ]

    def __str__(self) -> str:
        return f"{self.kpi.code} - {self.period_start} to {self.period_end}"


class KPIScore(models.Model):
    """Computed score for a KPI value based on scoring configuration."""

    id = models.BigAutoField(primary_key=True)
    kpi_value = models.OneToOneField(KPIValue, on_delete=models.CASCADE, related_name="score")
    score = models.DecimalField(max_digits=8, decimal_places=4)  # e.g., 0-120 or % points
    weighted_score = models.DecimalField(max_digits=8, decimal_places=4)
    details = models.JSONField(default=dict)  # store rule, intermediate values, rationale
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["kpi_value"]),
        ]

    def __str__(self) -> str:
        return f"Score: {self.score} (weighted: {self.weighted_score}) for {self.kpi_value}"

