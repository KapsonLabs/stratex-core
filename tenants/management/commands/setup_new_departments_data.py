"""
Management command to set up departments and department objectives from legacy SQL data.
"""

from django.core.management.base import BaseCommand
from decimal import Decimal
from datetime import date
from calendar import monthrange
import re
import hashlib

from strategy.models import Organization, Objective
from departments.models import Department, DepartmentObjective, Team, TeamObjective
from strategy.models import FinancialYear, StrategicPlanPeriod, Perspective, Mission, Vision, Organization, Objective
from indicators.models import (
    KPI, KPIValue, KPIScore,
    ReportingPeriod, Direction, IndicatorType
)


class Command(BaseCommand):
    help = "Set up departments and department objectives from legacy SQL data"

    def generate_kpi_code(self, name: str, dept_obj_id: int = None, team_obj_id: int = None) -> str:
        """Generate a unique KPI code from name and context."""
        # Clean name: remove special chars, convert to uppercase, replace spaces with hyphens
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        clean_name = re.sub(r'\s+', '-', clean_name.strip())
        clean_name = clean_name.upper()
        
        # Limit length
        if len(clean_name) > 40:
            clean_name = clean_name[:40]
        
        # Add context if needed for uniqueness
        prefix = "KPI"
        if dept_obj_id:
            prefix = f"KPI-DEPT-{dept_obj_id}"
        elif team_obj_id:
            prefix = f"KPI-TEAM-{team_obj_id}"
        
        code = f"{prefix}-{clean_name}"
        
        # Ensure uniqueness by checking and appending hash if needed
        if KPI.objects.filter(code=code).exists():
            hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8].upper()
            code = f"{code}-{hash_suffix}"
        
        return code

    def infer_direction(self, name: str, formula: str = "") -> str:
        """Infer if higher or lower is better based on KPI name and formula."""
        name_lower = name.lower()
        formula_lower = formula.lower() if formula else ""
        combined = f"{name_lower} {formula_lower}"
        
        # Lower is better indicators
        lower_indicators = [
            "reduce", "decrease", "minimize", "below", "debt", "debtor", "creditor",
            "rolled over", "rolled-over", "cost", "expenditure", "time taken",
            "turnaround", "response time", "waiting", "delay", "error", "failure"
        ]
        
        for indicator in lower_indicators:
            if indicator in combined:
                return Direction.LOWER_BETTER
        
        # Default to higher is better
        return Direction.HIGHER_BETTER

    def infer_indicator_type(self, name: str, formula: str = "") -> str:
        """Infer indicator type based on KPI name and formula."""
        name_lower = name.lower()
        formula_lower = formula.lower() if formula else ""
        combined = f"{name_lower} {formula_lower}"
        
        # Outcome indicators (results, impacts)
        outcome_keywords = [
            "satisfaction", "growth", "revenue", "achieved", "attained", "met",
            "targets achieved", "success", "productivity", "retention", "performance"
        ]
        
        # Output indicators (deliverables)
        output_keywords = [
            "completed", "delivered", "produced", "issued", "published", "submitted",
            "resolved", "addressed", "implemented", "executed", "initiated"
        ]
        
        # Process indicators (efficiency, timeliness)
        process_keywords = [
            "timeliness", "within", "days", "weeks", "time", "efficiency", "turnaround",
            "response", "cycle", "process", "workflow", "utilization", "availability"
        ]
        
        # Input indicators (resources, capacity)
        input_keywords = [
            "budget", "resources", "staff", "trained", "capacity", "allocation",
            "funding", "investment"
        ]
        
        if any(kw in combined for kw in outcome_keywords):
            return IndicatorType.OUTCOME
        elif any(kw in combined for kw in output_keywords):
            return IndicatorType.OUTPUT
        elif any(kw in combined for kw in process_keywords):
            return IndicatorType.PROCESS
        elif any(kw in combined for kw in input_keywords):
            return IndicatorType.INPUT
        
        # Default to process
        return IndicatorType.PROCESS

    def infer_reporting_period(self, name: str, formula: str = "") -> str:
        """Infer reporting period based on KPI name and formula."""
        name_lower = name.lower()
        formula_lower = formula.lower() if formula else ""
        combined = f"{name_lower} {formula_lower}"
        
        if "daily" in combined or "day" in combined and "days" not in combined:
            return ReportingPeriod.DAILY
        elif "weekly" in combined or "week" in combined:
            return ReportingPeriod.WEEKLY
        elif "quarterly" in combined or "quarter" in combined:
            return ReportingPeriod.QUARTERLY
        elif "annual" in combined or "year" in combined or "fy" in combined:
            return ReportingPeriod.ANNUAL
        else:
            # Default to monthly
            return ReportingPeriod.MONTHLY

    def infer_scoring_config(self, name: str, target: Decimal = None) -> dict:
        """Infer appropriate scoring configuration based on KPI characteristics."""
        name_lower = name.lower()
        
        # Check if it's a percentage-based KPI
        is_percentage = "%" in name or "percentage" in name_lower or "rate" in name_lower
        
        # For percentage KPIs with specific targets, use threshold scoring
        if is_percentage and target:
            # Determine if it's a high-stakes KPI (satisfaction, quality, etc.)
            high_stakes_keywords = ["satisfaction", "quality", "compliance", "availability", "uptime"]
            is_high_stakes = any(kw in name_lower for kw in high_stakes_keywords)
            
            if is_high_stakes:
                # Threshold scoring for high-stakes KPIs
                return {
                    "type": "threshold",
                    "thresholds": [
                        {"min": 0, "max": 0.7, "score": 50},
                        {"min": 0.7, "max": 0.85, "score": 75},
                        {"min": 0.85, "max": 1.0, "score": 100},
                        {"min": 1.0, "max": 2.0, "score": 120}
                    ],
                    "null_policy": "use_baseline"
                }
            else:
                # Linear scoring for standard percentage KPIs
                return {
                    "type": "linear",
                    "floor": 0,
                    "cap": 100,
                    "null_policy": "zero"
                }
        
        # For score-based KPIs (satisfaction scores, etc.)
        if "score" in name_lower:
            return {
                "type": "threshold",
                "thresholds": [
                    {"min": 0, "max": 0.6, "score": 40},
                    {"min": 0.6, "max": 0.75, "score": 70},
                    {"min": 0.75, "max": 1.0, "score": 100},
                    {"min": 1.0, "max": 2.0, "score": 120}
                ],
                "null_policy": "use_baseline"
            }
        
        # Default to linear scoring
        return {
            "type": "linear",
            "floor": 0,
            "cap": 100,
            "null_policy": "zero"
        }

    def infer_dept_objective_for_team_obj(self, team_obj_data: dict, dept_objectives_map: dict) -> int:
        """
        Infer the correct department objective ID for a team objective based on:
        1. The team's department
        2. Semantic similarity between titles
        3. Keywords matching
        
        Args:
            team_obj_data: Dictionary containing team objective data with 'title' and 'team' keys
            dept_objectives_map: Dictionary mapping dept_obj_id -> {'title': str, 'department_id': int, ...}
            
        Returns:
            int: The inferred department objective ID
        """
        team_id = team_obj_data.get("team")
        team_obj_title = team_obj_data.get("title", "").lower()
        
        # Map team_id to department_id based on teams_data structure
        # Teams: 1-3 (dept 2), 4-8 (dept 1), 9-10,26 (dept 5), 11-13 (dept 9), 14-15 (dept 8),
        # 16-17 (dept 4), 18 (dept 6), 19-22 (dept 7), 23-25 (dept 3)
        team_to_dept_map = {
            1: 2, 2: 2, 3: 2,  # PIR, SBP, Regional Offices -> Corporate Affairs
            4: 1, 5: 1, 6: 1, 7: 1, 8: 1,  # Legal teams
            9: 5, 10: 5, 26: 5,  # HRA teams
            11: 9, 12: 9, 13: 9,  # Finance teams
            14: 8, 15: 8,  # Internal Audit teams
            16: 4, 17: 4,  # ECI teams
            18: 6,  # UCUSAF
            19: 7, 20: 7, 21: 7, 22: 7,  # ICT & Research teams
            23: 3, 24: 3, 25: 3, 32: 3, 30: 3, 31: 3, 33: 3,  # IAC teams
        }
        
        department_id = team_to_dept_map.get(team_id)
        if not department_id:
            # Default fallback - use first available dept objective
            return list(dept_objectives_map.keys())[0] if dept_objectives_map else None
        
        # Filter department objectives by department
        candidate_dept_objs = {
            obj_id: obj for obj_id, obj in dept_objectives_map.items()
            if obj.get("department") == department_id or obj.get("department_id") == department_id
        }
        
        if not candidate_dept_objs:
            # If no exact match, try to find any suitable one
            candidate_dept_objs = dept_objectives_map
        
        # Score each candidate based on keyword matching
        best_match_id = None
        best_score = 0
        
        for obj_id, obj in candidate_dept_objs.items():
            dept_obj_title = obj.get("title", "").lower()
            score = 0
            
            # Exact phrase matches (highest priority)
            if team_obj_title in dept_obj_title or dept_obj_title in team_obj_title:
                score += 100
            
            # Keyword matching
            team_keywords = set(team_obj_title.split())
            dept_keywords = set(dept_obj_title.split())
            common_keywords = team_keywords & dept_keywords
            score += len(common_keywords) * 10
            
            # Specific important keyword matches
            important_keywords = [
                "stakeholder", "compliance", "financial", "reporting", "revenue", "expenditure",
                "audit", "risk", "procurement", "legal", "litigation", "board", "governance",
                "satisfaction", "productivity", "efficiency", "resources", "budget", "tools",
                "technology", "skills", "knowledge", "project", "monitoring", "quality",
                "cyber", "security", "information", "knowledge", "communication", "spectrum",
                "complaints", "timely", "timeliness", "operational", "business", "process"
            ]
            
            for keyword in important_keywords:
                if keyword in team_obj_title and keyword in dept_obj_title:
                    score += 15
            
            # Team-specific keyword matching
            if team_id == 6 or "legal affairs" in team_obj_title:
                if "legal" in dept_obj_title or "stakeholder" in dept_obj_title:
                    score += 20
            elif team_id == 7 or "compliance" in team_obj_title:
                if "compliance" in dept_obj_title or "regulatory" in dept_obj_title:
                    score += 20
            elif team_id == 8 or "procurement" in team_obj_title:
                if "procurement" in dept_obj_title or "resources" in dept_obj_title:
                    score += 20
            elif team_id in [11, 12, 13] or "revenue" in team_obj_title or "expenditure" in team_obj_title:
                if "revenue" in dept_obj_title or "expenditure" in dept_obj_title or "financial" in dept_obj_title:
                    score += 20
            elif team_id in [14, 15] or "audit" in team_obj_title:
                if "audit" in dept_obj_title or "governance" in dept_obj_title or "risk" in dept_obj_title:
                    score += 20
            elif team_id == 18 or "ucusaf" in team_obj_title or "project" in team_obj_title:
                if "project" in dept_obj_title or "stakeholder" in dept_obj_title:
                    score += 20
            elif team_id in [19, 20, 21, 22] or "ict" in team_obj_title or "cyber" in team_obj_title:
                if "cyber" in dept_obj_title or "tools" in dept_obj_title or "technology" in dept_obj_title:
                    score += 20
            elif team_id in [23, 24, 25, 30, 31, 32, 33] or "consumer" in team_obj_title or "complaints" in team_obj_title:
                if "complaints" in dept_obj_title or "information" in dept_obj_title or "regulatory" in dept_obj_title:
                    score += 20
            
            if score > best_score:
                best_score = score
                best_match_id = obj_id
        
        # If we found a good match, return it
        if best_match_id and best_score > 0:
            return best_match_id
        
        # Fallback: return first department objective for the team's department
        return list(candidate_dept_objs.keys())[0] if candidate_dept_objs else list(dept_objectives_map.keys())[0]

    def handle(self, *args, **options):
        self.stdout.write("Setting up organization, departments and department objectives...")

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
            {"year_label": "2021/2022", "start_date": "2021-07-01", "end_date": "2022-06-30", "status": "active"},
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

        # Get organization with id 1
        try:
            organization = Organization.objects.get(id=1)
            self.stdout.write(f"✓ Found organization: {organization.name}")
        except Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR("Organization with id 1 does not exist!"))
            return

        # 6. Create Objectives
        self.stdout.write("Creating Objectives...")
        objectives_data = [
            {
                "id": 1,
                "name": "Increase Communications User satisfaction",
                "perspective": 1,
                "composite_weight": 11,
                "target": "73",
                "owner_id": 1,
            },
            {
                "id": 2,
                "name": "Maximize Stakeholder Value",
                "perspective": 1,
                "composite_weight": 11,
                "target": "73",
                "owner_id": 1,
            },
            {
                "id": 3,
                "name": "Promote Sector Competitiveness",
                "perspective": 1,
                "composite_weight": 11,
                "target": "73",
                "owner_id": 1,
            },
            {
                "id": 4,
                "name": "Optimize Resources",
                "perspective": 2,
                "composite_weight": 11,
                "target": "98",
                "owner_id": 1,
            },
            {
                "id": 5,
                "name": "Improve Regulatory Processes",
                "perspective": 3,
                "composite_weight": 11,
                "target": "95",
                "owner_id": 1,
            },
            {
                "id": 6,
                "name": "Strengthen Stakeholder Collaboration",
                "perspective": 3,
                "composite_weight": 11,
                "target": "95",
                "owner_id": 1,
            },
            {
                "id": 7,
                "name": "Improve Tools & Technology",
                "perspective": 4,
                "composite_weight": 11,
                "target": "84",
                "owner_id": 1,
            },
            {
                "id": 8,
                "name": "Enhance Organizational Culture",
                "perspective": 4,
                "composite_weight": 11,
                "target": "84",
                "owner_id": 1,
            },
            {
                "id": 9,
                "name": "Improve Knowledge Skills and Abilities",
                "perspective": 4,
                "composite_weight": 11,
                "target": "84",
                "owner_id": 1,
            },
        ]

        objective_map = {}
        for obj_data in objectives_data:
            perspective = Perspective.objects.get(id=obj_data["perspective"])
            objective, created = Objective.objects.get_or_create(
                financial_year=FinancialYear.objects.get(id=1),
                organization=organization,
                name=obj_data["name"],
                defaults={
                    "id": obj_data["id"],
                    "perspective": perspective,
                    "composite_weight": obj_data["composite_weight"],
                    "target": obj_data["target"],
                    "owner_id": obj_data["owner_id"],
                },
            )
            objective_map[obj_data["name"]] = objective
            if created:
                self.stdout.write(f"  ✓ Created objective: {objective.name}")

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(objective_map)} objectives"))

        # 1. Create or get Departments
        self.stdout.write("Creating/Getting Departments...")
        department_map = {}
        departments_data = departments_data = [
            {
                "id": 1,
                "name": "Legal",
                "description": "To Provide Expert & Efficient Legal Advisory & Procurement services to facilitate execution of the Commissions Mandate",
                "head_id": 1,
            },
            {
                "id": 2,
                "name": "Corporate Affairs",
                "description": "To Facilitate the Development & Implementation of UCC's Strategy and Strengthen Credibility that Fosters Sustainable Relationships for the Commission",
                "head_id": 1,
            },
            {
                "id": 3,
                "name": "Industry Affairs and Content",
                "description": "Promote Industry Competitiveness & Consumer Protection for Quality Communication User Experience",
                "head_id": 1,
            },
            {
                "id": 4,
                "name": "Engineering & Communication Infrastructure",
                "description": "To Develop & Implement Innovative & Responsive Technical Regulatory Tools that Drive the Development of the Communications Sector",
                "head_id": 1,
            },
            {
                "id": 5,
                "name": "Human Resources and Administration",
                "description": "To Provide Innovative Human Resource Solutions & Efficient Administrative Services that Delivers a Conducive Workplace which Promotes a Productive Workforce & Operational Efficiency",
                "head_id": 1,
            },
            {
                "id": 6,
                "name": "Uganda Communications Universal Service Access Fund",
                "description": "To Facilitate Universal Access to Communication Services in Uganda",
                "head_id": 1,
            },
            {
                "id": 7,
                "name": "ICT & Research",
                "description": "To Enhance Our Customers Decision through Knowledge Generation and Innovative ICT Solutions",
                "head_id": 1,
            },
            {
                "id": 8,
                "name": "Internal Audit",
                "description": "To Provide Objective Independent Assurance & Advisory Services that Minimize Organizational Risks, Improve Controls and Enhance Governance",
                "head_id": 1,
            },
            {
                "id": 9,
                "name": "Finance",
                "description": "To Provide Professional & Efficient Financial Management & Advisory Services That Optimises Resource use in UCC",
                "head_id": 1,
            },
        ]

        for dept_data in departments_data:
            department, created = Department.objects.get_or_create(
                organization=organization,
                name=dept_data["name"],
                defaults={
                    "id": dept_data["id"],
                    "description": dept_data["description"],
                    "head_id": dept_data["head_id"],
                    "status": "active",
                },
            )
            department_map[dept_data["name"]] = department
            if created:
                self.stdout.write(f"  ✓ Created department: {department.name}")

        self.stdout.write(self.style.SUCCESS(f"✓ Processed {len(department_map)} departments"))

        # 2. Get all strategic objectives to map old IDs to new objects
        self.stdout.write("Mapping strategic objectives...")
        objectives = Objective.objects.filter(organization=organization)
        objective_map = {}
        for obj in objectives:
            # Map by name since we don't have old IDs
            objective_map[obj.name] = obj

        self.stdout.write(f"✓ Found {len(objective_map)} strategic objectives")

        # 3. Create Department Objectives
        self.stdout.write("Creating Department Objectives...")
        dept_objectives_data = [
            {"id": 1, "title": "Increase Stakeholder satisfaction", "department": 1, "composite_weight": 70, "target": 70, "objective": 1, "status": "active"},
            {"id": 2, "title": "Strengthen Regulatory Frameworks", "department": 1, "composite_weight": 80,  "target": 70, "objective": 5, "status": "active"},
            {"id": 3, "title": "Optimize Resources", "department": 1, "composite_weight": 80, "target": 75, "objective": 4, "status": "active"},
            {"id": 4, "title": "Improve Board, Legal and PDU Compliance Management", "department": 1, "composite_weight": 80, "target": 80, "objective": 6, "status": "active"},
            {"id": 5, "title": "Improve Board, Legal and PDU Process Efficiency", "department": 1, "composite_weight": 70, "target": 70, "objective": 6, "status": "active"},
            {"id": 6, "title": "Strengthen Legal and PDU Risk Management", "department": 1, "composite_weight": 70, "target": 70, "objective": 6, "status": "active"},
            {"id": 7, "title": "Promote use of communication services", "department": 6, "composite_weight": 11, "target": 60, "objective": 1, "status": "active"},
            {"id": 8, "title": "Improve UCUSAF operational efficiency", "department": 6, "composite_weight": 11, "target": 60, "objective": 4, "status": "active"},
            {"id": 9, "title": "Increase project monitoring turnaround", "department": 6, "composite_weight": 80, "target": 80, "objective": 4, "status": "active"},
            {"id": 10, "title": "Improve project conceptualization", "department": 6, "composite_weight": 90, "target": 90, "objective": 4, "status": "active"},
            {"id": 11, "title": "Improve contract management", "department": 6, "composite_weight": 90, "target": 90, "objective": 4, "status": "active"},
            {"id": 12, "title": "Decrease Number of Rolled Over projects", "department": 6, "composite_weight": 25, "target": 65, "objective": 4, "status": "active"},
            {"id": 13, "title": "Strengthen stakeholder relationships", "department": 6, "composite_weight": 80, "target": 85, "objective": 6, "status": "active"},
            {"id": 14, "title": "Improve Resource Mobilisation and Use", "department": 9, "composite_weight": 100, "target": 70, "objective": 4, "status": "active"},
            {"id": 15, "title": "Increase Customer & Stakeholder Satisfaction", "department": 9, "composite_weight": 80, "target": 80, "objective": 1, "status": "active"},
            {"id": 16, "title": "Enhance Financial Accountability", "department": 9, "composite_weight": 80, "target": 80, "objective": 6, "status": "active"},
            {"id": 17, "title": "Improve Revenue Management", "department": 9, "composite_weight": 100, "target": 70, "objective": 4, "status": "active"},
            {"id": 18, "title": "Strengthen Expenditure Management", "department": 9, "composite_weight": 85, "target": 85, "objective": 4, "status": "active"},
            {"id": 19, "title": "Strengthen Financial Reporting", "department": 9, "composite_weight": 90, "target": 90, "objective": 6, "status": "active"},
            {"id": 20, "title": "Enhance Planning & Budgeting", "department": 9, "composite_weight": 100, "target": 100, "objective": 4, "status": "active"},
            {"id": 21, "title": "Improve DF Skills, Knowledge & Abilities", "department": 9, "composite_weight": 100, "target": 100, "objective": 9, "status": "active"},
            {"id": 22, "title": "Improve customer & stakeholder satisfaction", "dept_name": "Human Resources and Administration", "composite_weight": 80, "target": 80, "objective": 6, "status": "active"},
            {"id": 23, "title": "Increase employee productivity", "dept_name": "Human Resources and Administration", "composite_weight": 88, "target": 88, "objective": 9, "status": "active"},
            {"id": 24, "title": "Optimize HRA resources", "dept_name": "Human Resources and Administration", "composite_weight": 95, "target": 95, "objective": 4, "status": "active"},
            {"id": 25, "title": "Improve HRA operational efficiency", "dept_name": "Human Resources and Administration", "composite_weight": 11, "target": 60, "objective": 4, "status": "active"},
            {"id": 26, "title": "Enhance UCC Business success", "dept_name": "Legal", "composite_weight": 80, "target": 75, "objective": 7, "status": "active"},
            {"id": 27, "title": "Staff Performance", "dept_name": "Legal", "composite_weight": 80, "target":70, "objective": 9, "status": "active"},
            {"id": 28, "title": "Improve/Promote good governance", "dept_name": "Internal Audit", "composite_weight": 75, "target": 75, "objective": 2, "status": "active"},
            {"id": 29, "title": "Improve HRA tools & Technology", "dept_name": "Human Resources and Administration", "composite_weight": 11, "target": 60, "objective": 7, "status": "active"},
            {"id": 30, "title": "Improve timely conclusion of complaints •Consumer complaints •Content complaints •Licensee disputes", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective": 6, "status": "active"},
            {"id": 31, "title": "Improve the timely availability of information to stakeholders •Market reports •Consumer advisories •Content quota reports •Competition scans", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective": 6, "status": "active"},
            {"id": 32, "title": "Reduce cost of doing business/operation", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective": 4, "status": "active"},
            {"id": 33, "title": "Enhance Stakeholder Collaboration", "dept_name": "Internal Audit", "composite_weight": 75, "target": 75, "objective": 2, "status": "active"},
            {"id": 34, "title": "Optimise Financial Resource Use", "dept_name": "Internal Audit", "composite_weight": 90, "target": 90, "objective": 4, "status": "active"},
            {"id": 35, "title": "Improve quality of audit services", "dept_name": "Internal Audit", "composite_weight": 80, "target": 80, "objective": 2, "status": "active"},
            {"id": 36, "title": "Enhance UCC business process", "dept_name": "Internal Audit", "composite_weight": 70, "target": 70, "objective": 6, "status": "active"},
            {"id": 37, "title": "Strengthen coordination of Risk management", "dept_name": "Internal Audit", "composite_weight": 70, "target": 70, "objective": 2, "status": "active"},
            {"id": 38, "title": "Improve responsiveness of the regulatory frameworks and standards", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective": 5, "status": "active"},
            {"id": 39, "title": "Improve the timeliness of DIAC's plan execution, compliance activities and assessment decisions", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective": 5, "status": "active"},
            {"id": 40, "title": "Improve IAC Tools & Technology capability for better work environment & processes •Online data portal •Digital logger •Call Centre", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective": 7, "status": "active"},
            {"id": 41, "title": "Strengthen Internal Compliance Monitoring", "dept_name": "Internal Audit", "composite_weight": 80, "target": 80, "objective": 6, "status": "active"},
            {"id": 42, "title": "Improve Quality of Communication services offered by Licensees", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 11, "target": 60, "objective": 3, "status": "active"},
            {"id": 43, "title": "Improve IA Tools and Technologies", "dept_name": "Internal Audit", "composite_weight": 80, "target": 80, "objective": 7, "status": "active"},
            {"id": 44, "title": "Improve IA Skills, knowledge and Abilities", "dept_name": "Internal Audit", "composite_weight": 75, "target": 75, "objective": 9, "status": "active"},
            {"id": 45, "title": "Improve utilization of Communication Resources (Spectrum, Numbering and Electronic Addressing/LCNs)", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 80, "target": 80, "objective": 4, "status": "active"},
            {"id": 46, "title": "Improve the timeliness of ECI's actions, compliance activities and assessment decisions", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 83, "target": 83, "objective": 5, "status": "active"},
            {"id": 47, "title": "Improve availability of our technical tools to be used when required", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 80, "target": 80, "objective": 7, "status": "active"},
            {"id": 48, "title": "Improve customer and stakeholder satisfaction", "dept_name": "ICT & Research", "composite_weight": 80, "objective": 6, "status": "active"},
            {"id": 49, "title": "Improve cyber security", "dept_name": "ICT & Research", "composite_weight": 60, "target": 60, "objective": 1, "status": "active"},
            {"id": 50, "title": "Optimize ICT&R resources", "dept_name": "ICT & Research", "composite_weight": 100, "target": 100, "objective": 4, "status": "active"},
            {"id": 51, "title": "Strengthen risk Management", "dept_name": "ICT & Research", "composite_weight": 80, "target": 80, "objective": 6, "status": "active"},
            {"id": 52, "title": "Enhance Knowledge Management", "dept_name": "ICT & Research", "composite_weight": 67, "target": 67, "objective": 9, "status": "active"},
            {"id": 53, "title": "Improve Operational efficiency", "dept_name": "ICT & Research", "composite_weight": 60, "target": 60, "objective": 6, "status": "active"},
            {"id": 54, "title": "Improve Tools and Technology", "dept_name": "ICT & Research", "composite_weight": 80, "target": 80, "objective": 7, "status": "active"},
            {"id": 55, "title": "Enhance Staff Performance", "dept_name": "ICT & Research", "composite_weight": 70, "target": 70, "objective": 9, "status": "active"},
            {"id": 56, "title": "Enhance UCC Business success", "dept_name": "ICT & Research", "composite_weight": 80, "target": 80, "objective": 6, "status": "active"},
            {"id": 57, "title": "Improve stakeholder awareness", "dept_name": "Corporate Affairs", "composite_weight": 70, "target": 70, "objective": 6, "status": "active"},
            {"id": 58, "title": "Enhance visibility and image of UCC Brand", "dept_name": "Corporate Affairs", "composite_weight": 80, "target": 80, "objective": 8, "status": "active"},
            {"id": 59, "title": "Enhance UCC Business Success", "dept_name": "Corporate Affairs", "composite_weight": 80, "target": 80, "objective": 3, "status": "active"},
            {"id": 60, "title": "Minimize Budget Variance", "dept_name": "Corporate Affairs", "composite_weight": 90, "target": 90, "objective": 4, "status": "active"},
            {"id": 61, "title": "Improve Corporate Performance Reporting", "dept_name": "Corporate Affairs", "composite_weight": 80, "target": 80, "objective": 6, "status": "active"},
            {"id": 62, "title": "Enhance coordination of CA Internal stakeholders", "dept_name": "Corporate Affairs", "composite_weight": 75, "target": 75, "objective": 6, "status": "active"},
            {"id": 63, "title": "Increase CA System & Process Efficiency", "dept_name": "Corporate Affairs", "composite_weight": 70, "target": 70, "objective": 7, "status": "active"},
            {"id": 64, "title": "Improve productivity of Corporate Affairs Staff", "dept_name": "Corporate Affairs", "composite_weight": 80, "target": 80, "objective": "Improve Staff Skills Knowledge and Abilities", "status": "active"},
            {"id": 65, "title": "Improve CA Tools & Technology", "dept_name": "Corporate Affairs", "composite_weight": 50, "target": 50, "objective": 7, "status": "active"},
            {"id": 66, "title": "Improve Skills, Knowledge & Abilities", "dept_name": "Industry Affairs and Content", "composite_weight": 70, "target": 70, "objective": 9, "status": "active"},
        ]

        dept_objectives_created = 0
        dept_objectives_skipped = 0
        # Map old department objective IDs to new DepartmentObjective objects
        # This mapping is based on the order in the SQL and the title

        # Build mapping of old department objective IDs to new DepartmentObjective objects
        old_dept_obj_id_to_dept_obj = {}
        
        for idx, dept_obj_data in enumerate(dept_objectives_data):
            # Get department - handle both numeric ID and name
            department = None
            dept_identifier = dept_obj_data.get("dept_name") or dept_obj_data.get("department")
            if isinstance(dept_identifier, str):
                department = department_map.get(dept_identifier)
            elif isinstance(dept_identifier, int):
                department = next((d for d in department_map.values() if hasattr(d, 'id') and d.id == dept_identifier), None)
            
            if not department:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping department objective '{dept_obj_data['title']}' - department '{dept_identifier}' not found")
                )
                dept_objectives_skipped += 1
                continue

            # Get strategic objective - handle both numeric ID and name
            objective = None
            objective_identifier = dept_obj_data.get("objective")
            if isinstance(objective_identifier, str):
                objective = objective_map.get(objective_identifier)
            elif isinstance(objective_identifier, int):
                objective = Objective.objects.filter(id=objective_identifier).first()
            
            if not objective:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping department objective '{dept_obj_data['title']}' - strategic objective '{objective_identifier}' not found")
                )
                dept_objectives_skipped += 1
                continue

            # Map status: "active" -> "in_progress"
            status = "in_progress" if dept_obj_data["status"] == "active" else "draft"

            # Create department objective
            dept_objective, created = DepartmentObjective.objects.get_or_create(
                department=department,
                department_objective_name=dept_obj_data["title"],
                defaults={
                    "objective": objective,
                    "composite_weight": Decimal(str(dept_obj_data["composite_weight"])),
                    "status": status,
                    "objective_target": Decimal(str(dept_obj_data.get("target", dept_obj_data["composite_weight"]))),
                },
            )
            
            # Store mapping from old ID to new object
            old_dept_obj_id_to_dept_obj[dept_obj_data["id"]] = dept_objective
            
            if created:
                dept_objectives_created += 1
                self.stdout.write(f"  ✓ Created department objective: {dept_obj_data['title']}")

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Created {dept_objectives_created} department objectives"
            )
        )
        if dept_objectives_skipped > 0:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Skipped {dept_objectives_skipped} department objectives")
            )

        # 4. Create Teams
        self.stdout.write("Creating Teams...")
        teams_data = [
            {"id": 1, "name": "PIR", "department": 2, "lead_id": 1},
            {"id": 2, "name": "SBP", "department": 2, "lead_id": 1},
            {"id": 3, "name": "Regional Offices", "department": 2, "lead_id": 1},
            {"id": 4, "name": "Board Affairs", "department": 1, "lead_id": 1},
            {"id": 5, "name": "Litigation Unit", "department": 1, "lead_id": 1},
            {"id": 6, "name": "Legal Affairs", "department": 1, "lead_id": 1},
            {"id": 7, "name": "Compliance and Enforcement", "department": 1, "lead_id": 1},
            {"id": 8, "name": "Procurement", "department": 1, "lead_id": 1},
            {"id": 9, "name": "Human Resources", "department": 5, "lead_id": 1},
            {"id": 10, "name": "Administration", "department": 5, "lead_id": 1},
            {"id": 11, "name": "Expenditure Unit", "department": 9, "lead_id": 1},
            {"id": 12, "name": "Revenue Unit", "department": 9, "lead_id": 1},
            {"id": 13, "name": "Management Accounts", "department": 9, "lead_id": 1},
            {"id": 14, "name": "Risk and Compliance", "department": 8, "lead_id": 1},
            {"id": 15, "name": "Assurance", "department": 8, "lead_id": 1},
            {"id": 16, "name": "Communications Infrastructure Services", "department": 4, "lead_id": 1},
            {"id": 17, "name": "Spectrum Management Division", "department": 4, "lead_id": 1},
            {"id": 18, "name": "UCUSAF", "department": 6, "lead_id": 1},
            {"id": 19, "name": "IT&S", "department": 7, "lead_id": 1},
            {"id": 20, "name": "ISU", "department": 7, "lead_id": 1},
            {"id": 21, "name": "CERT", "department": 7, "lead_id": 1},
            {"id": 22, "name": "R&SD", "department": 7, "lead_id": 1},
            {"id": 23, "name": "Multimedia and Content", "department": 3, "lead_id": 1},
            {"id": 24, "name": "Economic Regulation and Competition", "department": 3, "lead_id": 1},
            {"id": 25, "name": "Consumer Affairs", "department": 3, "lead_id": 1},
            {"id": 26, "name": "Human Resource", "department": 5, "lead_id": 1},
        ]

        teams_created = 0
        teams_skipped = 0

        for team_data in teams_data:
            department = Department.objects.get(id=team_data["department"])
            team, created = Team.objects.get_or_create(
                department=department,
                name=team_data["name"],
                defaults={
                    "lead_id": team_data["lead_id"],
                },
            )
            if created:
                teams_created += 1
                self.stdout.write(f"  ✓ Created team: {team_data['name']} ({department.name})")

        self.stdout.write(
            self.style.SUCCESS(f"✓ Created {teams_created} teams")
        )
        if teams_skipped > 0:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Skipped {teams_skipped} teams")
            )


        # 5. Create Department KPIs
        self.stdout.write("Creating Department KPIs...")
        # Map old department objective IDs to KPI data
        # Only including active KPIs (status=1) from the SQL
        dept_kpis_data = [
            {"id":1, "name": "Percentage of received stakeholder requests resolved", "department_objective": 1, "target": 85, "formula": "(Number of of received stakeholder requests resolved/Total Number of stakeholder requests received)*100", "current_value": 14},
            {"id":2, "name": "Percentage of planned engagements undertaken (DPP, UPF, industry bodies, Solicitor General, MoJCA, Judiciary, ULS)", "department_objective": 1, "target": 85, "formula": "(Number of engagements undertaken (DPP, UPF, industry bodies, Solicitor General, MoJCA, Judiciary, ULS)/Total Number of planned engagements)*100", "current_value": 0},
            {"id":3, "name": "Percentage of regulatory gaps identified with proposals", "department_objective": 2, "target": 80, "formula": "(Number of regulatory gaps with proposals/total number of regulatory gaps identified) *100", "current_value": 0},
            {"id":4, "name": "Percentage of procurements within budget", "department_objective": 3, "target": 80, "formula": "(Number of procurements within budget/Total Number of procurements made)*100", "current_value": 0},
            {"id":5, "name": "Percentage of procurements executed in time", "department_objective": 3, "target": 80, "formula": "(Number of procurements executed in time/planned procurements)*100", "current_value": 0},
            {"id":6, "name": "Percentage of operators notified on compliance and reporting processes within the month of May", "department_objective": 4, "target": 80, "formula": "(Number of operators notified on compliance and reporting processes within the month of May /Total Number of operators)*100", "current_value": 0},
            {"id":7, "name": "Percentage of departments engaged on compliance issues per quarter", "department_objective": 4, "target": 80, "formula": "(Number of departments engaged on compliance issues per quarter/Total Number of Departments planned)*100", "current_value": 0},
            {"id":8, "name": "Percentage of departments-initiated operator compliance issues addressed", "department_objective": 4, "target": 80, "formula": "(Number of departments-initiated operator compliance issues addressed /Total Number of compliance issues initiated)*100", "current_value": 0},
            {"id":9, "name": "Percentage of PPDA Audit issues addressed", "department_objective": 4, "target": 80, "formula": "(Number of PPDA Audit issues addressed/Total Number of PPDA Audit Issues raised)*100", "current_value": 0},
            {"id":10, "name": "Stakeholder satisfaction score", "department_objective": 22, "target": 80, "formula": "Survey score", "current_value": 0},
            {"id":11, "name": "Percentage of technical audit completed within three weeks", "department_objective": 5, "target": 70, "formula": "Number of technical audits completed/Total number of technical audits*100", "current_value": 0},
            {"id":12, "name": "Percentage of project monitoring activities completed as per schedule", "department_objective": 6, "target": 80, "formula": "Number of project monitoring activities done/Total number of projects*100", "current_value": 0},
            {"id":13, "name": "Percentage of projects initiated as per schedule/workplan", "department_objective": 6, "target": 90, "formula": "Number of projects initiated/Total number of projects in the workplan *100", "current_value": 0},
            {"id":14, "name": "Percentage of projects executed as per schedule", "department_objective": 7, "target": 90, "formula": "Number of projects executed/Total number of projects in the schedule*100", "current_value": 0},
            {"id":15, "name": "Budget Absorption Rate", "department_objective": 8, "target": 100, "formula": "(Actual Expenditure/Budgeted Amount)*100", "current_value": 0},
            {"id":16, "name": "Percentage of creditors below 30 days", "department_objective": 9, "target": 80, "formula": "(Number of creditors below 30 days/Total Number of creditors)*100", "current_value": 0},
            {"id":17, "name": "Percentage Expenditure aligned to Strategy", "department_objective": 8, "target": 100, "formula": "Percentage of analysis of actual vs strategy", "current_value": 0},
            {"id":18, "name": "Percentage Increase in Revenue", "department_objective": 10, "target": 5, "formula": "Revenue Growth = 100*(Current FY Revenue - Previous FY Revenue)/Previous FY Revenue", "current_value": 0},
            {"id":19, "name": "Percentage of projects rolled over to the next year", "department_objective": 11, "target": 25, "formula": "Number of projects rolled over/Total number of projects implemented*100", "current_value": 0},
            {"id":20, "name": "Percentage of identified audit recommendations implemented", "department_objective": 12, "target": 80, "formula": "(Number of audit recommendations implemented/ Total number of audit recommendations identified.)*100", "current_value": 0},
            {"id":21, "name": "Percentage of identified Board/TMT recommendations implemented", "department_objective": 13, "target": 80, "formula": "(Number of Board and TMT recommendations implemented/Total number of audit recommendations identified)*100", "current_value": 0},
            {"id":22, "name": "Percentage of correspondences completed as per the charter", "department_objective": 34, "target": 80, "formula": "Number of correspondences answered/Total number of correspondences received*100", "current_value": 0},
            {"id":23, "name": "Percentage of Revenues Billed", "department_objective": 15, "target": 100, "formula": "(Amount of Revenues Billed/Amount of Revenue Budgeted)*100", "current_value": 0},
            {"id":24, "name": "Percentage of Revenues Collected", "department_objective": 15, "target": 80, "formula": "(Amount of Revenues collected/Amount of Revenue Budgeted)*100", "current_value": 0},
            {"id":25, "name": "Percentage of Debtors below 90 days", "department_objective": 15, "target": 85, "formula": "(Number of Debtors below 90 days/Total Number of Debtors)*100", "current_value": 0},
            {"id":26, "name": "Employee satisfaction score", "department_objective": 16, "target": 80, "formula": "Staff satisfaction score| Benefits satisfaction| Services satisfaction survey score", "current_value": 0},
            {"id":27, "name": "Percentage of Creditors below 90 Days", "department_objective": 17, "target": 90, "formula": "(Number of Creditors below 60 days/Total Number of Creditors)*100", "current_value": 0},
            {"id":28, "name": "Percentage of staff outstanding accountable advances below 60 days", "department_objective": 17, "target": 80, "formula": "(Number of staff with outstanding accountable advances below 60 days/Total Number of staff with accountable advances)*100", "current_value": 0},
            {"id":29, "name": "Percentage of service requests successfully handled within 7 days", "department_objective": 16, "target": 70, "formula": "(Number of service requests successfully handled within 7 days/Total number of service requests received)*100", "current_value": 0},
            {"id":30, "name": "Percentage of finance reports developed in line with the QA framework and submitted on agreed timelines", "department_objective": 18, "target": 90, "formula": "(Number of finance reports developed in line with the QA framework and submitted on agreed timelines/ Total Number of Financial Reports produced)*100", "current_value": 0},
            {"id":31, "name": "Percentage of staff who met performance targets", "department_objective": 19, "target": 80, "formula": "(Number of staff scoring above 65%/Total number of eligible staff)*100", "current_value": 0},
            {"id":32, "name": "Budget absorption rate", "department_objective": 20, "target": 100, "formula": "(Actual expenditure/Amount in the HRA budget)*100", "current_value": 0},
            {"id":33, "name": "Timeliness of budget preparation", "department_objective": 21, "target": 100, "formula": "In accordance to PFMA", "current_value": 0},
            {"id":34, "name": "Annual budget Report Quality Score", "department_objective": 21, "target": 100, "formula": "In accordance to PFMA", "current_value": 0},
            {"id":35, "name": "Skills gap", "department_objective": 22, "target": 100, "formula": " Finance skills gap = (Number of Finance staff trained/Total number of HRA staff scheduled for training)*100", "current_value": 0},
            {"id":36, "name": "Percentage of work plan activities implemented in time", "department_objective": 23, "target": 80, "formula": "(Number of activities implemented in time/Total workplan activities)*100", "current_value": 0},
            {"id":37, "name": "Percentage of Finance staff meeting intended performance goals", "department_objective": 22, "target": 70, "formula": "Staff Productivity Score = (Number of Staff scoring above 70%/Total number of staff appraised)*100", "current_value": 0},
            {"id":38, "name": "Percentage of Departmental targets achieved", "department_objective": 24, "target": 80, "formula": "Number of Targets achieved/Total Number of Departmental Targets", "current_value": 0},
            {"id":39, "name": "Percentage of legal staff achieving 65% and above", "department_objective": 24, "target": 80, "formula": "(Number of staff achieving 65% and above /Total Number of staff in the department)*100", "current_value": 0},
            {"id":40, "name": "Talent retention rate (High performing staff)", "department_objective": 25, "target": 95, "formula": "(Number of staff retained with appraisal score above 70%/Total number of eligible staff in specified period)*100", "current_value": 0},
            {"id":41,"name": "Post training evaluation score", "department_objective": 25, "target": 80, "formula": "Percentage of training programs scores above 80%", "current_value": 0},
            {"id":42, "name": "Percentage of quarterly reports submitted to the audit Committee within the schedule to the Committee meeting", "department_objective": 26, "target": 75, "formula": "(Number of quarterly reports submitted as per schedule in the FY 2022-23/Total Number of Reports Planned)*100", "current_value": 0},
            {"id":43, "name": "Percentage of reports on Board actions presented as per schedule", "department_objective": 26, "target": 75, "formula": "(Number of reports on Board actions presented as per schedule in the FY 2022-23/Number of reports scheduled for presentation to TMT in the FY 2022-23)*100", "current_value": 0},
            {"id":44, "name": "Percentage of HRA services conducted online", "department_objective": 27, "target": 100, "formula": "Number of HRA services conducted online (Performance appraisal & leave)/Total number of HRA services*100", "current_value": 0},
            {"id":45, "name": "Percentage of consumer related complaints concluded within the set timelines (2 weeks)", "department_objective": 28, "target": 95, "formula": "Number of complaints for which the UCC decision has been communicated to the consumer in the set time/total number of consumer complaints received (call Centre, letters, email and social media)", "current_value": 0},
            {"id":46, "name": "Percentage of content related complaints concluded within 20 working days", "department_objective": 28, "target": 80, "formula": "Number of complaints for which a UCC ruling is communicated to the complainant in the set time/total number of content related complaints received", "current_value": 0},
            {"id":47, "name": "Percentage of competition related complaints concluded within 45 working days", "department_objective": 28, "target": 85, "formula": "Number of complaints for which a UCC ruling is issued to the complainant in the set time/total number of competition related complaints received", "current_value": 0},
            {"id":48, "name": "Percentage of market reports ready for publication in the month following the respective quarter", "department_objective": 29, "target": 75, "formula": "Number of quarterly reports approved for publication by ED the month following the respective quarter/4 (number of quarters in the year)", "current_value": 0},
            {"id":49, "name": "Percentage of consumer advisories issued", "department_objective": 29, "target": 62, "formula": "Number of weekly consumer notices put out/52 (number of weeks)", "current_value": 0},
            {"id":50, "name": "Percentage of quarterly local quota assessment reports ready for publication in the month following the respective quarter", "department_objective": 29, "target": 75, "formula": "Number of quarterly reports approved for publication by ED the month following the respective quarter/4 (number of quarters in the year)", "current_value": 0},
        ]

        kpis_created = 0
        kpis_skipped = 0
        # Map old department_measures.id to KPI objects for team objectives
        # This mapping is based on the order and names from the SQL
        old_measure_id_to_kpi = {}
        # Mapping old measure_id to KPI name (from department_measures SQL)
        # Used to map old measure_ids to KPIs for team objectives

        for kpi_data in dept_kpis_data:
            # Get department objective using the ID from kpi_data
            dept_obj_id = kpi_data.get("department_objective")
            dept_objective = old_dept_obj_id_to_dept_obj.get(dept_obj_id)
            if not dept_objective:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping department KPI '{kpi_data['name']}' - department objective ID {dept_obj_id} not found")
                )
                kpis_skipped += 1
                continue
            
            # Infer KPI properties
            code = self.generate_kpi_code(kpi_data["name"], dept_obj_id=dept_objective.id)
            direction = self.infer_direction(kpi_data["name"], kpi_data.get("formula", ""))
            indicator_type = self.infer_indicator_type(kpi_data["name"], kpi_data.get("formula", ""))
            reporting_period = self.infer_reporting_period(kpi_data["name"], kpi_data.get("formula", ""))
            scoring_config = self.infer_scoring_config(kpi_data["name"], Decimal(str(kpi_data["target"])) if kpi_data.get("target") else None)
            
            # Determine unit
            unit = "%"
            if "score" in kpi_data["name"].lower() and "%" not in kpi_data["name"]:
                unit = "score"
            elif "days" in kpi_data["name"].lower() or "time" in kpi_data["name"].lower():
                unit = "days"
            elif "ugx" in kpi_data["name"].lower() or "revenue" in kpi_data["name"].lower() or "budget" in kpi_data["name"].lower():
                unit = "UGX"

            # Create KPI linked to department_objective
            kpi, created = KPI.objects.get_or_create(
                code=code,
                defaults={
                    "name": kpi_data["name"],
                    "description": f"KPI for {dept_objective.department_objective_name}",
                    "department_objective": dept_objective,
                    "formula": kpi_data.get("formula", ""),
                    "unit": unit,
                    "direction": direction,
                    "indicator_type": indicator_type,
                    "reporting_period": reporting_period,
                    "weight": Decimal("100.0"),
                    "scoring_config": scoring_config,
                    "is_composite": False,
                    "metadata": {},
                    "owner_id": dept_objective.department.head_id if dept_objective.department.head_id else None,
                },
            )
            if created:
                kpis_created += 1
                self.stdout.write(f"  ✓ Created KPI: {kpi.code} - {kpi.name}")
                
                # Create KPIValue for initial target/actual if provided
                if kpi_data.get("target") or kpi_data.get("current_value"):
                    # Use current date for period (will be updated when actual data is loaded)
                    today = date.today()
                    period_start = date(today.year, today.month, 1)
                    # Get last day of month
                    last_day = monthrange(today.year, today.month)[1]
                    period_end = date(today.year, today.month, last_day)
                    
                    KPIValue.objects.create(
                        kpi=kpi,
                        period_start=period_start,
                        period_end=period_end,
                        target=Decimal(str(kpi_data["target"])) if kpi_data.get("target") else None,
                        actual=Decimal(str(kpi_data["current_value"])) if kpi_data.get("current_value") else None,
                        notes="Initial value from legacy data migration"
                    )
            else:
                # Update existing KPI if needed
                updated = False
                if kpi.department_objective != dept_objective:
                    kpi.department_objective = dept_objective
                    updated = True
                if updated:
                    kpi.save()

        self.stdout.write(
            self.style.SUCCESS(f"✓ Created {kpis_created} department KPIs")
        )
        if kpis_skipped > 0:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Skipped {kpis_skipped} department KPIs")
            )

        # 6. Create Team Objectives
        self.stdout.write("Creating Team Objectives...")


        team_objectives_data = [
            {"id": 1, "title": "Improve the completeness and timeliness of litigation and prosecution process flows and Legal Advisory services", "team": 6, "department_objective": 1, "status": 1},
            {"id": 2, "title": "Improve on the response time towards stakeholder requests", "team": 7, "department_objective": 1, "status": 1},
            {"id": 3, "title": "Increase engagements with Internal and External Stakeholders", "team": 7, "department_objective": 1, "status": 1},
            {"id": 4, "title": "Improve on management and disbursement of legal documents", "team": 5, "department_objective": 1, "status": 1},
            {"id": 5, "title": "Improve Timeliness and quality of information submitted to the Ministry", "team": 5, "department_objective": 1, "status": 1},
            {"id": 6, "title": "Improve the collaboration with the Directorate of Public Prosecution, Courts of Law and other communications sector stakeholders", "team": 6, "department_objective": 2, "status": 1},
            {"id": 7, "title": "Enhance compliance of UCC with provisions of signed international agreements, treaties and conventions", "team": 8, "department_objective": 2, "status": 1},
            {"id": 8, "title": "Reduce identified regulatory gaps by 80%", "team": 7, "department_objective": 2, "status": 1},
            {"id": 9, "title": "Ensure value for money is obtained in the execution of the procurement process", "team": 8, "department_objective": 3, "status": 1},
            {"id": 10, "title": "Improve compliance of internal and external stakeholder", "team": 8, "department_objective": 4, "status": 1},
            {"id": 11, "title": "Improve compliance of internal and external stakeholder", "team": 8, "department_objective": 4, "status": 1},
            {"id": 12, "title": "Improve enforcement management process", "team": 8, "department_objective": 4, "status": 1},
            {"id": 13, "title": "Ensure compliance to established rules and procedures for procurement", "team": 8, "department_objective": 3, "status": 1},
            {"id": 14, "title": "Ensure compliance to established rules and procedures for procurement", "team": 8, "department_objective": 3, "status": 1},
            {"id": 15, "title": "Improve the completeness and timeliness of litigation and prosecution process flows and Legal Advisory services", "team": 6, "department_objective": 5, "status": 1},
            {"id": 16, "title": "Reduce turn-around times for processing of license applications", "team": 7, "department_objective": 5, "status": 1},
            {"id": 17, "title": "Improve legal compliance risk management", "team": 8, "department_objective": 6, "status": 1},
            {"id": 18, "title": "Strengthen Financial Reporting", "team": 13, "department_objective": 19, "status": 1},
            {"id": 19, "title": "Improve timelines of budget preparation and reporting to PFMA", "team": 13, "department_objective": 20, "status": 1},
            {"id": 20, "title": "Improve service management", "team": 11, "department_objective": 18, "status": 1},
            {"id": 21, "title": "Improve the number of activities in the administration work plan that are implemented on time", "team": 11, "department_objective": 18, "status": 1},
            {"id": 22, "title": "Improve creditors pay out time", "team": 12, "department_objective": 17, "status": 1},
            {"id": 23, "title": "Reduce staff debtors", "team": 12, "department_objective": 15, "status": 1},
            {"id": 24, "title": "Percentage of identified HRA audit recommendations implemented", "team": 10, "department_objective": 22, "status": 1},
            {"id": 25, "title": "Enhance Business Success of Litigation and Prosecution Unit", "team": 6, "department_objective": 26, "status": 1},
            {"id": 26, "title": "Enhance Business Success of Legal Affairs Unit", "team": 7, "department_objective": 26, "status": 1},
            {"id": 27, "title": "Enhance Business Success of Compliance and Enforcement Unit", "team": 8, "department_objective": 26, "status": 1},
            {"id": 28, "title": "Enhance Business Success of Procurement Unit", "team": 8, "department_objective": 26, "status": 1},
            {"id": 29, "title": "Increase talent retention", "team": 10, "department_objective": 27, "status": 1},
            {"id": 30, "title": "Increase talent retention", "team": 9, "department_objective": 23, "status": 1},
            {"id": 31, "title": "Increase talent retention", "team": 26, "department_objective": 27, "status": 1},
            {"id": 32, "title": "Improve timely review of governance systems", "team": 15, "department_objective": 28, "status": 1},
            {"id": 33, "title": "Promote usage of HRA online services", "team": 10, "department_objective": 29, "status": 1},
            {"id": 34, "title": "Reduce time taken to communicate risk updates/risk assessments", "team": 14, "department_objective": 37, "status": 1},
            {"id": 35, "title": "Improve timely coverage of Board and Management decisions followed up", "team": 14, "department_objective": 28, "status": 1},
            {"id": 36, "title": "Increase coverage of audit client sensitization activities", "team": 15, "department_objective": 33, "status": 1},
            {"id": 37, "title": "Increase utilization of allocated financial resources within market assessed values", "team": 15, "department_objective": 34, "status": 1},
            {"title": "Increase utilization of allocated financial resources within market assessed values", "team": 14, "department_objective": 34, "status": 1},
            {"id": 39, "title": "Increase utilization of allocated financial resources within market assessed values", "team": 15, "department_objective": 34, "status": 1},
            {"id": 40, "title": "Reduce time taken to complete audit assignments", "team": 15, "department_objective": 35, "status": 1},
            {"id": 41, "title": "Improve quality of audit reports to Management and the Audit Committee", "team": 15, "department_objective": 35, "status": 1},
            {"id": 42, "title": "Increase coverage of investigation requests", "team": 15, "department_objective": 35, "status": 1},
            {"id": 43, "title": "Increase coverage of audit follow up reports", "team": 15, "department_objective": 41, "status": 1},
            {"id": 44, "title": "Enhance team business process", "team": 15, "department_objective": 36, "status": 1},
            {"id": 45, "title": "Enhance team business process", "team": 14, "department_objective": 36, "status": 1},
            {"id": 46, "title": "Increase coverage of sensitization on risk management", "team": 14, "department_objective": 37, "status": 1},
            {"id": 47, "title": "Increase coverage of sensitization on risk management", "team": 14, "department_objective": 37, "status": 1},
            {"id": 48, "title": "Improve quality of risk coordination reports to Management and the Audit Committee", "team": 14, "department_objective": 37, "status": 1},
            {"id": 49, "title": "Increase coverage of business units with updated risk information", "team": 15, "department_objective": 41, "status": 1},
            {"id": 50, "title": "Increase coverage of business units with updated risk information", "team": 14, "department_objective": 41, "status": 1},
            {"id": 51, "title": "Improve quality of compliance audit reports to Management and the Audit Committee", "team": 14, "department_objective": 41, "status": 1},
            {"id": 52, "title": "Improve timeliness in conducting the QoS assessment exercises", "team": 16, "department_objective": 42, "status": 1},
            {"id": 53, "title": "Increase the audit tasks completed using the audit tools & technology", "team": 14, "department_objective": 43, "status": 1},
            {"id": 54, "title": "Increase the audit tasks completed using the audit tools & technology", "team": 15, "department_objective": 43, "status": 1},
            {"id": 55, "title": "Improve skills, knowledge and abilities of Assurance team", "team": 15, "department_objective": 44, "status": 1},
            {"id": 56, "title": "Improve skills, knowledge and abilities of Risk and compliance team", "team": 14, "department_objective": 44, "status": 1},
            {"id": 57, "title": "Improve skills, knowledge and abilities of Assurance team", "team": 15, "department_objective": 44, "status": 1},
            {"id": 58, "title": "Improve skills, knowledge and abilities of Assurance team", "team": 15, "department_objective": 44, "status": 1},
            {"id": 59, "title": "Improve skills, knowledge and abilities of Risk and compliance team", "team": 14, "department_objective": 44, "status": 1},
            {"id": 60, "title": "Improve timeliness of investigating interference (Access, Broadcasting, and Land Mobile)", "team": 17, "department_objective": 42, "status": 1},
            {"id": 61, "title": "Improve the frequency/regularity of reporting on radio frequency resource utilization from annual to quarterly with the view to timely identify and report on unauthorized operations", "team": 17, "department_objective": 45, "status": 1},
            {"id": 62, "title": "Improve utilization of Communication Resources (Numbering resources)", "team": 16, "department_objective": 45, "status": 1},
            {"id": 63, "title": "Improve the timeliness of SMD Business Processes, activities and assessment decisions", "team": 16, "department_objective": 46, "status": 1},
            {"id": 64, "title": "Improve the timeliness of SMD BUSINESS processes", "team": 17, "department_objective": 46, "status": 1},
            {"id": 65, "title": "Improve the timeliness of SMD BUSINESS processes", "team": 17, "department_objective": 46, "status": 1},
            {"id": 66, "title": "Improve the timeliness of SMD BUSINESS processes", "team": 17, "department_objective": 46, "status": 1},
            {"id": 67, "title": "Improve utilization of smd technical tools", "team": 16, "department_objective": 47, "status": 1},
            {"id": 68, "title": "Promote use of communication services", "team": 18, "department_objective": 7, "status": 1},
            {"id": 69, "title": "Improve UCUSAF operational efficiency", "team": 18, "department_objective": 8, "status": 1},
            {"id": 70, "title": "Increase project monitoring turnaround", "team": 18, "department_objective": 9, "status": 1},
            {"id": 71, "title": "Improve project conceptualization", "team": 18, "department_objective": 10, "status": 1},
            {"id": 72, "title": "Improve contract management", "team": 18, "department_objective": 11, "status": 1},
            {"id": 73, "title": "Decrease Number of Rolled Over Projects", "team": 18, "department_objective": 12, "status": 1},
            {"id": 74, "title": "Strengthen stakeholder relationships", "team": 18, "department_objective": 13, "status": 1},
            {"id": 75, "title": "Improve IT&S Customer Satisfaction", "team": 19, "department_objective": 48, "status": 1},
            {"id": 76, "title": "Improve IT&S Customer Satisfaction", "team": 20, "department_objective": 48, "status": 1},
            {"id": 77, "title": "Improve IT&S Customer Satisfaction", "team": 21, "department_objective": 48, "status": 1},
            {"id": 78, "title": "Improve quality of Information systems services", "team": 19, "department_objective": 48, "status": 1},
            {"id": 79, "title": "Improve quality of Information systems services", "team": 19, "department_objective": 48, "status": 1},
            {"id": 80, "title": "Automate Business Processes", "team": 19, "department_objective": 53, "status": 1},
            {"id": 81, "title": "Build cyber security capacity and capabilities in the sector and the Commission", "team": 21, "department_objective": 49, "status": 1},
            {"id": 82, "title": "Build cyber security capacity and capabilities in the sector and the Commission", "team": 21, "department_objective": 49, "status": 1},
            {"id": 83, "title": "Optimize Resources", "team": 19, "department_objective": 50, "status": 1},
            {"id": 84, "title": "Optimize Resources", "team": 20, "department_objective": 50, "status": 1},
            {"id": 85, "title": "Optimize Resources", "team": 21, "department_objective": 50, "status": 1},
            {"id": 86, "title": "Optimize Resources", "team": 22, "department_objective": 50, "status": 1},
            {"id": 87, "title": "Improve budget cost savings", "team": 19, "department_objective": 50, "status": 1},
            {"id": 88, "title": "Improve budget cost savings", "team": 20, "department_objective": 50, "status": 1},
            {"id": 89, "title": "Improve budget cost savings", "team": 21, "department_objective": 50, "status": 1},
            {"id": 90, "title": "Improve budget cost savings", "team": 22, "department_objective": 50, "status": 1},
            {"id": 91, "title": "Improve Information services risk management", "team": 20, "department_objective": 51, "status": 1},
            {"id": 92, "title": "Improve project planning and contract management", "team": 22, "department_objective": 51, "status": 1},
            {"id": 93, "title": "Improve R&SD risk management", "team": 22, "department_objective": 51, "status": 1},
            {"id": 94, "title": "Improve IT risk management", "team": 19, "department_objective": 51, "status": 1},
            {"id": 95, "title": "Improve CERT risk management", "team": 21, "department_objective": 51, "status": 1},
            {"id": 96, "title": "Enhance the utilization of research information", "team": 22, "department_objective": 52, "status": 1},
            {"id": 97, "title": "Enhance the utilization of research information", "team": 22, "department_objective": 52, "status": 1},
            {"id": 98, "title": "Improve access to knowledge", "team": 20, "department_objective": 52, "status": 1},
            {"id": 99, "title": "Improve performance on Team Service Charter KPIs", "team": 19, "department_objective": 53, "status": 1},
            {"id": 100, "title": "Improve performance on Team Service Charter KPIs", "team": 20, "department_objective": 53, "status": 1},
            {"id": 101, "title": "Improve quality of Information systems services", "team": 21, "department_objective": 53, "status": 1},
            {"id": 102, "title": "Improve performance on Team Service Charter KPIs", "team": 22, "department_objective": 53, "status": 1},
            {"id": 103, "title": "Increase IT systems availability", "team": 19, "department_objective": 54, "status": 1},
            {"id": 104, "title": "Review processes and policies in the Division", "team": 21, "department_objective": 54, "status": 1},
            {"id": 105, "title": "Improve ISU Internal Processes", "team": 20, "department_objective": 54, "status": 1},
            {"id": 106, "title": "Improve turnaround time for approval of R&SD Processes", "team": 22, "department_objective": 54, "status": 1},
            {"id": 107, "title": "Improve Resource utilization", "team": 19, "department_objective": 50, "status": 1},
            {"id": 108, "title": "Increment in Usage of Resource Centre", "team": 20, "department_objective": 50, "status": 1},
            {"id": 109, "title": "Enhance IT Staff Performance", "team": 19, "department_objective": 55, "status": 1},
            {"id": 110, "title": "Enhance ISU Staff Performance", "team": 20, "department_objective": 55, "status": 1},
            {"id": 111, "title": "Enhance CERT Staff Performance", "team": 21, "department_objective": 55, "status": 1},
            {"id": 112, "title": "Enhance Research Staff Performance", "team": 22, "department_objective": 55, "status": 1},
            {"id": 113, "title": "Enhance Business Success of IT Unit", "team": 19, "department_objective": 56, "status": 1},
            {"id": 114, "title": "Enhance Business Success of ISU Unit", "team": 20, "department_objective": 56, "status": 1},
            {"id": 115, "title": "Enhance Business Success of CERT Unit", "team": 21, "department_objective": 56, "status": 1},
            {"id": 116, "title": "Enhance Business Success of Research Unit", "team": 22, "department_objective": 56, "status": 1},
            {"id": 117, "title": "Improve stakeholder awareness", "team": 1, "department_objective": 57, "status": 1},
            {"id": 118, "title": "Improve timeliness of performance information to support management decision making", "team": 1, "department_objective": 61, "status": 1},
            {"id": 119, "title": "Strengthen the coordination of Regional office stakeholder engagements", "team": 3, "department_objective": 62, "status": 1},
            {"id": 120, "title": "Enhance visibility and image of UCC brand", "team": 1, "department_objective": 58, "status": 1},
            {"id": 121, "title": "Enhance implementation of SBP workplan", "team": 2, "department_objective": 59, "status": 1},
            {"id": 122, "title": "Improve timely conclusion of complaints (Consumer complaints)", "team": 25, "department_objective": 30, "status": 1},
            {"id": 123, "title": "Enhance implementation of PIR workplan", "team": 1, "department_objective": 59, "status": 1},
            {"id": 124, "title": "Improve the turnaround time for review of licensee/industry disputes and investigations within 45 working days", "team": 24, "department_objective": 30, "status": 1},
            {"id": 125, "title": "Improve timely conclusion of Content and licensee complaints", "team": 23, "department_objective": 30, "status": 1},
            {"id": 126, "title": "Improve the timely availability of information to stakeholders", "team": 23, "department_objective": 31, "status": 1},
            {"id": 127, "title": "Improve the timely availability of information to stakeholders.(Report and Consumer advisories)", "team": 25, "department_objective": 31, "status": 1},
            {"id": 128, "title": "Increase Uganda's contribution to the development of international standards", "team": 1, "department_objective": 59, "status": 1},
            {"id": 129, "title": "Strengthen achievement of strategy and Business Planning Targets", "team": 2, "department_objective": 59, "status": 1},
            {"id": 130, "title": "Improve the timeliness of competition and market information", "team": 24, "department_objective": 31, "status": 1},
            {"id": 131, "title": "Enhance RO business success", "team": 3, "department_objective": 59, "status": 1},
            {"id": 132, "title": "Reduce cost of doing business/operation", "team": 23, "department_objective": 32, "status": 1},
            {"id": 133, "title": "Reduce cost of doing business/operation", "team": 25, "department_objective": 32, "status": 1},
            {"id": 134, "title": "Strengthen the relevancy of industry standards ( develop, review, register and apply frameworks, guidelines, standards and rules)", "team": 23, "department_objective": 38, "status": 1},
            {"id": 135, "title": "Strengthen the relevance of industry/tools standards/guidelines and frameworks within the division", "team": 24, "department_objective": 38, "status": 1},
            {"id": 136, "title": "Improve responsiveness of the regulatory frameworks and standards", "team": 25, "department_objective": 38, "status": 1},
            {"id": 137, "title": "Strengthen Compliance monitoring •Improve the quality of compliance information on licensed operators •Increase awareness of compliance standards", "team": 23, "department_objective": 30, "status": 1},
            {"id": 138, "title": "Strengthen Compliance monitoring •Improve the quality of compliance information on licensed operators •Increase awareness of compliance standards", "team": 24, "department_objective": 30, "status": 1},
            {"id": 139, "title": "Strengthen Compliance monitoring", "team": 25, "department_objective": 30, "status": 1},
            {"id": 140, "title": "Strengthen Compliance monitoring", "team": 23, "department_objective": 39, "status": 1},
            {"id": 141, "title": "Strengthen Compliance monitoring", "team": 24, "department_objective": 39, "status": 1},
            {"id": 142, "title": "Strengthen Compliance monitoring", "team": 23, "department_objective": 30, "status": 1},
            {"id": 143, "title": "Strengthen Compliance monitoring", "team": 24, "department_objective": 30, "status": 1},
            {"id": 144, "title": "Strengthen Compliance monitoring", "team": 25, "department_objective": 30, "status": 1},
            {"id": 145, "title": "Improve Tools & Technology capability for better work environment & processes (Digital Logger)", "team": 23, "department_objective": 40, "status": 1},
            {"id": 146, "title": "Enhance online data collection portal to include Telecom, Postal and Multimedia subsector. (Filemaker and Kompare site/ portal)", "team": 24, "department_objective": 40, "status": 1},
            {"id": 147, "title": "Improve Tools & Technology capability for better work environment & processes (Digital Logger)", "team": 25, "department_objective": 40, "status": 1},
            {"id": 148, "title": "Enhance coordination of RO internal stakeholders", "team": 3, "department_objective": 62, "status": 1},
            {"id": 149, "title": "Increase PIR systems and process efficiency", "team": 1, "department_objective": 63, "status": 1},
            {"id": 150, "title": "Improve Skills, Knowledge & Abilities", "team": 23, "department_objective": 66, "status": 1},
            {"id": 151, "title": "Improve Skills, Knowledge & Abilities", "team": 24, "department_objective": 66, "status": 1},
            {"id": 152, "title": "Improve documentation of Strategy and Business planning frameworks", "team": 2, "department_objective": 63, "status": 1},
            {"id": 153, "title": "Improve documentation of PIR frameworks", "team": 1, "department_objective": 63, "status": 1},
            {"id": 154, "title": "Improve productivity of Regional office staff", "team": 3, "department_objective": 59, "status": 1},
            {"id": 155, "title": "Improve Skills, Knowledge & Abilities", "team": 25, "department_objective": 66, "status": 1},
            {"id": 156, "title": "Improve Employee Satisfaction Score", "team": 26, "department_objective": 22, "status": 1},
            {"id": 157, "title": "Increase Employee Productivity", "team": 26, "department_objective": 23, "status": 1},
            {"id": 158, "title": "Improve Department Efficiency", "team": 26, "department_objective": 25, "status": 1},
        ]
        
        team_objectives_created = 0
        team_objectives_skipped = 0
        
        # Build a map of department objectives by ID for matching
        dept_objectives_map = {}
        for dept_obj_data in dept_objectives_data:
            dept_id = dept_obj_data.get("department") or dept_obj_data.get("dept_name")
            # Handle both numeric department IDs and department names
            if isinstance(dept_id, str):
                # Look up department by name
                dept = department_map.get(dept_id)
                dept_id = dept.id if dept else None
            elif isinstance(dept_id, int):
                # Look up department by numeric ID
                dept = next((d for d in department_map.values() if hasattr(d, 'id') and d.id == dept_id), None)
                if dept:
                    dept_id = dept.id
            dept_objectives_map[dept_obj_data["id"]] = {
                "title": dept_obj_data["title"],
                "department": dept_id,
                "department_id": dept_id,
                "dept_name": dept_obj_data.get("dept_name", ""),
            }
        
        # Build team ID to team object mapping
        teams_id_map = {}
        for team_data in teams_data:
            team_obj = Team.objects.filter(
                department_id=team_data["department"],
                name=team_data["name"]
            ).first()
            if team_obj:
                teams_id_map[team_data["id"]] = team_obj
        
        # Update team_objectives_data with inferred department_objective IDs
        for team_obj_data in team_objectives_data:
            inferred_dept_obj_id = self.infer_dept_objective_for_team_obj(
                team_obj_data, dept_objectives_map
            )
            team_obj_data["department_objective"] = inferred_dept_obj_id
        
        # Map old department objective IDs to actual DepartmentObjective objects
        old_dept_obj_id_to_dept_obj = {}
        for dept_obj_data in dept_objectives_data:
            dept = department_map.get(dept_obj_data.get("dept_name"))
            if not dept:
                # Try numeric department ID
                dept_id = dept_obj_data.get("department")
                dept = next((d for d in department_map.values() if hasattr(d, 'id') and d.id == dept_id), None)
            
            if dept:
                dept_obj = DepartmentObjective.objects.filter(
                    department=dept,
                    department_objective_name=dept_obj_data["title"]
                ).first()
                if dept_obj:
                    old_dept_obj_id_to_dept_obj[dept_obj_data["id"]] = dept_obj
        
        # Create team objectives
        for idx, team_obj_data in enumerate(team_objectives_data):
            # Get team object
            team = teams_id_map.get(team_obj_data["team"])
            if not team:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping team objective '{team_obj_data['title']}' - team ID {team_obj_data['team']} not found")
                )
                team_objectives_skipped += 1
                continue
            
            # Get department objective using inferred ID
            dept_obj_id = team_obj_data.get("department_objective")
            dept_objective = old_dept_obj_id_to_dept_obj.get(dept_obj_id)
            if not dept_objective:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping team objective '{team_obj_data['title']}' - department objective ID {dept_obj_id} not found")
                )
                team_objectives_skipped += 1
                continue
            
            # Map status: 1 -> "in_progress"
            status = "in_progress" if team_obj_data["status"] == 1 else "draft"
            
            # Get target value from data, default to empty string if 0 or not provided
            target = team_obj_data.get("target", "")
            if target == 0 or target == "0":
                target = Decimal("70")
            else:
                target = Decimal(str(target)) if target else Decimal("70")
            
            # Create team objective - lookup by team and dept_objective, set name and target in defaults
            team_objective, created = TeamObjective.objects.get_or_create(
                team=team,
                dept_objective=dept_objective,
                defaults={
                    "team_objective_name": team_obj_data["title"],
                    "objective_target": target,
                    "status": status,
                },
            )
            # Update if exists but name/target might have changed
            if not created:
                updated = False
                if team_objective.team_objective_name != team_obj_data["title"]:
                    team_objective.team_objective_name = team_obj_data["title"]
                    updated = True
                if team_objective.objective_target != target:
                    team_objective.objective_target = target
                    updated = True
                if updated:
                    team_objective.save()
                    self.stdout.write(f"  ✓ Updated team objective: {team_obj_data['title']} ({team.name})")
            else:
                team_objectives_created += 1
                self.stdout.write(f"  ✓ Created team objective: {team_obj_data['title']} ({team.name})")
            
        
        self.stdout.write(
            self.style.SUCCESS(f"✓ Created {team_objectives_created} team objectives")
        )
        if team_objectives_skipped > 0:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Skipped {team_objectives_skipped} team objectives")
            )

        # Map team_objective data index to TeamObjective objects
        # Create mapping based on the order in team_objectives_data
        # The "team_objective" key in team_kpis_data refers to the index (1-based) in team_objectives_data
        team_obj_data_idx_to_team_obj = {}
        for idx, team_obj_data in enumerate(team_objectives_data, start=1):
            # Get team object
            team = teams_id_map.get(team_obj_data["team"])
            if not team:
                continue
            
            # Get department objective using inferred ID
            dept_obj_id = team_obj_data.get("department_objective")
            dept_objective = old_dept_obj_id_to_dept_obj.get(dept_obj_id)
            if not dept_objective:
                continue
            
            # Find the TeamObjective object that was created for this data entry
            team_objective = TeamObjective.objects.filter(
                team=team,
                dept_objective=dept_objective,
                team_objective_name=team_obj_data["title"]
            ).first()
            
            if team_objective:
                team_obj_data_idx_to_team_obj[idx] = team_objective
        

        # 7. Create Team KPIs
        self.stdout.write("Creating Team KPIs...")

        # Format: (id, measure, target, formula, score, team_objective_id, reporting_period_id, created_at, updated_at, status)
        # Only including uncommented entries with status=1
        team_kpis_data = [
            {"id": 21, "name": "Percentage of stakeholder querries addressed within 7 working days", "target": 70, "formula": "(Number of stakeholder querries addressed within 7 working days/Total Number of stakeholder querries addressed received)*100", "score": 55, "team_objective": 1, "status": 1},
            {"id": 22, "name": "%ge of received stakeholder requests resolved", "target": 85, "formula": "(Number of stakeholder requests addressed within 7 days/Total Number of External stakeholder requests received)*100", "score": 100, "team_objective": 2, "status": 1},
            {"id": 23, "name": "Percentage of stakeholder engagements undertaken", "target": 100, "formula": "(Number of stakeholder engagements undertaken/Total Number of engagements planned)*100", "score": 100, "team_objective": 3, "status": 1},
            {"id": 26, "name": "Percentage of documents received and dispatched within a day for commissions secretary signature", "target": 85, "formula": "(Number of documents received and dispatched within a day for commissions secretary signature/Total number of documents received)*100", "score": 61, "team_objective": 4, "status": 1},
            {"id": 27, "name": "Percentage of legal documents sealed", "target": 85, "formula": "(Number of legal documents sealed/Total Number of documents received)*100", "score": 20, "team_objective": 5, "status": 1},
            {"id": 28, "name": "Percentage of licensed operators updated in the database", "target": 85, "formula": "(Number of licensed operators updated in the database/Total Number of operators Licensed)*100", "score": 90, "team_objective": 16, "status": 1},
            {"id": 29, "name": "Percentage of minister reports submitted in set timelines", "target": 85, "formula": "(Number of Quarterly reports submitted to the minister by 6th day of the month after the quarter/Total Number of reports)*100", "score": 0, "team_objective": 7, "status": 1},
            {"id": 30, "name": "Percentage of planned meetings and engagement implemented", "target": 80, "formula": "(Number of meeting and engagements held/Total Number of meetings and engagements planned)*100", "score": 100, "team_objective": 8, "status": 1},
            {"id": 32, "name": "Percentage of licensing gaps addressed", "target": 80, "formula": "(Number of licensing gaps addressed/total number of license gaps identified) *100", "score": 75, "team_objective": 10, "status": 1},
            {"id": 33, "name": "Percentage of procurements within budget", "target": 80, "formula": "(Number of procurements within budget/Total Number of procurements made)*100", "score": 100, "team_objective": 11, "status": 1},
            {"id": 34, "name": "Percentage of planned procurements completed", "target": 80, "formula": "(Number of planned procurements completed/Total Number of procurements planned)*100", "score": 70, "team_objective": 11, "status": 1},
            {"id": 63, "name": "Percentage of cases handled within statutory periods", "target": 70, "formula": "(Number of cases handled within statutory timelines/Total Number of cases handled)*100", "score": 0, "team_objective": 11, "status": 1},
            {"id": 38, "name": "Percentage of non-compliant operators handled", "target": 70, "formula": "(Number of non-compliant operators handled within 7 days/Total Number of non-compliant operators forwarded to Legal)*100", "score": 95, "team_objective": 12, "status": 1},
            {"id": 39, "name": "Percentage of checklists issued", "target": 70, "formula": "(Number of checklists issued two months prior to the expiry of the License/Total Number of Licenses due for renewal)*100", "score": 80, "team_objective": 13, "status": 1},
            {"id": 40, "name": "Percentage of requests addressed and responded to", "target": 70, "formula": "(Number of enforcement requests addressed and responded to/Total Number of requests received)*100", "score": 75, "team_objective": 14, "status": 1},
            {"id": 41, "name": "Percentage of PPDA queries addressed", "target": 80, "formula": "(Number of PPDA querries addressed/Total Number of PPDA Querries raised)*100", "score": 100, "team_objective": 15, "status": 1},
            {"id": 42, "name": "Percentage of Internal Audit queries addressed", "target": 80, "formula": "(Number of Internal Audit querries addressed/Total Number of Internal Audit querries raised)*100", "score": 100, "team_objective": 16, "status": 1},
            {"id": 44, "name": "Percentage of cases and legal documents filed in court on time", "target": 70, "formula": "(Number of court matters filed within the statutory period/the total number of court matters requiring filing) *100", "score": 100, "team_objective": 17, "status": 1},
            {"id": 46, "name": "Percentage of complete license applications reviewed within 60 days", "target": 70, "formula": "(Number of complete applications processed within 60 days/ number of complete applications received) *100", "score": 45, "team_objective": 18, "status": 1},
            {"id": 47, "name": "Percentage of approved license applications processed within the stipulated 20 days", "target": 80, "formula": "(Number of approved applications processed within 20 days/ total number of approved applications) *100", "score": 67, "team_objective": 18, "status": 1},
            {"id": 48, "name": "Percentage of License agreements and or license certificates dispatched to operators within 7 days from date of printing or date of signing", "target": 80, "formula": "(Number of signed agreements and certificates issued within 7 days from date of signing/Total Number of licenses issued)*100", "score": 100, "team_objective": 18, "status": 1},
            {"id": 49, "name": "Percentage of notified user gliches cascaded to IT Department for resolution", "target": 70, "formula": "(Number of identified glitches resolved/Total Number of identified glitches)*100", "score": 100, "team_objective": 19, "status": 1},
            {"id": 50, "name": "Percentage of operators submitting applications through the system", "target": 50, "formula": "(Number of applications received and processed through the E-licensing system/Total Number of applications received)*100", "score": 98, "team_objective": 20, "status": 1},
            {"id": 51, "name": "Percentage of procurements done within set/planned timelines", "target": 70, "formula": "(Number of procurements done within set/planned timelines/Total Number of procurements done)*100", "score": 50, "team_objective": 21, "status": 1},
            {"id": 52, "name": "Percentage of board action papers/Resolutions disseminated to Directors for consideration in a timely manner", "target": 70, "formula": "(Number of board action papers/Resolutions submitted to directors 7 days after board meeting/Total Number of board action papers)*100", "score": 0, "team_objective": 22, "status": 1},
            {"id": 53, "name": "Percentage of board action papers with updates submitted to the board in a timely manner", "target": 70, "formula": "(Number of board action papers with updates submitted to the board within 14 days before board meeting/Total Number of board action papers)*100", "score": 0, "team_objective": 22, "status": 1},
            {"id": 54, "name": "Percentage of board minutes submitted to the board in a timely manner", "target": 70, "formula": "(Number of board minutes submitted to the board within 14 days before board meeting/Total Number of board minutes)*100", "score": 0, "team_objective": 22, "status": 1},
            {"id": 55, "name": "Percentage of board papers submitted to the board in a timely manner", "target": 70, "formula": "(Number of board papers submitted to the board within 14 days before board meeting/Total Number of board papers prepared)*100", "score": 0, "team_objective": 22, "status": 1},
            {"id": 56, "name": "Percentage of Board international travels and logistics coordinated within set schedules", "target": 70, "formula": "(Number of board international travels and logistics coordinated within set schedules/ Total number of Board international travels)*100", "score": 0, "team_objective": 22, "status": 1},
            {"id": 57, "name": "Percentage of reminders to board members on report writing on return from international trips", "target": 70, "formula": "(Number of formal Reminders made to board members within 2 weeks on return from a given international travels/Total Number of Board International Travels)*100", "score": 0, "team_objective": 22, "status": 1},
            {"id": 58, "name": "Percentage committee action papers with updates submitted in a timely manner", "target": 70, "formula": "(Number of committee action papers with updates submitted within 14 days before committee meeting/Total Number of committee action papers prepared)*100", "score": 0, "team_objective": 23, "status": 1},
            {"id": 59, "name": "Percentage of committee minutes submitted to the board in a timely manner", "target": 70, "formula": "(Number of committee minutes submitted to the board within 14 days before board meeting/Total Number of committee minutes prepared)*100", "score": 0, "team_objective": 23, "status": 1},
            {"id": 60, "name": "Percentage of committee papers submitted in a timely manner", "target": 70, "formula": "(Number of committee papers submitted within 14 days before committee meeting/Total Number of Committee papers prepared)*100", "score": 0, "team_objective": 23, "status": 1},
            {"id": 61, "name": "Percentage of board sitting allowances prepared on time", "target": 70, "formula": "(Number of board meetings with sitting allowances paid prior to the meeting/Total number of board meetings)*100", "score": 0, "team_objective": 23, "status": 1},
            {"id": 62, "name": "Percentage of committee sitting allowances prepared on time", "target": 70, "formula": "(Number of committee meetings with sitting allowances paid prior to the meeting/Total number of committee meetings held)*100", "score": 0, "team_objective": 23, "status": 1},
            {"id": 64, "name": "Percentage of cases handled within statutory periods", "target": 70, "formula": "(Number of cases handled within statutory timelines/Total Number of cases handled)*100", "score": 0, "team_objective": 24, "status": 1},
            {"id": 65, "name": "Percentage of Legal opinions provided within 7 working days", "target": 70, "formula": "(Number of Legal opinions provided within 7 working days/Total Number of legal issues Received)*100", "score": 89, "team_objective": 25, "status": 1},
            {"id": 66, "name": "Percentage of legal advisory requests responded to within 7 days from date of receipt", "target": 70, "formula": "(Number of request addressed in 7 days/ total number of internal legal requests) *100", "score": 0, "team_objective": 26, "status": 1},
            {"id": 67, "name": "Percentage of investigations concluded within set timelines", "target": 70, "formula": "(Number of investigations concluded within set timelines/Total Number of Investigations Carried out)*100", "score": 0, "team_objective": 27, "status": 1},
            {"id": 68, "name": "Percentage of investigations concluded within set timelines", "target": 70, "formula": "(Number of investigations concluded within set timelines/Total Number of Investigations Carried out)*100", "score": 75, "team_objective": 28, "status": 1},
            {"id": 69, "name": "Percentage of risks with adoptable mitigation measures", "target": 70, "formula": "(Number of risks with workable mitigation measures /Total Number of Risks Identified)*100", "score": 85, "team_objective": 29, "status": 1},
            {"id": 70, "name": "Percentage of identified litigation risks with mitigation measures", "target": 50, "formula": "(Number of risks mitigated/total number of risks identified) *100", "score": 100, "team_objective": 30, "status": 1},
            {"id": 71, "name": "Percentage of identified risks within the licensing process with workable mitigation measures in place", "target": 70, "formula": "(Number of risks in the licensing process with workable mitigants/ Total Number of risks in the licensing process identified) *100", "score": 100, "team_objective": 31, "status": 1},
            {"id": 72, "name": "Percentage of identified risks with mitigation measures", "target": 70, "formula": "(Number of identified risks with mitigation measures/Total Number of identified risks)*100", "score": 100, "team_objective": 32, "status": 1},
            {"id": 73, "name": "Percentage of Mitigation Measures with Updates", "target": 70, "formula": "(Number of mitigants with updates/ Total Number of Mitigants) *100", "score": 100, "team_objective": 33, "status": 1},
            {"id": 74, "name": "Percentage of Commission's Contracts and MOUs reviewed for completeness", "target": 70, "formula": "(Number of Commission's Contracts and MOUs reviewed for completeness/Total Number of agreements and MOUs received by Compliance and Enforcement Unit)*100", "score": 100, "team_objective": 34, "status": 1},
            {"id": 77, "name": "Percentage of service requests handled within 5 days", "target": 70, "formula": "(Number of service requests handled within 5 days/Total number of service requests handled)*100", "score": 0, "team_objective": 33, "status": 1},
            {"id": 80, "name": "Budget absorption rate", "target": 100, "formula": "(Actual Expenditure/Amount in administration Expenditure Budget)*100", "score": 74, "team_objective": 35, "status": 1},
            {"id": 83, "name": "Percentage of creditors below 30 days", "target": 80, "formula": "(Number of creditors below 30 days/Total Number of creditors)*100", "score": 51, "team_objective": 36, "status": 1},
            {"id": 84, "name": "Budget Absorption Rate", "target": 100, "formula": "(Actual Expenditure/Budgeted Amount)*100", "score": 106, "team_objective": 37, "status": 1},
            {"id": 85, "name": "Percentage Expenditure aligned to Strategy", "target": 100, "formula": "Percentage of analysis of actual vs strategy", "score": 100, "team_objective": 38, "status": 1},
            {"id": 87, "name": "Percentage Increase in Revenue", "target": 5, "formula": "Revenue Growth = 100*(Current FY Revenue - Previous FY Revenue)/Previous FY Revenue", "score": 0, "team_objective": 39, "status": 1},
            {"id": 88, "name": "Percentage of the amount spent within the budget", "target": 90, "formula": "(Amount spent/Amount budgeted)*100", "score": 75, "team_objective": 40, "status": 1},
            {"id": 89, "name": "Percentage of identified audit recommendations implemented", "target": 80, "formula": "(Number of audit recommendations implemented/ Total number of audit recommendations identified.)*100", "score": 93, "team_objective": 41, "status": 1},
            {"id": 91, "name": "Percentage of workforce that meet performance standards", "target": 88, "formula": "(Number of staff who scored above set standards 65/Total number of staff)*100", "score": 0, "team_objective": 42, "status": 1},
            {"id": 92, "name": "Percentage of Revenues Billed", "target": 100, "formula": "(Amount of Revenues Billed/Amount of Revenue Budgeted)*100", "score": 99, "team_objective": 43, "status": 1},
            {"id": 93, "name": "Staff Satisfaction Survey", "target": 80, "formula": "Satisfaction Survey score", "score": 0, "team_objective": 60, "status": 1},
            {"id": 95, "name": "Percentage of Revenues Collected", "target": 80, "formula": "(Amount of Revenues collected/Amount of Revenue Budgeted)*100", "score": 83, "team_objective": 44, "status": 1},
            {"id": 96, "name": "Percentage of Debtors below 90 days", "target": 85, "formula": "(Number of Debtors below 90 days/Total Number of Debtors)*100", "score": 89, "team_objective": 45, "status": 1},
            {"id": 98, "name": "Percentage of service requests handled within 5 days", "target": 70, "formula": "(Number of service requests handled within 5 days/Total number of service requests handled)*100", "score": 80, "team_objective": 46, "status": 1},
            {"id": 99, "name": "Percentage of Manpower plan implemented", "target": 100, "formula": "(Number of cavant positions filled within set timelines/Total number of vacant positions approved for recruitment in a year)*100", "score": 0, "team_objective": 65, "status": 1},
            {"id": 101, "name": "Percentage of status reports that have been prepared", "target": 80, "formula": "(Number of status reports prepared in a timely manner/Total number of status reports expected to be prepared)*100", "score": 47, "team_objective": 67, "status": 1},
            {"id": 103, "name": "Percentage of service reports that have been prepared on time", "target": 90, "formula": "(Number of service reports prepared in a timely manner/Total number status reports expected to be prepared)*100", "score": 67, "team_objective": 48, "status": 1},
            {"id": 104, "name": "Percentage of finance reports developed in line with the QA framework and submitted on agreed timelines", "target": 90, "formula": "(Number of finance reports developed in line with the QA framework and submitted on agreed timelines/ Total Number of Financial Reports produced)*100", "score": 93, "team_objective": 49, "status": 1},
            {"id": 105, "name": "Timeliness of budget preparation", "target": 100, "formula": "In accordance to PFMA", "score": 100, "team_objective": 50, "status": 1},
            {"id": 106, "name": "Percentage of operational documents that have been prepared", "target": 100, "formula": "(Number of operational documents prepared in a timely manner/Total number of operational documents expected to be prepared)*100", "score": 75, "team_objective": 51, "status": 1},
            {"id": 107, "name": "Annual budget Report Quality Score", "target": 100, "formula": "In accordance to PFMA", "score": 0, "team_objective": 52, "status": 1},
            {"id": 109, "name": "Percentage of timely implemented activities in the administration work plan", "target": 85, "formula": "(Number of activities executed on time/Total workplan activities)*100", "score": 64, "team_objective": 53, "status": 1},
            {"id": 112, "name": "Percentage of Creditors below 90 Days", "target": 90, "formula": "(Number of Creditors below 60 days/Total Number of Creditors)*100", "score": 82, "team_objective": 54, "status": 1},
            {"id": 114, "name": "Percentage of staff outstanding accountable advances below 60 days", "target": 80, "formula": "(Number of staff with outstanding accountable advances below 60 days/Total Number of staff with accountable advances)*100", "score": 75, "team_objective": 55, "status": 1},
            {"id": 115, "name": "Percentage of audit issues addressed", "target": 80, "formula": "(Number of audit issues resolved/Total number of audit reported) *100", "score": 0, "team_objective": 56, "status": 1},
            {"id": 116, "name": "Percentage of Litigation and Prosecution team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of litigation and prosecution team targets)*100", "score": 100, "team_objective": 57, "status": 1},
            {"id": 117, "name": "Percentage of Legal Affair team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of legal affairs team targets)*100", "score": 73, "team_objective": 58, "status": 1},
            {"id": 118, "name": "Percentage of Compliance and Enforcement team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of compliance and enforcement team targets)*100", "score": 64, "team_objective": 59, "status": 1},
            {"id": 119, "name": "Percentage of procurement team targets achieved", "target": 60, "formula": "(Number of Targets Achieved/Total Number of procurement team targets)*100", "score": 0, "team_objective": 84, "status": 1},
            {"id": 122, "name": "Number of critical positions identified for succession planning", "target": 100, "formula": "(Number of critical positions classified/Total number of positions identified)*100", "score": 0, "team_objective": 61, "status": 1},
            {"id": 123, "name": "Job description manual/Planned frameworks", "target": 100, "formula": "(Number of job description framework drafted/Total number of frameworks)*100", "score": 0, "team_objective": 62, "status": 1},
            {"id": 125, "name": "Proportion of planned governance systems reviewed as per schedule", "target": 80, "formula": "Number of governance systems reviewed/Total number of governance systems scheduled for review", "score": 0, "team_objective": 63, "status": 1},
            {"id": 127, "name": "Number of reports scheduled for submission to the audit committee, concluded three weeks prior to the meeting/", "target": 80, "formula": "Number of reports submitted to the audit committee or concluded three weeks prior to the meeting/Total Number of reports scheduled for submission to the audit committee, concluded three weeks prior to the meeting.", "score": 75, "team_objective": 64, "status": 1},
            {"id": 129, "name": "Percentage of staff using the HRA self service portals", "target": 80, "formula": "(Number of staff using HRA self service portals/Total number of staff)*100", "score": 0, "team_objective": 65, "status": 1},
            {"id": 144, "name": "Proportion of sensitizations/engagements with risk champions", "target": 80, "formula": "Number of sensitizations/engagements with risk champions conducted/ Total number of planned engagements", "score": 100, "team_objective": 66, "status": 1},
            {"id": 145, "name": "Proportion of Business units/departments sensitized on risk management", "target": 80, "formula": "No. of business units/departments sensitized on risk management/ Total no. of business units", "score": 0, "team_objective": 67, "status": 1},
            {"id": 146, "name": "Percentage of risk coordination reports meeting the quality standards/checklist (80 %)", "target": 80, "formula": "No. of risk assignments meeting 80% quality standard/Total No. of completed assignments", "score": 100, "team_objective": 68, "status": 1},
            {"id": 147, "name": "Percentage of the risk universe with updated risk information", "target": 80, "formula": "No. of risk universe with updated risk information / Total No. of risk universe", "score": 100, "team_objective": 69, "status": 1},
            {"id": 148, "name": "Percentage of scheduled business units with risk updates", "target": 80, "formula": "No. of scheduled business units with risk updates / Total No. of business units scheduled for risk updates", "score": 100, "team_objective": 70, "status": 1},
            {"id": 149, "name": "Percentage of business units with updated compliance registers", "target": 80, "formula": "No. of business units with updated compliance information/Total no. of business units scheduled for compliance reviews", "score": 100, "team_objective": 71, "status": 1},
            {"id": 150, "name": "Percentage of audit assignments/reports meeting the quality standards/checklist", "target": 80, "formula": "No. of audit assignments meeting 80% quality standard/Total No. of completed assignments", "score": 100, "team_objective": 72, "status": 1},
            {"id": 151, "name": "Percentage of activities delivered within the set timelines for the two QoS assessment exercises", "target": 80, "formula": "(Activities carried out within the set timelines)/ (total number of activities ) for the 2 exercises* 100", "score": 67, "team_objective": 73, "status": 1},
            {"id": 152, "name": "Percentage of audit assignments performed using the audit tools & technology", "target": 80, "formula": "No. of audit tasks performed using existing tools& technology / Total No. of audit tasks scheduled to use audit tools & technology", "score": 100, "team_objective": 74, "status": 1},
            {"id": 153, "name": "Percentage of audit assignments performed using the audit tools & technology", "target": 80, "formula": "No. of audit tasks performed using existing tools& technology / Total No. of audit tasks scheduled to use audit tools & technology", "score": 0, "team_objective": 75, "status": 1},
            {"id": 154, "name": "Proportion of Internal audit (assurance) staff trained as per the skills gap", "target": 70, "formula": "Number of assurance staff trained in the FY 2022-23/ Total number of assurance staff scheduled for training in the FY 2022-23", "score": 0, "team_objective": 76, "status": 1},
            {"id": 155, "name": "Proportion of risk and compliance staff trained as per the skills gap", "target": 70, "formula": "Number of risk and compliance staff trained in the FY 2022-23/ Total number of staff scheduled for training in the FY 2022-23", "score": 0, "team_objective": 77, "status": 1},
            {"id": 156, "name": "Proportion of Internal audit (assurance) staff attaining the 65% performance appraisal score", "target": 80, "formula": "Number of Assurance staff attaining 65% performance appraisal score in the FY 2022-23/Total of number of staff in the team in the FY 2022-23", "score": 0, "team_objective": 78, "status": 1},
            {"id": 157, "name": "Proportion of Risk and Compliance staff attaining the 65% performance appraisal score", "target": 80, "formula": "Number of Risk and Compliance staff attaining 65% performance appraisal score in the FY 2022-23/Total of number of staff in the team in the FY 2022-23", "score": 0, "team_objective": 79, "status": 1},
            {"id": 158, "name": "Percentage of cases of interference investigated and reported within the ECI Charter timelines", "target": 75, "formula": "(Number of cases of interference handled & reported/Total number of cases of interference received) *100", "score": 85, "team_objective": 80, "status": 1},
            {"id": 160, "name": "% of quarterly radio frequency utilization reports submitted in the financial year (X/(no. of quarters considered)", "target": 100, "formula": "Number of quarterly reports submitted/Total expected reports in a year*100", "score": 51, "team_objective": 81, "status": 1},
            {"id": 161, "name": "Percentage of assigned numbering resources in use", "target": 80, "formula": "(Number of assigned numbering resources per block in use/total number of assigned numbering resources per block)*100", "score": 38, "team_objective": 82, "status": 1},
            {"id": 168, "name": "Percentage of technical evaluations for licenses completed within the ECI specified time", "target": 83, "formula": "(Number of technical evaluations for licenses completed in line with the department charter/Total number of license applications received) *100", "score": 95, "team_objective": 83, "status": 1},
            {"id": 170, "name": "Percentage of Spectrum Assignees with information on compliance status not more than six months old", "target": 85, "formula": "(Number of licensees with Spectrum Assignees whose information is six months or less/total number of Spectrum Assignees) *100", "score": 94, "team_objective": 84, "status": 1},
            {"id": 173, "name": "Percentage of SMD workplan activities implemented as scheduled", "target": 85, "formula": "(Number of SMD workplan activities implemented as scheduled/total number of SMD workplan activities planned) *100", "score": 78, "team_objective": 85, "status": 1},
            {"id": 175, "name": "Percentage smd tools utilization as per agreed criteria", "target": 80, "formula": "(Number of SMD tools utilized as per agreed criteria/Total number of tools)*100", "score": 100, "team_objective": 86, "status": 1},
            {"id": 182, "name": "Stakeholder satisfaction score", "target": 80, "formula": "Snap short project surveys", "score": 83, "team_objective": 87, "status": 1},
            {"id": 183, "name": "Percentage of technical audit completed within three weeks", "target": 70, "formula": "Number od technical audits completed/Total number of technical audits*100%", "score": 95, "team_objective": 88, "status": 1},
            {"id": 184, "name": "Percentage of project monitoring activities completed as per schedule", "target": 80, "formula": "Number of project monitoring activities done/Total number of projects*100%", "score": 79, "team_objective": 89, "status": 1},
            {"id": 185, "name": "Percentage of projects initiated as per schedule/ workplan", "target": 90, "formula": "(Number of projects initiated/Total number of projects in the workplan)*100%", "score": 90, "team_objective": 90, "status": 1},
            {"id": 186, "name": "Percentage of projects executed as per schedule", "target": 90, "formula": "(Number of projects executed/Total number of projects in the schedule)*100", "score": 47, "team_objective": 91, "status": 1},
            {"id": 187, "name": "Percentage of Projects rolled over to the next year", "target": 25, "formula": "(Number of projects rolled over/Total number of projects implemented)*100", "score": 42, "team_objective": 92, "status": 1},
            {"id": 188, "name": "Percentage of correspondences completed as per the charter", "target": 80, "formula": "(Number of correspondences answered/Total number of correspondences received)*100%", "score": 61, "team_objective": 93, "status": 1},
            {"id": 189, "name": "User satisfaction score for ICT Services", "target": 80, "formula": "Percentage score attained", "score": 74, "team_objective": 94, "status": 1},
            {"id": 190, "name": "User satisfaction score for ISU Services", "target": 80, "formula": "Percentage score attained", "score": 64, "team_objective": 95, "status": 1},
            {"id": 191, "name": "User satisfaction score for CERT Services", "target": 80, "formula": "Percentage score attained", "score": 0, "team_objective": 95, "status": 1},
            {"id": 192, "name": "Percentage of queries responded to as per the charter", "target": 90, "formula": "(Number of querries responded to as per the charter/Total Number of Queries received)*100", "score": 95, "team_objective": 96, "status": 1},
            {"id": 193, "name": "Percentage of databases compiled within specified time", "target": 80, "formula": "(Number of databases compiled within the specified time/Total Number of databases set out to be done)*100", "score": 0, "team_objective": 97, "status": 1},
            {"id": 194, "name": "Percentage of queries responded to as per the charter", "target": 90, "formula": "(Number of querries responded to as per the charter/Total Number of Queries received)*100", "score": 0, "team_objective": 98, "status": 1},
            {"id": 195, "name": "Percentage of queries responded to as per the charter", "target": 90, "formula": "(Number of querries responded to as per the charter/Total Number of Querries received)*100", "score": 0, "team_objective": 99, "status": 1},
            {"id": 196, "name": "Proportion of digital initiatives implemented as per the agreed project plans/road maps", "target": 80, "formula": "(Number of Digital initiatives implemented as per agreed project plan/road map/Total No. of Digital initiatives scheduled to be implemented)*100", "score": 80, "team_objective": 100, "status": 1},
            {"id": 197, "name": "Percentage of quarterly reports produced on Implementation of sector cyber security strategy", "target": 20, "formula": "(Number of Quarterly reports produced/Total Number planned)*100", "score": 0, "team_objective": 101, "status": 1},
            {"id": 198, "name": "Commission Cyber Readiness index", "target": 75, "formula": "(Number of monthly reports presented to the Board/Total  reports planned)*100", "score": 0, "team_objective": 102, "status": 1},
            {"id": 199, "name": "Percentage Expenditure within budget", "target": 100, "formula": "(Actual IT team expenditure/Total budget allocation to IT Team)*100", "score": 100, "team_objective": 103, "status": 1},
            {"id": 200, "name": "Percentage Expenditure within budget", "target": 100, "formula": "(Actual ISU team expenditure/Total budget allocation to ISU Team)*100", "score": 0, "team_objective": 104, "status": 1},
            {"id": 201, "name": "Percentage Expenditure within budget", "target": 100, "formula": "(Actual CERT team expenditure/Total budget allocation to CERT Team)*100", "score": 0, "team_objective": 105, "status": 1},
            {"id": 202, "name": "Percentage Expenditure within budget", "target": 90, "formula": "(Actual Research team expenditure/Total budget allocation to Research Team)*100", "score": 100, "team_objective": 105, "status": 1},
            {"id": 203, "name": "Proportion of Budget Savings", "target": 2, "formula": "(Actual saved by IT team/Total budget allocation to IT Team)*100", "score": 3, "team_objective": 106, "status": 1},
            {"id": 204, "name": "Proportion of Budget Savings", "target": 20, "formula": "(Actual saved by ISU team/Total budget allocation to ISU Team)*100", "score": 0, "team_objective": 107, "status": 1},
            {"id": 205, "name": "Proportion of Budget Savings", "target": 20, "formula": "(Actual saved by CERT team/Total budget allocation to CERT Team)*100", "score": 0, "team_objective": 108, "status": 1},
            {"id": 206, "name": "Proportion of Budget Savings", "target": 20, "formula": "(Actual saved by Research team/Total budget allocation to Research Team)*100", "score": 0, "team_objective": 109, "status": 1},
            {"id": 207, "name": "Proportion of Audit issues issues identified and implemented", "target": 70, "formula": "(Number of Audit issues issues identified and implemented/Total Number of Audit Issues)*100", "score": 0, "team_objective": 110, "status": 1},
            {"id": 208, "name": "Proportion of Registers developed", "target": 50, "formula": "(No of departments with developed and updated registers /total No of Departments)*100", "score": 55, "team_objective": 111, "status": 1},
            {"id": 209, "name": "Proportion of Departments aligned to their respective processes in ERDMS", "target": 85, "formula": "(Number of departments aligned/Total number of departments)*100", "score": 60, "team_objective": 112, "status": 1},
            {"id": 210, "name": "Proportion of Information processed and organized in time as per the charter", "target": 85, "formula": "(Information processed and organized in charter timelines/Total information received)*100", "score": 90, "team_objective": 113, "status": 1},
            {"id": 211, "name": "Proportion of contracts/projects completed according to the specified terms of references", "target": 80, "formula": "(Number of contracts/projects completed according to the specified terms of references/ Total number in the FY)*100", "score": 54, "team_objective": 114, "status": 1},
            {"id": 212, "name": "Percentage Implementation of audit/risk recommendations within a financial year", "target": 80, "formula": "(Number of audit/risk recommendations implemented within a financial year/Total number of audit recommendations raised)*100", "score": 80, "team_objective": 115, "status": 1},
            {"id": 213, "name": "Percentage Implementation of audit/risk recommendations within a financial year", "target": 80, "formula": "Number of audit/risk recommendations implemented within a financial year/Total number of audit recommendations raised)*100", "score": 90, "team_objective": 116, "status": 1},
            {"id": 214, "name": "Percentage Implementation of audit/risk recommendations within a financial year", "target": 80, "formula": "(Number of audit/risk recommendations implemented within a financial year/Total number of audit recommendations raised)*100", "score": 0, "team_objective": 117, "status": 1},
            {"id": 215, "name": "Percentage of approved research reports", "target": 80, "formula": "(Number of approved research reports available( based on approved research agenda studies) for publication / Number of approved research agenda studies for FY 2022/23)*100", "score": 25, "team_objective": 118, "status": 1},
            {"id": 216, "name": "Proportion of information disseminated by the R&SD division versus studies conducted", "target": 80, "formula": "(Number of research studies conducted and disseminated/Total Number of studies conducted)*100", "score": 86, "team_objective": 119, "status": 1},
            {"id": 217, "name": "Proportion of Knowledge Sharings carried out", "target": 60, "formula": "(Number of Knwledge sharing sessions carried out/Total Number of Knowledge sharing sessions planned)*100", "score": 87, "team_objective": 120, "status": 1},
            {"id": 218, "name": "Proportion of Teams Service Charter KPIs attained", "target": 60, "formula": "(ICT Service Charter KPIs attained/Number of Service Charter KPIs)*100", "score": 0, "team_objective": 121, "status": 1},
            {"id": 219, "name": "Proportion of Teams Service Charter KPIs attained", "target": 60, "formula": "(ISU Service Charter KPIs attained/Number of Service Charter KPIs)*100", "score": 0, "team_objective": 122, "status": 1},
            {"id": 220, "name": "Proportion of Teams Service Charter KPIs attained", "target": 60, "formula": "(CERT Service Charter KPIs attained/Number of Service Charter KPIs)*100", "score": 0, "team_objective": 123, "status": 1},
            {"id": 221, "name": "Proportion of Teams Service Charter KPIs attained", "target": 60, "formula": "(Research Service Charter KPIs attained/Number of Service Charter KPIs)*100", "score": 0, "team_objective": 124, "status": 1},
            {"id": 222, "name": "Percentage of IT systems that are available", "target": 100, "formula": "(Number of IT systems available/ Number of IT systems monitored)*100", "score": 99, "team_objective": 125, "status": 1},
            {"id": 223, "name": "Percentage of Team processes and policies Reviewed", "target": 90, "formula": "(Number of IT Team processes and policies reviewed/Total Planned)*100", "score": 0, "team_objective": 126, "status": 1},
            {"id": 224, "name": "Percentage of Team processes and policies Reviewed", "target": 90, "formula": "(Number of ISU Team processes and policies reviewed/Total Planned)*100", "score": 0, "team_objective": 127, "status": 1},
            {"id": 225, "name": "Percentage of Team processes and policies Reviewed", "target": 90, "formula": "(Number of CERT Team processes and policies reviewed/Total Planned)*100", "score": 0, "team_objective": 128, "status": 1},
            {"id": 226, "name": "Percentage of trainings held", "target": 80, "formula": "(Number of trainings held/Total Number of planned trainings)*100", "score": 100, "team_objective": 129, "status": 1},
            {"id": 227, "name": "Proportion of information disseminated", "target": 80, "formula": "(Information disseminated/Number of studies conducted)*100", "score": 86, "team_objective": 130, "status": 1},
            {"id": 228, "name": "Percentage of tools and technologies used in execution of business processes", "target": 80, "formula": "(Number of tools and technologies used in execution of business processes/Total Number of tools and technologies available)*100", "score": 85, "team_objective": 131, "status": 1},
            {"id": 229, "name": "Percentage utilization of tools and technologies by staff for various Commission business processes", "target": 80, "formula": "(Number of tools and technologies used by staff for various Commission business processes/Total Number of tools and technologies available)*100", "score": 89, "team_objective": 132, "status": 1},
            {"id": 230, "name": "Percentage utilization of tools to execute division business processes", "target": 100, "formula": "(Number of tools used to execute division business processes/Total Number of tools available)*100", "score": 87, "team_objective": 133, "status": 1},
            {"id": 231, "name": "Percentage Increment in Usage of Resource Centre", "target": 75, "formula": "(Total No of Users in 2022/23/Total Number of users in 2021/22) -1*100", "score": 80, "team_objective": 134, "status": 1},
            {"id": 232, "name": "Proportion of Digitised information", "target": 80, "formula": "(Number of digitized information/ Total Physical Information Received)*100", "score": 0, "team_objective": 135, "status": 1},
            {"id": 233, "name": "Percentage of IT staff achieving 70% and above", "target": 70, "formula": "(Number of IT staff achieving 70% and above/Total Number of IT Staff)*100", "score": 100, "team_objective": 136, "status": 1},
            {"id": 234, "name": "Percentage of ISU staff achieving 70% and above", "target": 70, "formula": "(Number of ISU staff achieving 70% and above/Total Number of ISU Staff)*100", "score": 100, "team_objective": 137, "status": 1},
            {"id": 235, "name": "Percentage of CERT staff achieving 70% and above", "target": 70, "formula": "(Number of CERT staff achieving 70% and above/Total Number of ISU Staff)*100", "score": 0, "team_objective": 138, "status": 1},
            {"id": 236, "name": "Percentage of Research staff achieving 70% and above", "target": 70, "formula": "(Number of Research staff achieving 70% and above/Total Number of ISU Staff)*100", "score": 75, "team_objective": 139, "status": 1},
            {"id": 237, "name": "Percentage of IT team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of IT team targets)*100", "score": 60, "team_objective": 140, "status": 1},
        ]

        team_kpis_created = 0
        team_kpis_skipped = 0
        kpi_scores_created = 0

        for kpi_data in team_kpis_data:
            # Get team objective using team_objective index from team_objectives_data
            team_obj_idx = kpi_data.get("team_objective")
            if not team_obj_idx:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping Team KPI '{kpi_data['name']}' - no team_objective specified")
                )
                team_kpis_skipped += 1
                continue
            
            team_objective = team_obj_data_idx_to_team_obj.get(team_obj_idx)
            if not team_objective:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping Team KPI '{kpi_data['name']}' - team objective index {team_obj_idx} not found")
                )
                team_kpis_skipped += 1
                continue

            # Infer KPI properties
            code = self.generate_kpi_code(kpi_data["name"], team_obj_id=team_objective.id)
            direction = self.infer_direction(kpi_data["name"], kpi_data.get("formula", ""))
            indicator_type = self.infer_indicator_type(kpi_data["name"], kpi_data.get("formula", ""))
            reporting_period = self.infer_reporting_period(kpi_data["name"], kpi_data.get("formula", ""))
            scoring_config = self.infer_scoring_config(kpi_data["name"], Decimal(str(kpi_data["target"])) if kpi_data.get("target") else None)
            
            # Determine unit
            unit = "%"
            if "score" in kpi_data["name"].lower() and "%" not in kpi_data["name"]:
                unit = "score"
            elif "days" in kpi_data["name"].lower() or "time" in kpi_data["name"].lower():
                unit = "days"
            elif "ugx" in kpi_data["name"].lower() or "revenue" in kpi_data["name"].lower() or "budget" in kpi_data["name"].lower():
                unit = "UGX"

            # Create team KPI
            kpi, created = KPI.objects.get_or_create(
                code=code,
                defaults={
                    "name": kpi_data["name"],
                    "description": f"KPI for {team_objective.team_objective_name}",
                    "team_objective": team_objective,
                    "formula": kpi_data.get("formula", ""),
                    "unit": unit,
                    "direction": direction,
                    "indicator_type": indicator_type,
                    "reporting_period": reporting_period,
                    "weight": Decimal("100.0"),
                    "scoring_config": scoring_config,
                    "is_composite": False,
                    "metadata": {},
                    "owner_id": team_objective.team.lead_id if team_objective.team.lead_id else None,
                },
            )
            if created:
                team_kpis_created += 1
                self.stdout.write(f"  ✓ Created Team KPI: {kpi.code} - {kpi.name}")

            # Create KPIValue for target/actual if provided
            kpi_value = None
            if kpi_data.get("target") or kpi_data.get("score"):
                today = date.today()
                period_start = date(today.year, today.month, 1)
                last_day = monthrange(today.year, today.month)[1]
                period_end = date(today.year, today.month, last_day)
                
                kpi_value, value_created = KPIValue.objects.get_or_create(
                    kpi=kpi,
                    period_start=period_start,
                    period_end=period_end,
                    defaults={
                        "target": Decimal(str(kpi_data["target"])) if kpi_data.get("target") else None,
                        "actual": Decimal(str(kpi_data["score"])) if kpi_data.get("score") else None,
                        "notes": f"Initial value from legacy data (old measure ID: {kpi_data.get('id', 'N/A')})",
                    }
                )

            # Create KPIScore if score exists and KPIValue was created
            if kpi_data.get("score") is not None and kpi_data["score"] > 0 and kpi_value:
                # Check if score already exists
                if not hasattr(kpi_value, 'score'):
                    # Import compute_kpi_score to calculate proper score
                    from indicators.utils import compute_kpi_score
                    try:
                        kpi_score = compute_kpi_score(kpi, kpi_value)
                        kpi_scores_created += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠ Could not compute score for KPI {kpi.code}: {str(e)}")
                        )

        self.stdout.write(
            self.style.SUCCESS(f"✓ Created {team_kpis_created} Team KPIs")
        )
        if team_kpis_skipped > 0:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Skipped {team_kpis_skipped} Team KPIs")
            )
        self.stdout.write(
            self.style.SUCCESS(f"✓ Created {kpi_scores_created} KPI Scores")
        )

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Departments and department objectives setup completed successfully!"))
        self.stdout.write("=" * 60)
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Organization data setup completed successfully!"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Organization: {organization.name}")
        self.stdout.write(f"Vision: {vision.statement[:50]}...")
        self.stdout.write(f"Mission: {mission.statement[:50]}...")
        self.stdout.write(f"Strategic Plan Periods: {StrategicPlanPeriod.objects.filter(organization=organization).count()}")
        self.stdout.write(f"Perspectives: {Perspective.objects.filter(organization=organization).count()}")
        self.stdout.write(f"Financial Years: {FinancialYear.objects.filter(strategic_plan_period=strategic_plan).count()}")
        self.stdout.write(f"Organization: {organization.name}")
        self.stdout.write(f"Departments: {Department.objects.filter(organization=organization).count()}")
        self.stdout.write(f"Department Objectives: {DepartmentObjective.objects.filter(department__organization=organization).count()}")
        self.stdout.write(f"Teams: {Team.objects.filter(department__organization=organization).count()}")
        self.stdout.write(f"Team Objectives: {TeamObjective.objects.filter(team__department__organization=organization).count()}")
        self.stdout.write(f"Department KPIs: {KPI.objects.filter(department_objective__department__organization=organization).count()}")
        self.stdout.write(f"Team KPIs: {KPI.objects.filter(team_objective__team__department__organization=organization).count()}")
        self.stdout.write(f"KPI Values: {KPIValue.objects.filter(kpi__department_objective__department__organization=organization).count() + KPIValue.objects.filter(kpi__team_objective__team__department__organization=organization).count()}")
        self.stdout.write(f"KPI Scores: {KPIScore.objects.filter(kpi_value__kpi__department_objective__department__organization=organization).count() + KPIScore.objects.filter(kpi_value__kpi__team_objective__team__department__organization=organization).count()}")
        self.stdout.write("=" * 60)