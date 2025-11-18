from django.db import models


class Department(models.Model):
    """A department within an organization."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("archived", "Archived"),
    ]

    organization = models.ForeignKey("strategy.Organization", on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=255)
    head_id = models.IntegerField(null=True, blank=True, help_text="User ID of the department head")
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [["organization", "name"]]

    def __str__(self) -> str:
        return self.name


class DepartmentObjective(models.Model):
    """A department's objective derived from a strategic objective."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="department_objectives")
    composite_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, help_text="Composite weight of the objective")
    objective = models.ForeignKey("strategy.Objective", on_delete=models.CASCADE, related_name="department_objectives")
    target = models.TextField(help_text="Target or goal for the department")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.department.name} - {self.objective.name}"


class Team(models.Model):
    """A team within a department."""

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=255)
    lead_id = models.IntegerField(null=True, blank=True, help_text="User ID of the team lead")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [["department", "name"]]

    def __str__(self) -> str:
        return self.name


class TeamObjective(models.Model):
    """A team's objective derived from a department objective."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="team_objectives")
    dept_objective = models.ForeignKey(DepartmentObjective, on_delete=models.CASCADE, related_name="team_objectives")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.team.name} - {self.dept_objective.objective.name}"


class KPI(models.Model):
    """A Key Performance Indicator applicable at strategic, department, or team level."""

    LEVEL_CHOICES = [
        ("strategic", "Strategic"),
        ("department", "Department"),
        ("team", "Team")
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    formula = models.CharField(max_length=255, blank=True, help_text="Formula or method to calculate the KPI")
    target_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, help_text="Unit of measurement (e.g., %, $, hours)")
    frequency = models.CharField(max_length=50, blank=True, help_text="e.g., monthly, quarterly")
    status = models.CharField(max_length=50, blank=True, help_text="e.g., On Track, Behind")
    owner_id = models.IntegerField(null=True, blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="team")

    # Flexible relationships to scope of measurement
    financial_year = models.ForeignKey("strategy.FinancialYear", on_delete=models.CASCADE, null=True, blank=True, related_name="kpis")
    objective = models.ForeignKey("strategy.Objective", on_delete=models.CASCADE, null=True, blank=True, related_name="kpis")
    department_objective = models.ForeignKey("departments.DepartmentObjective", on_delete=models.CASCADE, null=True, blank=True, related_name="kpis")
    team_objective = models.ForeignKey("departments.TeamObjective", on_delete=models.CASCADE, null=True, blank=True, related_name="kpis")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.name


class KPIScore(models.Model):
    """Time-based scores/measurements for a KPI."""

    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE, related_name="scores")
    period_label = models.CharField(max_length=50, blank=True, help_text="e.g., 2025-Q1, 2025-01")
    date = models.DateField(null=True, blank=True)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]


class Initiative(models.Model):
    """An initiative undertaken by a team to achieve objectives."""

    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("on_hold", "On Hold"),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="initiatives")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return self.name
