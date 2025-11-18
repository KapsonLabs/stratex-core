from django.db import models


class Organization(models.Model):
    """An organization belongs to a tenant."""

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="organizations")
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [["tenant", "name"]]

    def __str__(self) -> str:
        return self.name


class Vision(models.Model):
    """Strategic vision statement for the organization."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="visions")
    statement = models.TextField(help_text="The vision statement")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Vision (ID: {self.id})"


class Mission(models.Model):
    """Strategic mission statement for the organization."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="missions")
    statement = models.TextField(help_text="The mission statement")
    vision = models.OneToOneField(Vision, on_delete=models.CASCADE, related_name="mission", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Mission (ID: {self.id})"


class StrategicPlanPeriod(models.Model):
    """A strategic planning period (e.g., 2025-2030)."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="strategic_plan_periods")
    vision = models.ForeignKey(Vision, on_delete=models.CASCADE, related_name="strategic_plan_periods")
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="strategic_plan_periods")
    name = models.CharField(max_length=255, help_text="e.g., '2025-2030 Strategic Plan'")
    start_year = models.IntegerField()
    end_year = models.IntegerField()
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_year", "-end_year"]

    def __str__(self) -> str:
        return self.name


class FinancialYear(models.Model):
    """Financial year within a strategic plan period."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed"),
    ]

    strategic_plan_period = models.ForeignKey(
        StrategicPlanPeriod, on_delete=models.CASCADE, related_name="financial_years"
    )
    year_label = models.CharField(max_length=50, help_text="e.g., '2025/2026'")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return self.year_label


class Perspective(models.Model):
    """A strategic perspective (e.g., Financial, Customer, Internal Process, Learning & Growth)."""

    strategic_plan_period = models.ForeignKey(
        StrategicPlanPeriod, on_delete=models.CASCADE, related_name="perspectives"
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="perspectives")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Objective(models.Model):
    """A strategic objective tied to a perspective and financial year."""

    perspective = models.ForeignKey(Perspective, on_delete=models.CASCADE, related_name="objectives")
    financial_year = models.ForeignKey(FinancialYear, on_delete=models.CASCADE, related_name="objectives")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="objectives")
    name = models.CharField(max_length=255)
    composite_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, help_text="Composite weight of the objective")
    description = models.TextField(blank=True)
    target = models.TextField(blank=True, help_text="Target or goal description")
    owner_id = models.IntegerField(null=True, blank=True, help_text="User ID of the objective owner")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
