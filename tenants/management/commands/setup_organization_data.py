"""
Management command to set up organization data from legacy SQL:
- Vision and Mission
- Strategic Plan Period
- Perspectives
- Financial Years
- Objectives
- Departments
"""

from django.core.management.base import BaseCommand
from datetime import datetime

from strategy.models import (
    Organization,
    Vision,
    Mission,
    StrategicPlanPeriod,
    Perspective,
    FinancialYear,
    Objective,
)
from departments.models import Department


class Command(BaseCommand):
    help = "Set up organization data: vision, mission, strategic plan, perspectives, financial years, objectives, and departments"

    def handle(self, *args, **options):
        self.stdout.write("Setting up organization data...")

        # Get organization with id 1
        try:
            organization = Organization.objects.get(id=1)
            self.stdout.write(f"✓ Found organization: {organization.name}")
        except Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR("Organization with id 1 does not exist!"))
            return

        # 1. Create Vision
        self.stdout.write("Creating Vision...")
        vision, created = Vision.objects.get_or_create(
            organization=organization,
            statement="Vision 2030",
            defaults={},
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✓ Created Vision"))
        else:
            self.stdout.write("  Vision already exists")

        # 2. Create Mission
        self.stdout.write("Creating Mission...")
        mission, created = Mission.objects.get_or_create(
            organization=organization,
            statement="Mission 2030",
            defaults={
                "vision": vision,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✓ Created Mission"))
        else:
            self.stdout.write("  Mission already exists")

        # 3. Create Strategic Plan Period
        self.stdout.write("Creating Strategic Plan Period...")
        strategic_plan, created = StrategicPlanPeriod.objects.get_or_create(
            organization=organization,
            name="2020/21-2024/25",
            defaults={
                "vision": vision,
                "mission": mission,
                "start_year": 2020,
                "end_year": 2025,
                "status": "active",
                "description": "Strategic Plan Period 2020/21-2024/25",
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✓ Created Strategic Plan Period"))
        else:
            self.stdout.write("  Strategic Plan Period already exists")

        # 4. Create Perspectives
        self.stdout.write("Creating Perspectives...")
        perspectives_data = [
            {"name": "Customer and stakeholder", "description": ""},
            {"name": "Financial stewardship", "description": ""},
            {"name": "Business processes", "description": ""},
            {"name": "Organizational capacity", "description": ""},
        ]

        perspective_map = {}
        for persp_data in perspectives_data:
            perspective, created = Perspective.objects.get_or_create(
                strategic_plan_period=strategic_plan,
                organization=organization,
                name=persp_data["name"],
                defaults={
                    "description": persp_data["description"],
                },
            )
            perspective_map[persp_data["name"]] = perspective
            if created:
                self.stdout.write(f"  ✓ Created perspective: {perspective.name}")

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(perspective_map)} perspectives"))

        # 5. Create Financial Years
        self.stdout.write("Creating Financial Years...")
        financial_years_data = [
            {"year_label": "2025/2026", "start_date": "2025-07-01", "end_date": "2026-06-30", "status": "active"},
            {"year_label": "2024/2025", "start_date": "2024-07-01", "end_date": "2025-06-30", "status": "active"},
            {"year_label": "2023/2024", "start_date": "2023-07-01", "end_date": "2024-06-30", "status": "active"},
            {"year_label": "2022/2023", "start_date": "2022-07-01", "end_date": "2023-06-30", "status": "active"},
        ]

        financial_year_map = {}
        for fy_data in financial_years_data:
            financial_year, created = FinancialYear.objects.get_or_create(
                strategic_plan_period=strategic_plan,
                year_label=fy_data["year_label"],
                defaults={
                    "start_date": fy_data["start_date"],
                    "end_date": fy_data["end_date"],
                    "status": fy_data["status"],
                },
            )
            financial_year_map[fy_data["year_label"]] = financial_year
            if created:
                self.stdout.write(f"  ✓ Created financial year: {financial_year.year_label}")

        # Use the first active financial year for objectives
        default_financial_year = financial_year_map.get("2023/2024") or list(financial_year_map.values())[0]

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(financial_year_map)} financial years"))

        # 6. Create Objectives
        self.stdout.write("Creating Objectives...")
        objectives_data = [
            {
                "name": "Increase Communications User satisfaction",
                "perspective": "Customer and stakeholder",
                "composite_weight": 11,
                "target": "73",
                "owner_id": 1,
            },
            {
                "name": "Maximize Stakeholder Value",
                "perspective": "Customer and stakeholder",
                "composite_weight": 11,
                "target": "73",
                "owner_id": 1,
            },
            {
                "name": "Promote Sector Competitiveness",
                "perspective": "Customer and stakeholder",
                "composite_weight": 11,
                "target": "73",
                "owner_id": 1,
            },
            {
                "name": "Optimize Resources",
                "perspective": "Financial stewardship",
                "composite_weight": 11,
                "target": "98",
                "owner_id": 1,
            },
            {
                "name": "Improve Regulatory Processes",
                "perspective": "Business processes",
                "composite_weight": 11,
                "target": "95",
                "owner_id": 1,
            },
            {
                "name": "Strengthen Stakeholder Collaboration",
                "perspective": "Business processes",
                "composite_weight": 11,
                "target": "95",
                "owner_id": 1,
            },
            {
                "name": "Improve Tools & Technology",
                "perspective": "Organizational capacity",
                "composite_weight": 11,
                "target": "84",
                "owner_id": 1,
            },
            {
                "name": "Enhance Organizational Culture",
                "perspective": "Organizational capacity",
                "composite_weight": 11,
                "target": "84",
                "owner_id": 1,
            },
            {
                "name": "Improve Knowledge Skills and Abilities",
                "perspective": "Organizational capacity",
                "composite_weight": 11,
                "target": "84",
                "owner_id": 1,
            },
        ]

        objective_map = {}
        for obj_data in objectives_data:
            perspective = perspective_map.get(obj_data["perspective"])
            if not perspective:
                self.stdout.write(self.style.WARNING(f"  ⚠ Skipping objective '{obj_data['name']}' - perspective not found"))
                continue

            objective, created = Objective.objects.get_or_create(
                perspective=perspective,
                financial_year=default_financial_year,
                organization=organization,
                name=obj_data["name"],
                defaults={
                    "composite_weight": obj_data["composite_weight"],
                    "target": obj_data["target"],
                    "owner_id": obj_data["owner_id"],
                },
            )
            objective_map[obj_data["name"]] = objective
            if created:
                self.stdout.write(f"  ✓ Created objective: {objective.name}")

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(objective_map)} objectives"))

        # 7. Create Departments
        self.stdout.write("Creating Departments...")
        departments_data = [
            {
                "name": "Legal",
                "description": "To Provide Expert & Efficient Legal Advisory & Procurement services to facilitate execution of the Commissions Mandate",
                "head_id": 1,
            },
            {
                "name": "Corporate Affairs",
                "description": "To Facilitate the Development & Implementation of UCC's Strategy and Strengthen Credibility that Fosters Sustainable Relationships for the Commission",
                "head_id": 1,
            },
            {
                "name": "Industry Affairs and Content",
                "description": "Promote Industry Competitiveness & Consumer Protection for Quality Communication User Experience",
                "head_id": 1,
            },
            {
                "name": "Engineering & Communication Infrastructure",
                "description": "To Develop & Implement Innovative & Responsive Technical Regulatory Tools that Drive the Development of the Communications Sector",
                "head_id": 1,
            },
            {
                "name": "Human Resources and Administration",
                "description": "To Provide Innovative Human Resource Solutions & Efficient Administrative Services that Delivers a Conducive Workplace which Promotes a Productive Workforce & Operational Efficiency",
                "head_id": 1,
            },
            {
                "name": "Uganda Communications Universal Service Access Fund",
                "description": "To Facilitate Universal Access to Communication Services in Uganda",
                "head_id": 1,
            },
            {
                "name": "ICT & Research",
                "description": "To Enhance Our Customers Decision through Knowledge Generation and Innovative ICT Solutions",
                "head_id": 1,
            },
            {
                "name": "Internal Audit",
                "description": "To Provide Objective Independent Assurance & Advisory Services that Minimize Organizational Risks, Improve Controls and Enhance Governance",
                "head_id": 1,
            },
            {
                "name": "Finance",
                "description": "To Provide Professional & Efficient Financial Management & Advisory Services That Optimises Resource use in UCC",
                "head_id": 1,
            },
        ]

        department_map = {}
        for dept_data in departments_data:
            department, created = Department.objects.get_or_create(
                organization=organization,
                name=dept_data["name"],
                defaults={
                    "description": dept_data["description"],
                    "head_id": dept_data["head_id"],
                    "status": "active",
                },
            )
            department_map[dept_data["name"]] = department
            if created:
                self.stdout.write(f"  ✓ Created department: {department.name}")

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(department_map)} departments"))

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Organization data setup completed successfully!"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Organization: {organization.name}")
        self.stdout.write(f"Vision: {vision.statement[:50]}...")
        self.stdout.write(f"Mission: {mission.statement[:50]}...")
        self.stdout.write(f"Strategic Plan Periods: {StrategicPlanPeriod.objects.filter(organization=organization).count()}")
        self.stdout.write(f"Perspectives: {Perspective.objects.filter(organization=organization).count()}")
        self.stdout.write(f"Financial Years: {FinancialYear.objects.filter(strategic_plan_period=strategic_plan).count()}")
        self.stdout.write(f"Objectives: {Objective.objects.filter(organization=organization).count()}")
        self.stdout.write(f"Departments: {Department.objects.filter(organization=organization).count()}")
        self.stdout.write("=" * 60)

