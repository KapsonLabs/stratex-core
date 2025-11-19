from django.db import models
from django.core.exceptions import ValidationError


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

    department_objective_name = models.CharField(max_length=255, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="department_objectives")
    composite_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, help_text="Composite weight of the objective")
    objective = models.ForeignKey("strategy.Objective", on_delete=models.CASCADE, related_name="department_objectives")
    objective_target = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.department.name} - {self.department_objective_name}"


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
    team_objective_name = models.CharField(max_length=255)
    objective_target = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    team_objective_description = models.TextField(blank=True)
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


class Employee(models.Model):
    """An employee linked to a user, department, and optionally a team."""

    related_user = models.OneToOneField(
        "accounts.User", 
        on_delete=models.CASCADE, 
        related_name="employee_profile",
        help_text="The user account associated with this employee"
    )
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE, 
        related_name="employees"
    )
    team = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="employees",
        help_text="Optional team assignment"
    )
    job_title = models.CharField(max_length=255, help_text="Job title or position")
    is_department_head = models.BooleanField(
        default=False,
        help_text="Whether this employee is the head of the department. Only one employee per department can be head."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_department_head", "job_title"]
        indexes = [
            models.Index(fields=["department", "is_department_head"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["department"],
                condition=models.Q(is_department_head=True),
                name="unique_department_head"
            ),
        ]

    def clean(self):
        """Validate that only one department head exists per department."""
        if self.is_department_head:
            existing_head = Employee.objects.filter(
                department=self.department,
                is_department_head=True
            ).exclude(pk=self.pk if self.pk else None)
            if existing_head.exists():
                raise ValidationError(
                    f"Department '{self.department.name}' already has a head assigned. "
                    "Only one employee per department can be designated as department head."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        user_name = self.related_user.get_full_name() or self.related_user.username
        return f"{user_name} - {self.job_title} ({self.department.name})"


class EmployeeReportingLine(models.Model):
    """Represents reporting relationships between employees."""

    RELATIONSHIP_TYPE_CHOICES = [
        ("line_manager", "Line Manager"),
        ("functional_manager", "Functional Manager"),
        ("supervisor", "Supervisor"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="reporting_lines",
        help_text="The employee who reports"
    )
    reports_to = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="direct_reports",
        help_text="The employee being reported to"
    )
    relationship_type = models.CharField(
        max_length=50,
        choices=RELATIONSHIP_TYPE_CHOICES,
        help_text="Type of reporting relationship"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [["employee", "reports_to", "relationship_type"]]
        indexes = [
            models.Index(fields=["employee", "relationship_type"]),
            models.Index(fields=["reports_to", "relationship_type"]),
        ]

    def clean(self):
        """Validate that an employee cannot report to themselves."""
        if self.employee_id and self.reports_to_id and self.employee_id == self.reports_to_id:
            raise ValidationError("An employee cannot report to themselves.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.employee} reports to {self.reports_to} ({self.get_relationship_type_display()})"
