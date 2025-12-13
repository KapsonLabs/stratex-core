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
                    "cap": 120,
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
            "cap": 120,
            "null_policy": "zero"
        }

    def handle(self, *args, **options):
        self.stdout.write("Setting up departments and department objectives...")

        # Get organization with id 1
        try:
            organization = Organization.objects.get(id=1)
            self.stdout.write(f"✓ Found organization: {organization.name}")
        except Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR("Organization with id 1 does not exist!"))
            return

        # Map old department IDs to department names for reference
        old_dept_id_to_name = {
            3: "Legal",
            4: "Corporate Affairs",
            9: "Industry Affairs and Content",
            10: "Engineering & Communication Infrastructure",
            11: "Human Resources and Administration",
            12: "Uganda Communications Universal Service Access Fund",
            13: "ICT & Research",
            14: "Internal Audit",
            15: "Finance",
        }

        # 1. Create or get Departments
        self.stdout.write("Creating/Getting Departments...")
        department_map = {}
        departments_data = [
            {
                "name": "Legal",
                "description": "To Provide Expert & Efficient Legal Advisory & Procurement services to facilitate execution of the Commissions Mandate",
                "head_id": 8,
            },
            {
                "name": "Corporate Affairs",
                "description": "To Facilitate the Development & Implementation of UCC's Strategy and Strengthen Credibility that Fosters Sustainable Relationships for the Commission",
                "head_id": 9,
            },
            {
                "name": "Industry Affairs and Content",
                "description": "Promote Industry Competitiveness & Consumer Protection for Quality Communication User Experience",
                "head_id": 5,
            },
            {
                "name": "Engineering & Communication Infrastructure",
                "description": "To Develop & Implement Innovative & Responsive Technical Regulatory Tools that Drive the Development of the Communications Sector",
                "head_id": 4,
            },
            {
                "name": "Human Resources and Administration",
                "description": "To Provide Innovative Human Resource Solutions & Efficient Administrative Services that Delivers a Conducive Workplace which Promotes a Productive Workforce & Operational Efficiency",
                "head_id": 6,
            },
            {
                "name": "Uganda Communications Universal Service Access Fund",
                "description": "To Facilitate Universal Access to Communication Services in Uganda",
                "head_id": 5,
            },
            {
                "name": "ICT & Research",
                "description": "To Enhance Our Customers Decision through Knowledge Generation and Innovative ICT Solutions",
                "head_id": 4,
            },
            {
                "name": "Internal Audit",
                "description": "To Provide Objective Independent Assurance & Advisory Services that Minimize Organizational Risks, Improve Controls and Enhance Governance",
                "head_id": 5,
            },
            {
                "name": "Finance",
                "description": "To Provide Professional & Efficient Financial Management & Advisory Services That Optimises Resource use in UCC",
                "head_id": 5,
            },
        ]

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
            {"title": "Increase Stakeholder satisfaction", "dept_name": "Legal", "composite_weight": 70, "target": 70, "objective_name": "Increase Communications User satisfaction", "status": "active"},
            {"title": "Strengthen Regulatory Frameworks", "dept_name": "Legal", "composite_weight": 80,  "target": 70, "objective_name": "Improve Regulatory Processes", "status": "active"},
            {"title": "Optimize Resources", "dept_name": "Legal", "composite_weight": 80, "target": 75, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve Board, Legal and PDU Compliance Management", "dept_name": "Legal", "composite_weight": 80, "target": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve Board, Legal and PDU Process Efficiency", "dept_name": "Legal", "composite_weight": 70, "target": 70, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Strengthen Legal and PDU Risk Management", "dept_name": "Legal", "composite_weight": 70, "target": 70, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Promote use of communication services", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 11, "target": 60, "objective_name": "Increase Communications User satisfaction", "status": "active"},
            {"title": "Improve UCUSAF operational efficiency", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 11, "target": 60, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Increase project monitoring turnaround", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 80, "target": 80, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve project conceptualization", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 90, "target": 90, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve contract management", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 90, "target": 90, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve Resource Mobilisation and Use", "dept_name": "Finance", "composite_weight": 100, "target": 70, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Increase Customer & Stakeholder Satisfaction", "dept_name": "Finance", "composite_weight": 80, "target": 80, "objective_name": "Increase Communications User satisfaction", "status": "active"},
            {"title": "Decrease Number of Rolled Over projects", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 25, "target": 65, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Enhance Financial Accountability", "dept_name": "Finance", "composite_weight": 80, "target": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Strengthen stakeholder relationships", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 80, "target": 85, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve Revenue Management", "dept_name": "Finance", "composite_weight": 100, "target": 70, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve customer & stakeholder satisfaction", "dept_name": "Human Resources and Administration", "composite_weight": 80, "target": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Strengthen Expenditure Management", "dept_name": "Finance", "composite_weight": 85, "target": 85, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Strengthen Financial Reporting", "dept_name": "Finance", "composite_weight": 90, "target": 90, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Increase employee productivity", "dept_name": "Human Resources and Administration", "composite_weight": 88, "target": 88, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Optimize HRA resources", "dept_name": "Human Resources and Administration", "composite_weight": 95, "target": 95, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Enhance Planning & Budgeting", "dept_name": "Finance", "composite_weight": 100, "target": 100, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve DF Skills, Knowledge & Abilities", "dept_name": "Finance", "composite_weight": 100, "target": 100, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Improve HRA operational efficiency", "dept_name": "Human Resources and Administration", "composite_weight": 11, "target": 60, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Enhance UCC Business success", "dept_name": "Legal", "composite_weight": 80, "target": 75, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Staff Performance", "dept_name": "Legal", "composite_weight": 80, "target":70, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Improve/Promote good governance", "dept_name": "Internal Audit", "composite_weight": 75, "target": 75, "objective_name": "Maximize Stakeholder Value", "status": "active"},
            {"title": "Improve HRA tools & Technology", "dept_name": "Human Resources and Administration", "composite_weight": 11, "target": 60, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Improve timely conclusion of complaints •Consumer complaints •Content complaints •Licensee disputes", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve the timely availability of information to stakeholders •Market reports •Consumer advisories •Content quota reports •Competition scans", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Reduce cost of doing business/operation", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Enhance Stakeholder Collaboration", "dept_name": "Internal Audit", "composite_weight": 75, "target": 75, "objective_name": "Maximize Stakeholder Value", "status": "active"},
            {"title": "Optimise Financial Resource Use", "dept_name": "Internal Audit", "composite_weight": 90, "target": 90, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve quality of audit services", "dept_name": "Internal Audit", "composite_weight": 80, "target": 80, "objective_name": "Maximize Stakeholder Value", "status": "active"},
            {"title": "Enhance UCC business process", "dept_name": "Internal Audit", "composite_weight": 70, "target": 70, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Strengthen coordination of Risk management", "dept_name": "Internal Audit", "composite_weight": 70, "target": 70, "objective_name": "Maximize Stakeholder Value", "status": "active"},
            {"title": "Improve responsiveness of the regulatory frameworks and standards", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective_name": "Improve Regulatory Processes", "status": "active"},
            {"title": "Improve the timeliness of DIAC's plan execution, compliance activities and assessment decisions", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective_name": "Improve Regulatory Processes", "status": "active"},
            {"title": "Improve IAC Tools & Technology capability for better work environment & processes •Online data portal •Digital logger •Call Centre", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "target": 60, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Strengthen Internal Compliance Monitoring", "dept_name": "Internal Audit", "composite_weight": 80, "target": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve Quality of Communication services offered by Licensees", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 11, "target": 60, "objective_name": "Promote Sector Competitiveness", "status": "active"},
            {"title": "Improve IA Tools and Technologies", "dept_name": "Internal Audit", "composite_weight": 80, "target": 80, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Improve IA Skills, knowledge and Abilities", "dept_name": "Internal Audit", "composite_weight": 75, "target": 75, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Improve utilization of Communication Resources (Spectrum, Numbering and Electronic Addressing/LCNs)", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 80, "target": 80, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve the timeliness of ECI's actions, compliance activities and assessment decisions", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 83, "target": 83, "objective_name": "Improve Regulatory Processes", "status": "active"},
            {"title": "Improve availability of our technical tools to be used when required", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 80, "target": 80, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Improve customer and stakeholder satisfaction", "dept_name": "ICT & Research", "composite_weight": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve cyber security", "dept_name": "ICT & Research", "composite_weight": 60, "target": 60, "objective_name": "Increase Communications User satisfaction", "status": "active"},
            {"title": "Optimize ICT&R resources", "dept_name": "ICT & Research", "composite_weight": 100, "target": 100, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Strengthen risk Management", "dept_name": "ICT & Research", "composite_weight": 80, "target": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Enhance Knowledge Management", "dept_name": "ICT & Research", "composite_weight": 67, "target": 67, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Improve Operational efficiency", "dept_name": "ICT & Research", "composite_weight": 60, "target": 60, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve Tools and Technology", "dept_name": "ICT & Research", "composite_weight": 80, "target": 80, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Enhance Staff Performance", "dept_name": "ICT & Research", "composite_weight": 70, "target": 70, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Enhance UCC Business success", "dept_name": "ICT & Research", "composite_weight": 80, "target": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve stakeholder awareness", "dept_name": "Corporate Affairs", "composite_weight": 70, "target": 70, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Enhance visibility and image of UCC Brand", "dept_name": "Corporate Affairs", "composite_weight": 80, "target": 80, "objective_name": "Enhance Organizational Culture", "status": "active"},
            {"title": "Enhance UCC Business Success", "dept_name": "Corporate Affairs", "composite_weight": 80, "target": 80, "objective_name": "Promote Sector Competitiveness", "status": "active"},
            {"title": "Minimize Budget Variance", "dept_name": "Corporate Affairs", "composite_weight": 90, "target": 90, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve Corporate Performance Reporting", "dept_name": "Corporate Affairs", "composite_weight": 80, "target": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Enhance coordination of CA Internal stakeholders", "dept_name": "Corporate Affairs", "composite_weight": 75, "target": 75, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Increase CA System & Process Efficiency", "dept_name": "Corporate Affairs", "composite_weight": 70, "target": 70, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Improve productivity of Corporate Affairs Staff", "dept_name": "Corporate Affairs", "composite_weight": 80, "target": 80, "objective_name": "Improve Staff Skills Knowledge and Abilities", "status": "active"},
            {"title": "Improve CA Tools & Technology", "dept_name": "Corporate Affairs", "composite_weight": 50, "target": 50, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Improve Skills, Knowledge & Abilities", "dept_name": "Industry Affairs and Content", "composite_weight": 70, "target": 70, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
        ]

        dept_objectives_created = 0
        dept_objectives_skipped = 0
        # Map old department objective IDs to new DepartmentObjective objects
        # This mapping is based on the order in the SQL and the title
        old_dept_obj_id_to_dept_obj = {}

        for idx, dept_obj_data in enumerate(dept_objectives_data):
            # Get department
            department = department_map.get(dept_obj_data["dept_name"])
            if not department:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping department objective '{dept_obj_data['title']}' - department '{dept_obj_data['dept_name']}' not found")
                )
                dept_objectives_skipped += 1
                continue

            # Get strategic objective
            objective = objective_map.get(dept_obj_data["objective_name"])
            if not objective:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping department objective '{dept_obj_data['title']}' - strategic objective '{dept_obj_data['objective_name']}' not found")
                )
                dept_objectives_skipped += 1
                continue

            # Map status: "active" -> "in_progress"
            status = "in_progress" if dept_obj_data["status"] == "active" else "draft"

            # Create department objective
            dept_objective, created = DepartmentObjective.objects.get_or_create(
                department=department,
                objective=objective,
                department_objective_name=dept_obj_data["title"],
                defaults={
                    "composite_weight": Decimal(str(dept_obj_data["composite_weight"])),
                    "status": status,
                    "objective_target": Decimal(str(dept_obj_data["composite_weight"])),
                },
            )
            if created:
                dept_objectives_created += 1
                self.stdout.write(f"  ✓ Created department objective: {dept_obj_data['title']}")
            
            # Map old department objective IDs (from SQL) to new DepartmentObjective
            # Mapping based on the order in dept_objectives_data and the SQL IDs
            # SQL IDs: 9, 17, 18, 19, 20, 21, 22, 23, 24, 25, 28, 29, 30, 33, 34, 35, 36, 38, 42, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 78, 79, 80, 81, 82, 83, 84, 85, 86, 92, 93, 94, 95, 96, 97, 98, 99, 100, 102, 103, 104
            old_dept_obj_ids = [9, 17, 18, 19, 20, 21, 22, 23, 24, 25, 28, 29, 30, 33, 34, 35, 36, 38, 42, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 78, 79, 80, 81, 82, 83, 84, 85, 86, 92, 93, 94, 95, 96, 97, 98, 99, 100, 102, 103, 104]
            # Always add to mapping (whether created or already existed)
            if idx < len(old_dept_obj_ids):
                old_dept_obj_id_to_dept_obj[old_dept_obj_ids[idx]] = dept_objective

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
            {"name": "PIR", "dept_old_id": 4, "lead_id": 7},
            {"name": "SBP", "dept_old_id": 4, "lead_id": 5},
            {"name": "Regional Offices", "dept_old_id": 4, "lead_id": 4},
            {"name": "Board Affairs", "dept_old_id": 3, "lead_id": 7},
            {"name": "Litigation Unit", "dept_old_id": 3, "lead_id": 7},
            {"name": "Legal Affairs", "dept_old_id": 3, "lead_id": 7},
            {"name": "Compliance and Enforcement", "dept_old_id": 3, "lead_id": 7},
            {"name": "Procurement", "dept_old_id": 3, "lead_id": 7},
            {"name": "Human Resources", "dept_old_id": 11, "lead_id": None},
            {"name": "Administration", "dept_old_id": 11, "lead_id": 7},
            {"name": "Expenditure Unit", "dept_old_id": 15, "lead_id": 7},
            {"name": "Revenue Unit", "dept_old_id": 15, "lead_id": 7},
            {"name": "Management Accounts", "dept_old_id": 15, "lead_id": 7},
            {"name": "Risk and Compliance", "dept_old_id": 14, "lead_id": 7},
            {"name": "Assurance", "dept_old_id": 14, "lead_id": 7},
            {"name": "Communications Infrastructure Services", "dept_old_id": 10, "lead_id": 7},
            {"name": "Spectrum Management Division", "dept_old_id": 10, "lead_id": 7},
            {"name": "UCUSAF", "dept_old_id": 12, "lead_id": 5},
            {"name": "IT&S", "dept_old_id": 13, "lead_id": 5},
            {"name": "ISU", "dept_old_id": 13, "lead_id": 5},
            {"name": "CERT", "dept_old_id": 13, "lead_id": 5},
            {"name": "R&SD", "dept_old_id": 13, "lead_id": 5},
            {"name": "Multimedia and Content", "dept_old_id": 9, "lead_id": 7},
            {"name": "Economic Regulation and Competition", "dept_old_id": 9, "lead_id": 7},
            {"name": "Consumer Affairs", "dept_old_id": 9, "lead_id": 7},
            {"name": "Human Resource", "dept_old_id": 11, "lead_id": 9},
        ]

        teams_created = 0
        teams_skipped = 0

        for team_data in teams_data:
            # Map old department ID to department name, then get department object
            dept_name = old_dept_id_to_name.get(team_data["dept_old_id"])
            if not dept_name:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping team '{team_data['name']}' - department ID {team_data['dept_old_id']} not found")
                )
                teams_skipped += 1
                continue

            department = department_map.get(dept_name)
            if not department:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping team '{team_data['name']}' - department '{dept_name}' not found")
                )
                teams_skipped += 1
                continue

            # Handle empty lead_id (convert to None)
            lead_id = team_data["lead_id"] if team_data["lead_id"] else None

            # Create team
            team, created = Team.objects.get_or_create(
                department=department,
                name=team_data["name"],
                defaults={
                    "lead_id": lead_id,
                },
            )
            if created:
                teams_created += 1
                self.stdout.write(f"  ✓ Created team: {team.name} ({dept_name})")

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
            {"name": "Percentage of received stakeholder requests resolve", "old_dept_obj_id": 9, "target": 85, "formula": "(Number of of received stakeholder requests resolved/Total Number of stakeholder requests received)*100", "current_value": 14},
            {"name": "Percentage of planned engagements undertaken (DPP, UPF, industry bodies, Solicitor General, MoJCA, Judiciary, ULS)", "old_dept_obj_id": 9, "target": 85, "formula": "(Number of engagements undertaken (DPP, UPF, industry bodies, Solicitor General, MoJCA, Judiciary, ULS)/Total Number of planned engagements)*100", "current_value": 0},
            {"name": "Percentage of regulatory gaps identified with proposals", "old_dept_obj_id": 17, "target": 80, "formula": "(Number of regulatory gaps with proposals/total number of regulatory gaps identified) *100", "current_value": 0},
            {"name": "Percentage of procurements within budget", "old_dept_obj_id": 18, "target": 80, "formula": "(Number of procurements within budget/Total Number of procurements made)*100", "current_value": 0},
            {"name": "Percentage of procurements executed in time", "old_dept_obj_id": 18, "target": 80, "formula": "(Number of procurements executed in time/planned procurements)*100", "current_value": 0},
            {"name": "Percentage of operators notified on compliance and reporting processes within the month of May", "old_dept_obj_id": 19, "target": 80, "formula": "(Number of operators notified on compliance and reporting processes within the month of May /Total Number of operators)*100", "current_value": 0},
            {"name": "Percentage of departments engaged on compliance issues per quarter", "old_dept_obj_id": 19, "target": 80, "formula": "(Number of departments engaged on compliance issues per quarter/Total Number of Departments planned)*100", "current_value": 0},
            {"name": "Percentage of departments-initiated operator compliance issues addressed", "old_dept_obj_id": 19, "target": 80, "formula": "(Number of departments-initiated operator compliance issues addressed /Total Number of compliance issues initiated)*100", "current_value": 0},
            {"name": "Percentage of PPDA Audit issues addressed", "old_dept_obj_id": 19, "target": 80, "formula": "(Number of PPDA Audit issues addressed/Total Number of PPDA Audit Issues raised)*100", "current_value": 0},
            {"name": "Stakeholder satisfaction score", "old_dept_obj_id": 22, "target": 80, "formula": "Survey score", "current_value": 0},
            {"name": "Percentage of technical audit completed within three weeks", "old_dept_obj_id": 23, "target": 70, "formula": "Number of technical audits completed/Total number of technical audits*100", "current_value": 0},
            {"name": "Percentage of project monitoring activities completed as per schedule", "old_dept_obj_id": 24, "target": 80, "formula": "Number of project monitoring activities done/Total number of projects*100", "current_value": 0},
            {"name": "Percentage of projects initiated as per schedule/workplan", "old_dept_obj_id": 25, "target": 90, "formula": "Number of projects initiated/Total number of projects in the workplan *100", "current_value": 0},
            {"name": "Percentage of projects executed as per schedule", "old_dept_obj_id": 28, "target": 90, "formula": "Number of projects executed/Total number of projects in the schedule*100", "current_value": 0},
            {"name": "Budget Absorption Rate", "old_dept_obj_id": 29, "target": 100, "formula": "(Actual Expenditure/Budgeted Amount)*100", "current_value": 0},
            {"name": "Percentage of creditors below 30 days", "old_dept_obj_id": 30, "target": 80, "formula": "(Number of creditors below 30 days/Total Number of creditors)*100", "current_value": 0},
            {"name": "Percentage Expenditure aligned to Strategy", "old_dept_obj_id": 29, "target": 100, "formula": "Percentage of analysis of actual vs strategy", "current_value": 0},
            {"name": "Percentage Increase in Revenue", "old_dept_obj_id": 33, "target": 5, "formula": "Revenue Growth = 100*(Current FY Revenue - Previous FY Revenue)/Previous FY Revenue", "current_value": 0},
            {"name": "Percentage of projects rolled over to the next year", "old_dept_obj_id": 34, "target": 25, "formula": "Number of projects rolled over/Total number of projects implemented*100", "current_value": 0},
            {"name": "Percentage of identified audit recommendations implemented", "old_dept_obj_id": 35, "target": 80, "formula": "(Number of audit recommendations implemented/ Total number of audit recommendations identified.)*100", "current_value": 0},
            {"name": "Percentage of identified Board/TMT recommendations implemented", "old_dept_obj_id": 35, "target": 80, "formula": "(Number of Board and TMT recommendations implemented/Total number of audit recommendations identified)*100", "current_value": 0},
            {"name": "Percentage of correspondences completed as per the charter", "old_dept_obj_id": 36, "target": 80, "formula": "Number of correspondences answered/Total number of correspondences received*100", "current_value": 0},
            {"name": "Percentage of Revenues Billed", "old_dept_obj_id": 38, "target": 100, "formula": "(Amount of Revenues Billed/Amount of Revenue Budgeted)*100", "current_value": 0},
            {"name": "Percentage of Revenues Collected", "old_dept_obj_id": 38, "target": 80, "formula": "(Amount of Revenues collected/Amount of Revenue Budgeted)*100", "current_value": 0},
            {"name": "Percentage of Debtors below 90 days", "old_dept_obj_id": 38, "target": 85, "formula": "(Number of Debtors below 90 days/Total Number of Debtors)*100", "current_value": 0},
            {"name": "Employee satisfaction score", "old_dept_obj_id": 42, "target": 80, "formula": "Staff satisfaction score| Benefits satisfaction| Services satisfaction survey score", "current_value": 0},
            {"name": "Percentage of Creditors below 90 Days", "old_dept_obj_id": 43, "target": 90, "formula": "(Number of Creditors below 60 days/Total Number of Creditors)*100", "current_value": 0},
            {"name": "Percentage of staff outstanding accountable advances below 60 days", "old_dept_obj_id": 43, "target": 80, "formula": "(Number of staff with outstanding accountable advances below 60 days/Total Number of staff with accountable advances)*100", "current_value": 0},
            {"name": "Percentage of service requests successfully handled within 7 days", "old_dept_obj_id": 42, "target": 70, "formula": "(Number of service requests successfully handled within 7 days/Total number of service requests received)*100", "current_value": 0},
            {"name": "Percentage of finance reports developed in line with the QA framework and submitted on agreed timelines", "old_dept_obj_id": 44, "target": 90, "formula": "(Number of finance reports developed in line with the QA framework and submitted on agreed timelines/ Total Number of Financial Reports produced)*100", "current_value": 0},
            {"name": "Percentage of staff who met performance targets", "old_dept_obj_id": 45, "target": 80, "formula": "(Number of staff scoring above 65%/Total number of eligible staff)*100", "current_value": 0},
            {"name": "Budget absorption rate", "old_dept_obj_id": 46, "target": 100, "formula": "(Actual expenditure/Amount in the HRA budget)*100", "current_value": 0},
            {"name": "Timeliness of budget preparation", "old_dept_obj_id": 47, "target": 100, "formula": "In accordance to PFMA", "current_value": 0},
            {"name": "Annual budget Report Quality Score", "old_dept_obj_id": 47, "target": 100, "formula": "In accordance to PFMA", "current_value": 0},
            {"name": "Skills gap", "old_dept_obj_id": 48, "target": 100, "formula": " Finance skills gap = (Number of Finance staff trained/Total number of HRA staff scheduled for training)*100", "current_value": 0},
            {"name": "Percentage of work plan activities implemented in time", "old_dept_obj_id": 51, "target": 80, "formula": "(Number of activities implemented in time/Total workplan activities)*100", "current_value": 0},
            {"name": "Percentage of Finance staff meeting intended performance goals", "old_dept_obj_id": 48, "target": 70, "formula": "Staff Productivity Score = (Number of Staff scoring above 70%/Total number of staff appraised)*100", "current_value": 0},
            {"name": "Percentage of Departmental targets achieved", "old_dept_obj_id": 52, "target": 80, "formula": "Number of Targets achieved/Total Number of Departmental Targets", "current_value": 0},
            {"name": "Percentage of legal staff achieving 65% and above", "old_dept_obj_id": 53, "target": 80, "formula": "(Number of staff achieving 65% and above /Total Number of staff in the department)*100", "current_value": 0},
            {"name": "Talent retention rate (High performing staff)", "old_dept_obj_id": 51, "target": 95, "formula": "(Number of staff retained with appraisal score above 70%/Total number of eligible staff in specified period)*100", "current_value": 0},
            {"name": "Post training evaluation score", "old_dept_obj_id": 51, "target": 80, "formula": "Percentage of training programs scores above 80%", "current_value": 0},
            {"name": "Percentage of quarterly reports submitted to the audit Committee within the schedule to the Committee meeting", "old_dept_obj_id": 54, "target": 75, "formula": "(Number of quarterly reports submitted as per schedule in the FY 2022-23/Total Number of Reports Planned)*100", "current_value": 0},
            {"name": "Percentage of reports on Board actions presented as per schedule", "old_dept_obj_id": 54, "target": 75, "formula": "(Number of reports on Board actions presented as per schedule in the FY 2022-23/Number of reports scheduled for presentation to TMT in the FY 2022-23)*100", "current_value": 0},
            {"name": "Percentage of HRA services conducted online", "old_dept_obj_id": 55, "target": 100, "formula": "Number of HRA services conducted online (Performance appraisal & leave)/Total number of HRA services*100", "current_value": 0},
            {"name": "Percentage of consumer related complaints concluded within the set timelines (2 weeks)", "old_dept_obj_id": 57, "target": 95, "formula": "Number of complaints for which the UCC decision has been communicated to the consumer in the set time/total number of consumer complaints received (call Centre, letters, email and social media)", "current_value": 0},
            {"name": "Percentage of content related complaints concluded within 20 working days", "old_dept_obj_id": 57, "target": 80, "formula": "Number of complaints for which a UCC ruling is communicated to the complainant in the set time/total number of content related complaints received", "current_value": 0},
            {"name": "Percentage of competition related complaints concluded within 45 working days", "old_dept_obj_id": 57, "target": 85, "formula": "Number of complaints for which a UCC ruling is issued to the complainant in the set time/total number of competition related complaints received", "current_value": 0},
            {"name": "Percentage of market reports ready for publication in the month following the respective quarter", "old_dept_obj_id": 58, "target": 75, "formula": "Number of quarterly reports approved for publication by ED the month following the respective quarter/4 (number of quarters in the year)", "current_value": 0},
            {"name": "Percentage of consumer advisories issued", "old_dept_obj_id": 58, "target": 62, "formula": "Number of weekly consumer notices put out/52 (number of weeks)", "current_value": 0},
            {"name": "Percentage of quarterly local quota assessment reports ready for publication in the month following the respective quarter", "old_dept_obj_id": 58, "target": 75, "formula": "Number of quarterly reports approved for publication by ED the month following the respective quarter/4 (number of quarters in the year)", "current_value": 0},
            {"name": "Percentage of available quarterly reports of competition market scans undertaken", "old_dept_obj_id": 58, "target": 50, "formula": "Number of quarterly competition reports presented to TMT in the month following the respective quarter/4 (number of quarters in the year)", "current_value": 0},
            {"name": "Percentage of cost centers in which a saving has been achieved versus budget •Publications •Events •Outreach  •Consultancies •Field work •Tools & equipment", "old_dept_obj_id": 59, "target": 66, "formula": "Number of cost centers implemented with at least 2% savings relative to budget/6 (number of cost centers)", "current_value": 0},
            {"name": "Percentage of reports on TMT actions presented as per schedule", "old_dept_obj_id": 54, "target": 75, "formula": "(Number of reports on TMT actions presented as per schedule in the FY 2022-23/Number of reports scheduled for presentation to TMT in the FY 2022-23)*100", "current_value": 0},
            {"name": "Proportion of internal stakeholder engagements accomplished as per schedule", "old_dept_obj_id": 60, "target": 75, "formula": "(Number of internal stakeholder engagements accomplished in the FY 2022-23/Total number of planned/scheduled engagements during the FY 2022-23)*100", "current_value": 0},
            {"name": "Proportion of expenditure requests for the department initiated on time", "old_dept_obj_id": 61, "target": 90, "formula": "(Number of expenditure requests initiated on time in the FY 2022-23/Total number of expenditure requests initiated)*100", "current_value": 0},
            {"name": "Percentage of contracts implemented within the contractual period", "old_dept_obj_id": 61, "target": 85, "formula": "(Number of contracts implemented within the contractual period during the FY 2022-23/Total number of scheduled contracts in the FY 2022-23)*100", "current_value": 0},
            {"name": "Proportion of departmental outputs accomplished as per schedule", "old_dept_obj_id": 62, "target": 80, "formula": "(Number of departmental assignments accomplished within set timelines during the FY 2022-23/ Total number of departmental assignments scheduled during the FY 2022-23)*100", "current_value": 0},
            {"name": "Proportion of audits accomplished within set quality standards", "old_dept_obj_id": 62, "target": 80, "formula": "(Number of audit, compliance, and risk assignments accomplished as per the set quality standards during the FY 2022-23/ Total Number of audit, compliance, and risk assignments implemented during the FY 2022-23)*100", "current_value": 0},
            {"name": "Proportion of investigations achieved per schedule", "old_dept_obj_id": 62, "target": 80, "formula": "(Number of investigations executed during the FY 2022-23/ Total number of investigations scheduled in the FY 2022-23)*100", "current_value": 0},
            {"name": "Proportion of quarterly action follow up reports submitted to the audit Committee as per schedule to the Committee meeting", "old_dept_obj_id": 62, "target": 80, "formula": "(Number of quarterly action follow up reports submitted as per reschedule during the FY 2022-23/Total number of actions follow up reports scheduled for submission to the Audit Committee for the FY 2022-23)*100", "current_value": 0},
            {"name": "Proportion of scheduled departmental outputs accomplished", "old_dept_obj_id": 63, "target": 70, "formula": "(Number of departmental assignments accomplished within the FY 2022-23/ Total number of scheduled departmental assignments for the FY 2022-23)*100", "current_value": 0},
            {"name": "Proportion of scheduled sensitizations/engagements conducted with Risk champions", "old_dept_obj_id": 64, "target": 70, "formula": "(Number of sensitizations/engagements (with Risk champions) implemented within the FY 2022-23/ Total number of sensitizations/engagements with Risk champions scheduled for the FY 2022-23)*100", "current_value": 0},
            {"name": "Percentage of identified regulatory frameworks/standards completed •Content distribution and exhibition •Roll over of unutilized data •Significant market power", "old_dept_obj_id": 65, "target": 80, "formula": "Number of identified regulatory frameworks completed/total number of frameworks identified for review", "current_value": 0},
            {"name": "Percentage of licensees with compliance status (based on report submitted & audits/inspections conducted) of not more than six months old  •Competition obligations •Postal  •Consumer", "old_dept_obj_id": 66, "target": 70, "formula": "Number of licensees with compliance information/total number of licensees", "current_value": 0},
            {"name": "Percentage of technical evaluations for licenses completed within the 14 days", "old_dept_obj_id": 66, "target": 70, "formula": "Number of technical evaluations for licenses completed in line within the set timelines/Total number of license applications received", "current_value": 0},
            {"name": "Percentage of departmental workplan activities implemented as scheduled", "old_dept_obj_id": 66, "target": 80, "formula": "Number of workplan items executed within planned period/ number of work plan items", "current_value": 0},
            {"name": "Average Availability Score •Criteria for availability/functionality for each tool/system to be set •Quarterly assessments for each tool against the respective criteria to determine tool availability", "old_dept_obj_id": 67, "target": 65, "formula": "Availability Score per Quarter= (No. of equipment meeting the established criteria/ total number of equipment) *100 \n&\nAverage   Availability Score = (FSQ1+ FSQ2+ FSQ3+ FSQ4)/4", "current_value": 0},
            {"name": "Proportion of sensitizations/engagements conducted with scheduled staff/departments", "old_dept_obj_id": 64, "target": 60, "formula": "(Number of sensitizations/engagements(with business units) implemented during the FY 2022/23/Total number of sensitization/engagements (with business units) scheduled for the FY 2022/23)*100", "current_value": 0},
            {"name": "Percentage of scheduled business units with updated compliance registers as per schedule", "old_dept_obj_id": 68, "target": 80, "formula": "(Number of business units' compliance registers updated during the FY2022-23/ Total number of business units' compliance registers scheduled for updates in the FY 2022-23*100", "current_value": 0},
            {"name": "Percentage of planned QoS publications/reports prepared (Three publications)", "old_dept_obj_id": 69, "target": 100, "formula": "(Number of publications issued/Total number of planned QoS publications) *100", "current_value": 0},
            {"name": "Percentage of reported cases of interference to telecom, FM radio & TV operations resolved", "old_dept_obj_id": 69, "target": 60, "formula": "(Number of reported cases of interference to telecom, FM radio & TV operations resolved/Total number of interference cases received) *100", "current_value": 0},
            {"name": "Proportion of assignments accomplished using the audit tools", "old_dept_obj_id": 72, "target": 80, "formula": "(Number of assignments performed during the FY 2022-23 using the audit tools/ Total number of assignments scheduled to use audit tools in the FY 2022-23)*100", "current_value": 0},
            {"name": "Proportion of Internal audit & risk staff trained as per the skills gap", "old_dept_obj_id": 73, "target": 70, "formula": "(Number of staff trained in the FY 2022-23/ Total number of staff scheduled for training in the FY 2022-23)*100", "current_value": 0},
            {"name": "Proportion of Internal audit & risk staff attaining the 65% performance appraisal score", "old_dept_obj_id": 73, "target": 80, "formula": "(Number of staff attaining 65% performance appraisal score in the FY 2022-23/Total of number of staff in the department in the FY 2022-23)*100", "current_value": 0},
            {"name": "Percentage of assigned resources in use (Spectrum, Numbering and Electronic Addressing/LCNs)", "old_dept_obj_id": 74, "target": 80, "formula": "(Number of assigned resources/Total Assigned Resources) *100", "current_value": 0},
            {"name": "Percentage of technical evaluations for licenses completed in line with the department charter", "old_dept_obj_id": 75, "target": 83, "formula": "(Number of technical evaluations for licences completed in line with the department charter/Total number of license applications received) *100", "current_value": 0},
            {"name": "Percentage of operators with information on compliance status not more than six months old", "old_dept_obj_id": 75, "target": 80, "formula": "(Number of licensees with compliance information that is six months or less/total number of licensees) *100", "current_value": 0},
            {"name": "Percentage of workplan activities implemented as scheduled", "old_dept_obj_id": 75, "target": 80, "formula": "(Number of workplan activities implemented as scheduled/total number of workplan activities planned) *100", "current_value": 0},
            {"name": "Average Availability Score", "old_dept_obj_id": 76, "target": 80, "formula": "Average Availability Score = (FSQ[1]1+ FSQ2+ FSQ3+ FSQ4)/4", "current_value": 0},
            {"name": "ICT/R user Satisfaction score", "old_dept_obj_id": 78, "target": 80, "formula": "Internal User Satisfaction survey score; rating of satisfaction of services", "current_value": 0},
            {"name": "Proportion of digital initiatives implemented as per the agreed project plans/road maps", "old_dept_obj_id": 78, "target": 75, "formula": "(Digital initiatives implemented as per agreed project plan/road map/Digital initiatives scheduled to be implemented)*100", "current_value": 0},
            {"name": "Corporate cyber security readiness level", "old_dept_obj_id": 79, "target": 60, "formula": "Readiness level as per the cyber security assessment guide (Ref: Corporate Cyber security framework)", "current_value": 0},
            {"name": "Proportion of Budget spent within cost", "old_dept_obj_id": 80, "target": 100, "formula": "(Actual ICT&R budget expenditure / Budget allocation to department of ICT&R for FY 2022/23)*100", "current_value": 0},
            {"name": "Budget spend cost savings", "old_dept_obj_id": 80, "target": 100, "formula": "IT&S Budget spend cost savings=(IT&S Budget allocation - Actual ICT budget expenditure) / Budget allocation to department of ICT&R for FY 2022/23)*100", "current_value": 0},
            {"name": "Proportion of risks mitigation measures implemented per function within the FY", "old_dept_obj_id": 81, "target": 80, "formula": "(Number of risks mitigation measures implemented per function within the FY/Total mitigants identified)*100", "current_value": 0},
            {"name": "Percentage of approved research reports available", "old_dept_obj_id": 82, "target": 67, "formula": "(Number of approved research reports available( based on approved research agenda studies) for publication / Number of approved research agenda studies for FY 2022/23)*100", "current_value": 0},
            {"name": "Proportion of information resources available for access by multiple users", "old_dept_obj_id": 82, "target": 60, "formula": "(Number of Information resources available for access by all staff/ Total Information resources planned to be available to users)*100", "current_value": 0},
            {"name": "Proportion of service charter KPIs attained", "old_dept_obj_id": 83, "target": 60, "formula": "(Number of Service Charter KPIs attained/Total Number of Service Charter KPIs)*100", "current_value": 0},
            {"name": "Percentage of IT systems that are available", "old_dept_obj_id": 83, "target": 99, "formula": "(Number of IT systems available/ Number of IT systems monitored)*100", "current_value": 0},
            {"name": "Tools and technology utilization score", "old_dept_obj_id": 84, "target": 80, "formula": "Enterprise Wide: Number of tools and technology used in execution of business processes/ Number of tools provisioned for execution of business processes", "current_value": 0},
            {"name": "Tools and technology utilization score", "old_dept_obj_id": 84, "target": 100, "formula": "Internal score: Number of tools and technology used in execution of division business processes/ Number of tools provisioned for execution of business processes", "current_value": 0},
            {"name": "Percentage of staff achieving 65% and above", "old_dept_obj_id": 85, "target": 70, "formula": "(Number of staff achieving 65% and above /Total Number of staff in the department)*100", "current_value": 0},
            {"name": "Percentage of Departmental targets achieved", "old_dept_obj_id": 86, "target": 80, "formula": "(Number of Targets achieved/Total Number of Departmental Targets)*100", "current_value": 0},
            {"name": "Frequency of update of UCC information", "old_dept_obj_id": 92, "target": 70, "formula": " Frequency of update of information=(Percentage of content dissemination plan [1] implemented)", "current_value": 0},
            {"name": "Budget Management Score (% of expenditure within budget)", "old_dept_obj_id": 95, "target": 90, "formula": "(Number of activities executed within budget/total number of budgeted activities)*100", "current_value": 0},
            {"name": "Corporate Performance Reporting score = (percentage of performance reports submitted on time)", "old_dept_obj_id": 96, "target": 80, "formula": "(Number of performance reports submitted on time/total number of expected performance reports)*100", "current_value": 0},
            {"name": "% of partner commitments met (Local and International)", "old_dept_obj_id": 97, "target": 75, "formula": "(Number of partner objectives met/total number of stakeholder/partner objectives) *100", "current_value": 0},
            {"name": "Corporate Affairs department charter score", "old_dept_obj_id": 98, "target": 70, "formula": "(Number of Corporate Affairs Charter targets achieved/total CA targets)*100", "current_value": 0},
            {"name": "CA productivity score (% of staff meeting performance targets)", "old_dept_obj_id": 99, "target": 80, "formula": "CA productivity score = (number of staff scoring above 65% in appraisals/Total number of CA department staff)", "current_value": 0},
            {"name": "Tools and Technology utilization score", "old_dept_obj_id": 100, "target": 50, "formula": "Average Tech Utilization score = (percentage  of CA staff using tech tools/Total number of identified tools)", "current_value": 0},
            {"name": "Technical accuracy of UCC content", "old_dept_obj_id": 92, "target": 80, "formula": "Technical accuracy:- Percentage of content adhering to QA standard ( approval by HoDs)", "current_value": 0},
            {"name": "Brand compliance score", "old_dept_obj_id": 93, "target": 80, "formula": "Percentage of identified branding initiatives implemented", "current_value": 0},
            {"name": "Corporate Affairs workplan execution rate", "old_dept_obj_id": 94, "target": 80, "formula": "(Number of CA implemented activities within schedule/total CA workplan activities)*100", "current_value": 0},
            {"name": "Percentage of country proposals presented", "old_dept_obj_id": 94, "target": 60, "formula": "Percentage of international events that have country proposals", "current_value": 0},
            {"name": "Percentage of Corporate Affairs (score card) targets met", "old_dept_obj_id": 94, "target": 80, "formula": "(Number of CA scorecard targets achieved/Total CA scorecard targets)*100", "current_value": 0},
            {"name": "Internal stakeholder engagement score", "old_dept_obj_id": 97, "target": 75, "formula": "Percentage of planned internal policy engagements undertaken", "current_value": 0},
            {"name": "Percentage of DIAC staff meeting intended performance goals", "old_dept_obj_id": 102, "target": 70, "formula": "Staff Productivity Score = (Number of Staff scoring above 70%/Total number of staff appraised)*100", "current_value": 0},
            {"name": "Percentage of planned frameworks developed", "old_dept_obj_id": 98, "target": 70, "formula": "(number of frameworks developed/number expected frameworks)*100", "current_value": 0},
            {"name": "Percentage increase in revenue", "old_dept_obj_id": 29, "target": 100, "formula": "Revenue Growth = 100*(Current FY Revenue - Previous FY Revenue)/Previous FY Revenue", "current_value": 0},
            {"name": "Percentage of scorecard targets achieved", "old_dept_obj_id": 63, "target": 80, "formula": "(Number of Scorecard targets Achieved/Total Number of Scorecard Targets)*100", "current_value": 0},
            {"name": "Proportion of Internal Audit  and risk staff trained as per the skills gap", "old_dept_obj_id": 104, "target": 70, "formula": "(Number of staff trained in FY 2022-2023/Total number of staff scheduled for training in the FY)*100", "current_value": 0},
            {"name": "Proportion of Internal Audit and risk staff attaining 65% performance appraisal score", "old_dept_obj_id": 104, "target": 80, "formula": "(Number of Internal Audit and risk staff attaining 65% performance appraisal score/Total Number of staff in the department in the FY 2022-23)*100", "current_value": 0},
            {"name": "Percentage of activities executed within budget", "old_dept_obj_id": 46, "target": 80, "formula": "Number of activities executed within budget/Total number of activities*100", "current_value": 0},
            {"name": "Frequency of update of UCC information", "old_dept_obj_id": 92, "target": 70, "formula": "Frequency of update of website content=(% adherence to website content management timelines[2])", "current_value": 0},
            {"name": "Percentage of risk reports submitted as per schedule", "old_dept_obj_id": 64, "target": 80, "formula": "(Number of risk reports submitted within timelines during the FY 2022-23/Total number of risk reports scheduled for the FY 2022-23)*100", "current_value": 0},
            {"name": "Percentage of departmental processes and policies reviewed", "old_dept_obj_id": 83, "target": 90, "formula": "(Number of departmental processes and policies reviewed/Total Number of departmental processes and policies)*100", "current_value": 0},
            {"name": "Percentage of applications processed in line with the department charter (resources & type approval)", "old_dept_obj_id": 75, "target": 82, "formula": "(Number of applications processed in line with service charter/Total number of license applications received)*100", "current_value": 0},
            {"name": "Percentage of updated contracts in the data base", "old_dept_obj_id": 9, "target": 70, "formula": "(Number of contracts updated/Total Number of contracts with pending issues)*100", "current_value": 0},
            {"name": "Percentage of insurance issues resolved", "old_dept_obj_id": 9, "target": 70, "formula": "(Number of Insurance claims addressed/Total number of insurance claims filed)*100", "current_value": 0},
            {"name": "Percentage of treaties, agreements and resolutions ratified adopted within the commission", "old_dept_obj_id": 17, "target": 50, "formula": "(Number of Legal and Regulatory obligations adopted within the commission/Total Number of International treaties, agreements and conventions)*100", "current_value": 0},
            {"name": "Percentage of Legal Department activities executed within budget", "old_dept_obj_id": 18, "target": 80, "formula": "(Number of Legal Department activities executed within budget/Total Number of Legal Department Activities Executed)*100", "current_value": 0},
            {"name": "Percentage of planned procurements completed", "old_dept_obj_id": 18, "target": 80, "formula": "(Number of planned procurements completed/Total Number of procurements planned)*100", "current_value": 0},
            {"name": "Percentage of identified risks in procurement with mitigation measures", "old_dept_obj_id": 21, "target": 70, "formula": "(Number of identified risks with mitigation measures/Total Number of identified risks)*100", "current_value": 0},
            {"name": "Proportion of DIAC staff trained as per the skills gap", "old_dept_obj_id": 102, "target": 100, "formula": "(Number of DIAC staff trained as per the skills gap/Total Number of DIAC staff)*100", "current_value": 0},
        ]

        kpis_created = 0
        kpis_skipped = 0
        # Map old department_measures.id to KPI objects for team objectives
        # This mapping is based on the order and names from the SQL
        old_measure_id_to_kpi = {}
        # Mapping old measure_id to KPI name (from department_measures SQL)
        # Used to map old measure_ids to KPIs for team objectives
        old_measure_id_to_name = {
            14: "Percentage of received stakeholder requests resolve",
            23: "Percentage of planned engagements undertaken (DPP, UPF, industry bodies, Solicitor General, MoJCA, Judiciary, ULS)",
            24: "Percentage of regulatory gaps identified with proposals",
            25: "Percentage of procurements within budget",
            26: "Percentage of procurements executed in time",
            27: "Percentage of operators notified on compliance and reporting processes within the month of May",
            28: "Percentage of departments engaged on compliance issues per quarter",
            29: "Percentage of departments-initiated operator compliance issues addressed",
            30: "Percentage of PPDA Audit issues addressed",
            31: "Percentage of internal Audit issues addressed",
            32: "Percentage of cases filed within schedule",
            33: "Percentage of licenses issued within statutory timelines",
            34: "Percentage of Procurements undertaken within set timelines (Percentage of service charter targets achieved",
            35: "Percentage of board documents developed and submitted on time",
            37: "Percentage of cases handled within statutory periods",
            38: "Percentage of opinions provided to internal clients within 7days",
            39: "Percentage of investigations concluded within set timelines",
            40: "Percentage of identified risks with workable mitigation measures in place",
            41: "Percentage of mitigation measures with updates",
            42: "Stakeholder satisfaction score",
            43: "Percentage of technical audit completed within three weeks",
            44: "Percentage of project monitoring activities completed as per schedule",
            45: "Percentage of projects initiated as per schedule/workplan",
            47: "Percentage of projects executed as per schedule",
            48: "Budget Absorption Rate",
            49: "Percentage of creditors below 30 days",
            52: "Percentage Expenditure aligned to Strategy",
            53: "Percentage Increase in Revenue",
            54: "Percentage of projects rolled over to the next year",
            55: "Percentage of identified audit recommendations implemented",
            56: "Percentage of identified Board/TMT recommendations implemented",
            57: "Percentage of correspondences completed as per the charter",
            59: "Percentage of Revenues Billed",
            60: "Percentage of Revenues Collected",
            61: "Percentage of Debtors below 90 days",
            62: "Employee satisfaction score",
            63: "Percentage of Creditors below 90 Days",
            64: "Percentage of staff outstanding accountable advances below 60 days",
            65: "Percentage of service requests successfully handled within 7 days",
            66: "Percentage of finance reports developed in line with the QA framework and submitted on agreed timelines",
            67: "Percentage of staff who met performance targets",
            68: "Budget absorption rate",
            70: "Timeliness of budget preparation",
            74: "Percentage of work plan activities implemented in time",
            76: "Percentage of identified HRA audit recommendations implemented",
            77: "Percentage of Departmental targets achieved",
            79: "Talent retention rate (High performing staff)",
            81: "Percentage of quarterly reports submitted to the audit Committee within the schedule to the Committee meeting",
            82: "Percentage of reports on Board actions presented as per schedule",
            83: "Percentage of HRA services conducted online",
            84: "Percentage of consumer related complaints concluded within the set timelines (2 weeks)",
            85: "Percentage of content related complaints concluded within 20 working days",
            88: "Percentage of market reports ready for publication in the month following the respective quarter",
            89: "Percentage of consumer advisories issued",
            90: "Percentage of quarterly local quota assessment reports ready for publication in the month following the respective quarter",
            92: "Percentage of cost centers in which a saving has been achieved versus budget •Publications •Events •Outreach  •Consultancies •Field work •Tools & equipment",
            93: "Percentage of reports on TMT actions presented as per schedule",
            94: "Proportion of internal stakeholder engagements accomplished as per schedule",
            95: "Proportion of expenditure requests for the department initiated on time",
            96: "Percentage of contracts implemented within the contractual period",
            97: "Proportion of departmental outputs accomplished as per schedule",
            98: "Proportion of audits accomplished within set quality standards",
            99: "Proportion of investigations achieved per schedule",
            100: "Proportion of quarterly action follow up reports submitted to the audit Committee as per schedule to the Committee meeting",
            101: "Proportion of scheduled departmental outputs accomplished",
            102: "Proportion of scheduled sensitizations/engagements conducted with Risk champions",
            103: "Percentage of identified regulatory frameworks/standards completed •Content distribution and exhibition •Roll over of unutilized data •Significant market power",
            104: "Percentage of licensees with compliance status (based on report submitted & audits/inspections conducted) of not more than six months old  •Competition obligations •Postal  •Consumer",
            105: "Percentage of technical evaluations for licenses completed within the 14 days",
            106: "Percentage of departmental workplan activities implemented as scheduled",
            107: "Average Availability Score •Criteria for availability/functionality for each tool/system to be set •Quarterly assessments for each tool against the respective criteria to determine tool availability",
            108: "Proportion of sensitizations/engagements conducted with scheduled staff/departments",
            109: "Proportion of sensitizations/engagements conducted with scheduled staff/departments",
            110: "Percentage of scheduled business units with updated compliance registers as per schedule",
            111: "Percentage of planned QoS publications/reports prepared (Three publications)",
            112: "Percentage of reported cases of interference to telecom, FM radio & TV operations resolved",
            113: "Proportion of assignments accomplished using the audit tools",
            114: "Proportion of Internal audit & risk staff trained as per the skills gap",
            115: "Proportion of Internal audit & risk staff attaining the 65% performance appraisal score",
            116: "Percentage of assigned resources in use (Spectrum, Numbering and Electronic Addressing/LCNs)",
            119: "Percentage of technical evaluations for licenses completed in line with the department charter",
            120: "Percentage of operators with information on compliance status not more than six months old",
            121: "Percentage of applications processed in line with the department charter",
            122: "Percentage of workplan activities implemented as scheduled",
            123: "Average Availability Score",
            126: "ICT/R user Satisfaction score",
            127: "Proportion of digital initiatives implemented as per the agreed project plans/road maps",
            128: "Corporate cyber security readiness level",
            129: "Proportion of Budget spent within cost",
            130: "Budget spend cost savings",
            131: "Proportion of risks mitigation measures implemented per function within the FY",
            132: "Percentage of approved research reports available",
            133: "Proportion of information resources available for access by multiple users",
            134: "Proportion of service charter KPIs attained",
            135: "Percentage of IT systems that are available",
            136: "Tools and technology utilization score",
            138: "Percentage of staff achieving 65% and above",
            139: "Percentage of Departmental targets achieved",
            150: "Frequency of update of UCC information",
            152: "UCC work plan execution rate",
            156: "Corporate Affairs department charter score",
            157: "CA productivity score (% of staff meeting performance targets)",
            161: "Technical accuracy of UCC content",
            162: "Brand compliance score",
            165: "Percentage of country proposals presented",
            166: "Percentage of Corporate Affairs (score card) targets met",
            167: "Internal stakeholder engagement score",
            168: "Percentage of DIAC staff meeting intended performance goals",
            169: "Percentage of planned frameworks developed",
            174: "Number of timely implemented activities in the workplan",
        }

        for kpi_data in dept_kpis_data:
            # Get department objective using old ID mapping
            dept_objective = old_dept_obj_id_to_dept_obj.get(kpi_data["old_dept_obj_id"])
            if not dept_objective:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping KPI '{kpi_data['name']}' - department objective ID {kpi_data['old_dept_obj_id']} not found")
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
            
            # Map old measure_id to KPI for team objectives
            # Find the measure_id by matching KPI name (case-insensitive, ignore trailing periods)
            for old_measure_id, measure_name in old_measure_id_to_name.items():
                # Normalize names for comparison (remove trailing periods/whitespace)
                kpi_name_normalized = kpi.name.strip().rstrip('.')
                measure_name_normalized = measure_name.strip().rstrip('.')
                if kpi_name_normalized.lower() == measure_name_normalized.lower():
                    old_measure_id_to_kpi[old_measure_id] = kpi
                    break

        self.stdout.write(
            self.style.SUCCESS(f"✓ Created {kpis_created} department KPIs")
        )
        if kpis_skipped > 0:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Skipped {kpis_skipped} department KPIs")
            )

        # 6. Create Team Objectives
        self.stdout.write("Creating Team Objectives...")
        # Map old team IDs to team names/objects
        team_name_map = {team.name: team for team in Team.objects.filter(department__organization=organization)}
        
        # Uncommented team_objectives (status=1) from SQL lines 307-326
        team_objectives_data = [
            {"title": "Improve the completeness and timeliness of litigation and prosecution process flows and Legal Advisory services", "old_team_id": 6, "old_measure_id": 14, "status": 1},
            {"title": "Improve on the response time towards stakeholder requests", "old_team_id": 7, "old_measure_id": 14, "status": 1},
            {"title": "Increase engagements with Internal and External Stakeholders", "old_team_id": 7, "old_measure_id": 14, "status": 1},
            {"title": "Improve on management and disbursement of legal documents", "old_team_id": 5, "old_measure_id": 14, "status": 1},
            {"title": "Improve Timeliness and quality of information submitted to the Ministry", "old_team_id": 5, "old_measure_id": 14, "status": 1},
            {"title": "Improve the collaboration with the Directorate of Public Prosecution, Courts of Law and other communications sector stakeholders", "old_team_id": 6, "old_measure_id": 23, "status": 1},
            {"title": "Enhance compliance of UCC with provisions of signed international agreements, treaties and conventions", "old_team_id": 8, "old_measure_id": 23, "status": 1},
            {"title": "Reduce identified regulatory gaps by 80%", "old_team_id": 7, "old_measure_id": 23, "status": 1},
            {"title": "Ensure value for money is obtained in the execution of the procurement process", "old_team_id": 9, "old_measure_id": 23, "status": 1},
            {"title": "Improve compliance of internal and external stakeholder", "old_team_id": 8, "old_measure_id": 27, "status": 1},
            {"title": "Improve compliance of internal and external stakeholder", "old_team_id": 8, "old_measure_id": 28, "status": 1},
            {"title": "Improve enforcement management process", "old_team_id": 8, "old_measure_id": 29, "status": 1},
            {"title": "Ensure compliance to established rules and procedures for procurement", "old_team_id": 9, "old_measure_id": 30, "status": 1},
            {"title": "Ensure compliance to established rules and procedures for procurement", "old_team_id": 9, "old_measure_id": 31, "status": 1},
            {"title": "Improve the completeness and timeliness of litigation and prosecution process flows and Legal Advisory services", "old_team_id": 6, "old_measure_id": 32, "status": 1},
            {"title": "Reduce turn-around times for processing of license applications", "old_team_id": 7, "old_measure_id": 33, "status": 1},
            {"title": "Increase adoption and usability of the E-Licensing portal", "old_team_id": 7, "old_measure_id": 33, "status": 1},
            {"title": "Improve procurement cycle activity management", "old_team_id": 9, "old_measure_id": 34, "status": 1},
            {"title": "Improve Board Efficiency", "old_team_id": 5, "old_measure_id": 35, "status": 1},
            {"title": "Improve Efficiency of Board Committees", "old_team_id": 5, "old_measure_id": 35, "status": 1},
            # Remaining uncommented team objectives (status=1)
            {"title": "Improve the completeness and timeliness of litigation and prosecution process flows and Legal Advisory services", "old_team_id": 6, "old_measure_id": 37, "status": 1},
            {"title": "Improve the completeness and timeliness of litigation and prosecution process flows and Legal Advisory services", "old_team_id": 6, "old_measure_id": 38, "status": 1},
            {"title": "Improve Legal Advisory Services", "old_team_id": 7, "old_measure_id": 38, "status": 1},
            {"title": "Improve Legal Process Efficiency", "old_team_id": 6, "old_measure_id": 39, "status": 1},
            {"title": "Improve Legal Process Efficiency", "old_team_id": 8, "old_measure_id": 39, "status": 1},
            {"title": "Improve legal compliance risk management", "old_team_id": 8, "old_measure_id": 40, "status": 1},
            {"title": "Minimize Potential Litigation against the Commission", "old_team_id": 6, "old_measure_id": 40, "status": 1},
            {"title": "Reduce Legal Risk identified within the licensing process", "old_team_id": 7, "old_measure_id": 40, "status": 1},
            {"title": "Minimize risks that are likely to affect the efficient delivery of the procurement function", "old_team_id": 9, "old_measure_id": 40, "status": 1},
            {"title": "Reduce Legal Risk identified within the licensing process", "old_team_id": 7, "old_measure_id": 41, "status": 1},
            {"title": "Improve timeliness and completeness of information on the Commission's obligations as per Contract and MOUs in place", "old_team_id": 8, "old_measure_id": 41, "status": 1},
            {"title": "Improve Administration budget absorption", "old_team_id": 11, "old_measure_id": 68, "status": 1},
            {"title": "Decrease stakeholder complaints", "old_team_id": 12, "old_measure_id": 49, "status": 1},
            {"title": "Improve expenditure alignement to budget", "old_team_id": 12, "old_measure_id": 48, "status": 1},
            {"title": "Improve on expenditure alignement to Strategy", "old_team_id": 12, "old_measure_id": 52, "status": 1},
            {"title": "Strengthen revenue growth", "old_team_id": 13, "old_measure_id": 53, "status": 1},
            {"title": "Enhance Planning and Coordination of the audit exercise/processes", "old_team_id": 14, "old_measure_id": 55, "status": 1},
            {"title": "Enhance Planning and Coordination of the audit exercise/processes", "old_team_id": 14, "old_measure_id": 56, "status": 1},
            {"title": "Increase employee productivity", "old_team_id": 10, "old_measure_id": 67, "status": 1},
            {"title": "Improve billings and related process flows", "old_team_id": 13, "old_measure_id": 59, "status": 1},
            {"title": "Improve Employee satisfaction score", "old_team_id": 10, "old_measure_id": 62, "status": 1},
            {"title": "Enhance collection process", "old_team_id": 13, "old_measure_id": 60, "status": 1},
            {"title": "Reduce debt above 90 days", "old_team_id": 13, "old_measure_id": 61, "status": 1},
            {"title": "Reduce response time to Administration service requests to a maximum of 5 days", "old_team_id": 11, "old_measure_id": 65, "status": 1},
            {"title": "Improve department efficiency", "old_team_id": 10, "old_measure_id": 74, "status": 1},
            {"title": "Improve reporting on vehicles/fleet", "old_team_id": 11, "old_measure_id": 74, "status": 1},
            {"title": "Improve reporting on services provided by administration", "old_team_id": 11, "old_measure_id": 74, "status": 1},
            {"title": "Strengthen Financial Reporting", "old_team_id": 14, "old_measure_id": 66, "status": 1},
            {"title": "Improve timelines of budget preparation and reporting to PFMA", "old_team_id": 14, "old_measure_id": 70, "status": 1},
            {"title": "Improve service management", "old_team_id": 11, "old_measure_id": 74, "status": 1},
            {"title": "Improve the number of activities in the administration work plan that are implemented on time", "old_team_id": 11, "old_measure_id": 74, "status": 1},
            {"title": "Improve creditors pay out time", "old_team_id": 12, "old_measure_id": 63, "status": 1},
            {"title": "Reduce staff debtors", "old_team_id": 12, "old_measure_id": 64, "status": 1},
            {"title": "Percentage of identified HRA audit recommendations implemented", "old_team_id": 10, "old_measure_id": 76, "status": 1},
            {"title": "Enhance Business Success of Litigation and Prosecution Unit", "old_team_id": 6, "old_measure_id": 77, "status": 1},
            {"title": "Enhance Business Success of Legal Affairs Unit", "old_team_id": 7, "old_measure_id": 77, "status": 1},
            {"title": "Enhance Business Success of Compliance and Enforcement Unit", "old_team_id": 8, "old_measure_id": 77, "status": 1},
            {"title": "Enhance Business Success of Procurement Unit", "old_team_id": 9, "old_measure_id": 77, "status": 1},
            {"title": "Increase talent retention", "old_team_id": 10, "old_measure_id": 79, "status": 1},
            {"title": "Increase talent retention", "old_team_id": 10, "old_measure_id": 79, "status": 1},
            {"title": "Increase talent retention", "old_team_id": 10, "old_measure_id": 79, "status": 1},
            {"title": "Improve timely review of governance systems", "old_team_id": 18, "old_measure_id": 81, "status": 1},
            {"title": "Promote usage of HRA online services", "old_team_id": 10, "old_measure_id": 83, "status": 1},
            {"title": "Reduce time taken to communicate risk updates/risk assessments", "old_team_id": 17, "old_measure_id": 82, "status": 1},
            {"title": "Improve timely coverage of Board and Management decisions followed up", "old_team_id": 17, "old_measure_id": 93, "status": 1},
            {"title": "Increase coverage of audit client sensitization activities", "old_team_id": 18, "old_measure_id": 94, "status": 1},
            {"title": "Increase utilization of allocated financial resources within market assessed values", "old_team_id": 18, "old_measure_id": 95, "status": 1},
            {"title": "Increase utilization of allocated financial resources within market assessed values", "old_team_id": 17, "old_measure_id": 95, "status": 1},
            {"title": "Increase utilization of allocated financial resources within market assessed values", "old_team_id": 18, "old_measure_id": 96, "status": 1},
            {"title": "Reduce time taken to complete audit assignments", "old_team_id": 18, "old_measure_id": 97, "status": 1},
            {"title": "Improve quality of audit reports to Management and the Audit Committee", "old_team_id": 18, "old_measure_id": 98, "status": 1},
            {"title": "Increase coverage of investigation requests", "old_team_id": 18, "old_measure_id": 99, "status": 1},
            {"title": "Increase coverage of audit follow up reports", "old_team_id": 18, "old_measure_id": 100, "status": 1},
            {"title": "Enhance team business process", "old_team_id": 18, "old_measure_id": 101, "status": 1},
            {"title": "Enhance team business process", "old_team_id": 17, "old_measure_id": 101, "status": 1},
            {"title": "Increase coverage of sensitization on risk management", "old_team_id": 17, "old_measure_id": 102, "status": 1},
            {"title": "Increase coverage of sensitization on risk management", "old_team_id": 17, "old_measure_id": 108, "status": 1},
            {"title": "Improve quality of risk coordination reports to Management and the Audit Committee", "old_team_id": 17, "old_measure_id": 109, "status": 1},
            {"title": "Increase coverage of business units with updated risk information", "old_team_id": 18, "old_measure_id": 110, "status": 1},
            {"title": "Increase coverage of business units with updated risk information", "old_team_id": 17, "old_measure_id": 110, "status": 1},
            {"title": "Improve quality of compliance audit reports to Management and the Audit Committee", "old_team_id": 17, "old_measure_id": 110, "status": 1},
            {"title": "Improve timeliness in conducting the QoS assessment exercises", "old_team_id": 20, "old_measure_id": 111, "status": 1},
            {"title": "Increase the audit tasks completed using the audit tools & technology", "old_team_id": 17, "old_measure_id": 113, "status": 1},
            {"title": "Increase the audit tasks completed using the audit tools & technology", "old_team_id": 18, "old_measure_id": 113, "status": 1},
            {"title": "Improve skills, knowledge and abilities of Assurance team", "old_team_id": 18, "old_measure_id": 114, "status": 1},
            {"title": "Improve skills, knowledge and abilities of Risk and compliance team", "old_team_id": 17, "old_measure_id": 114, "status": 1},
            {"title": "Improve skills, knowledge and abilities of Assurance team", "old_team_id": 18, "old_measure_id": 115, "status": 1},
            {"title": "Improve skills, knowledge and abilities of Assurance team", "old_team_id": 18, "old_measure_id": 115, "status": 1},
            {"title": "Improve skills, knowledge and abilities of Risk and compliance team", "old_team_id": 17, "old_measure_id": 115, "status": 1},
            {"title": "Improve timeliness of investigating interference (Access, Broadcasting, and Land Mobile)", "old_team_id": 21, "old_measure_id": 112, "status": 1},
            {"title": "Improve the frequency/regularity of reporting on radio frequency resource utilization from annual to quarterly with the view to timely identify and report on unauthorized operations", "old_team_id": 21, "old_measure_id": 116, "status": 1},
            {"title": "Improve utilization of Communication Resources (Numbering resources)", "old_team_id": 20, "old_measure_id": 116, "status": 1},
            {"title": "Improve the timeliness of SMD Business Processes, activities and assessment decisions", "old_team_id": 20, "old_measure_id": 119, "status": 1},
            {"title": "Improve the timeliness of SMD BUSINESS processes", "old_team_id": 21, "old_measure_id": 120, "status": 1},
            {"title": "Improve the timeliness of SMD BUSINESS processes", "old_team_id": 21, "old_measure_id": 121, "status": 1},
            {"title": "Improve the timeliness of SMD BUSINESS processes", "old_team_id": 21, "old_measure_id": 122, "status": 1},
            {"title": "Improve utilization of smd technical tools", "old_team_id": 20, "old_measure_id": 123, "status": 1},
            {"title": "Promote use of communication services", "old_team_id": 23, "old_measure_id": 42, "status": 1},
            {"title": "Improve UCUSAF operational efficiency", "old_team_id": 23, "old_measure_id": 43, "status": 1},
            {"title": "Increase project monitoring turnaround", "old_team_id": 23, "old_measure_id": 44, "status": 1},
            {"title": "Improve project conceptualization", "old_team_id": 23, "old_measure_id": 45, "status": 1},
            {"title": "Improve contract management", "old_team_id": 23, "old_measure_id": 47, "status": 1},
            {"title": "Decrease Number of Rolled Over Projects", "old_team_id": 23, "old_measure_id": 54, "status": 1},
            {"title": "Strengthen stakeholder relationships", "old_team_id": 23, "old_measure_id": 57, "status": 1},
            {"title": "Improve IT&S Customer Satisfaction", "old_team_id": 24, "old_measure_id": 126, "status": 1},
            {"title": "Improve IT&S Customer Satisfaction", "old_team_id": 25, "old_measure_id": 126, "status": 1},
            {"title": "Improve IT&S Customer Satisfaction", "old_team_id": 26, "old_measure_id": 126, "status": 1},
            {"title": "Improve quality of Information systems services", "old_team_id": 24, "old_measure_id": 126, "status": 1},
            {"title": "Improve quality of Information systems services", "old_team_id": 24, "old_measure_id": 126, "status": 1},
            {"title": "Automate Business Processes", "old_team_id": 24, "old_measure_id": 127, "status": 1},
            {"title": "Build cyber security capacity and capabilities in the sector and the Commission", "old_team_id": 26, "old_measure_id": 128, "status": 1},
            {"title": "Build cyber security capacity and capabilities in the sector and the Commission", "old_team_id": 26, "old_measure_id": 128, "status": 1},
            {"title": "Optimize Resources", "old_team_id": 24, "old_measure_id": 129, "status": 1},
            {"title": "Optimize Resources", "old_team_id": 25, "old_measure_id": 129, "status": 1},
            {"title": "Optimize Resources", "old_team_id": 26, "old_measure_id": 129, "status": 1},
            {"title": "Optimize Resources", "old_team_id": 27, "old_measure_id": 129, "status": 1},
            {"title": "Improve budget cost savings", "old_team_id": 24, "old_measure_id": 130, "status": 1},
            {"title": "Improve budget cost savings", "old_team_id": 25, "old_measure_id": 130, "status": 1},
            {"title": "Improve budget cost savings", "old_team_id": 26, "old_measure_id": 130, "status": 1},
            {"title": "Improve budget cost savings", "old_team_id": 27, "old_measure_id": 130, "status": 1},
            {"title": "Improve Information services risk management", "old_team_id": 25, "old_measure_id": 131, "status": 1},
            {"title": "Improve project planning and contract management", "old_team_id": 27, "old_measure_id": 131, "status": 1},
            {"title": "Improve R&SD risk management", "old_team_id": 27, "old_measure_id": 131, "status": 1},
            {"title": "Improve IT risk management", "old_team_id": 24, "old_measure_id": 131, "status": 1},
            {"title": "Improve CERT risk management", "old_team_id": 26, "old_measure_id": 131, "status": 1},
            {"title": "Enhance the utilization of research information", "old_team_id": 27, "old_measure_id": 132, "status": 1},
            {"title": "Enhance the utilization of research information", "old_team_id": 27, "old_measure_id": 133, "status": 1},
            {"title": "Improve access to knowledge", "old_team_id": 25, "old_measure_id": 133, "status": 1},
            {"title": "Improve performance on Team Service Charter KPIs", "old_team_id": 24, "old_measure_id": 134, "status": 1},
            {"title": "Improve performance on Team Service Charter KPIs", "old_team_id": 25, "old_measure_id": 134, "status": 1},
            {"title": "Improve quality of Information systems services", "old_team_id": 26, "old_measure_id": 134, "status": 1},
            {"title": "Improve performance on Team Service Charter KPIs", "old_team_id": 27, "old_measure_id": 134, "status": 1},
            {"title": "Increase IT systems availability", "old_team_id": 24, "old_measure_id": 135, "status": 1},
            {"title": "Review processes and policies in the Division", "old_team_id": 26, "old_measure_id": 135, "status": 1},
            {"title": "Improve ISU Internal Processes", "old_team_id": 25, "old_measure_id": 135, "status": 1},
            {"title": "Improve turnaround time for approval of R&SD Processes", "old_team_id": 27, "old_measure_id": 135, "status": 1},
            {"title": "Improve Resource utilization", "old_team_id": 24, "old_measure_id": 136, "status": 1},
            {"title": "Increment in Usage of Resource Centre", "old_team_id": 25, "old_measure_id": 136, "status": 1},
            {"title": "Enhance IT Staff Performance", "old_team_id": 24, "old_measure_id": 138, "status": 1},
            {"title": "Enhance ISU Staff Performance", "old_team_id": 25, "old_measure_id": 138, "status": 1},
            {"title": "Enhance CERT Staff Performance", "old_team_id": 26, "old_measure_id": 138, "status": 1},
            {"title": "Enhance Research Staff Performance", "old_team_id": 27, "old_measure_id": 138, "status": 1},
            {"title": "Enhance Business Success of IT Unit", "old_team_id": 24, "old_measure_id": 139, "status": 1},
            {"title": "Enhance Business Success of ISU Unit", "old_team_id": 25, "old_measure_id": 139, "status": 1},
            {"title": "Enhance Business Success of CERT Unit", "old_team_id": 26, "old_measure_id": 139, "status": 1},
            {"title": "Enhance Business Success of Research Unit", "old_team_id": 27, "old_measure_id": 139, "status": 1},
            {"title": "Improve stakeholder awareness", "old_team_id": 1, "old_measure_id": 150, "status": 1},
            {"title": "Improve timeliness of performance information to support management decision making", "old_team_id": 1, "old_measure_id": 161, "status": 1},
            {"title": "Strengthen the coordination of Regional office stakeholder engagements", "old_team_id": 4, "old_measure_id": 161, "status": 1},
            {"title": "Enhance visibility and image of UCC brand", "old_team_id": 1, "old_measure_id": 162, "status": 1},
            {"title": "Enhance implementation of SBP workplan", "old_team_id": 2, "old_measure_id": 152, "status": 1},
            {"title": "Improve timely conclusion of complaints (Consumer complaints)", "old_team_id": 32, "old_measure_id": 84, "status": 1},
            {"title": "Enhance implementation of PIR workplan", "old_team_id": 1, "old_measure_id": 152, "status": 1},
            {"title": "Improve the turnaround time for review of licensee/industry disputes and investigations within 45 working days", "old_team_id": 31, "old_measure_id": 84, "status": 1},
            {"title": "Improve timely conclusion of Content and licensee complaints", "old_team_id": 30, "old_measure_id": 85, "status": 1},
            {"title": "Improve the timely availability of information to stakeholders", "old_team_id": 30, "old_measure_id": 88, "status": 1},
            {"title": "Improve the timely availability of information to stakeholders.(Report and Consumer advisories)", "old_team_id": 32, "old_measure_id": 89, "status": 1},
            {"title": "Increase Uganda's contribution to the development of international standards", "old_team_id": 1, "old_measure_id": 165, "status": 1},
            {"title": "Strengthen achievement of strategy and Business Planning Targets", "old_team_id": 2, "old_measure_id": 166, "status": 1},
            {"title": "Improve the timeliness of competition and market information", "old_team_id": 31, "old_measure_id": 90, "status": 1},
            {"title": "Enhance RO business success", "old_team_id": 4, "old_measure_id": 166, "status": 1},
            {"title": "Reduce cost of doing business/operation", "old_team_id": 30, "old_measure_id": 92, "status": 1},
            {"title": "Reduce cost of doing business/operation", "old_team_id": 32, "old_measure_id": 92, "status": 1},
            {"title": "Strengthen the relevancy of industry standards ( develop, review, register and apply frameworks, guidelines, standards and rules)", "old_team_id": 30, "old_measure_id": 103, "status": 1},
            {"title": "Strengthen the relevance of industry/tools standards/guidelines and frameworks within the division", "old_team_id": 31, "old_measure_id": 103, "status": 1},
            {"title": "Improve responsiveness of the regulatory frameworks and standards", "old_team_id": 32, "old_measure_id": 103, "status": 1},
            {"title": "Strengthen Compliance monitoring •Improve the quality of compliance information on licensed operators •Increase awareness of compliance standards", "old_team_id": 30, "old_measure_id": 104, "status": 1},
            {"title": "Strengthen Compliance monitoring •Improve the quality of compliance information on licensed operators •Increase awareness of compliance standards", "old_team_id": 31, "old_measure_id": 104, "status": 1},
            {"title": "Strengthen Compliance monitoring", "old_team_id": 32, "old_measure_id": 104, "status": 1},
            {"title": "Strengthen Compliance monitoring", "old_team_id": 30, "old_measure_id": 105, "status": 1},
            {"title": "Strengthen Compliance monitoring", "old_team_id": 31, "old_measure_id": 105, "status": 1},
            {"title": "Strengthen Compliance monitoring", "old_team_id": 30, "old_measure_id": 106, "status": 1},
            {"title": "Strengthen Compliance monitoring", "old_team_id": 31, "old_measure_id": 106, "status": 1},
            {"title": "Strengthen Compliance monitoring", "old_team_id": 32, "old_measure_id": 106, "status": 1},
            {"title": "Improve Tools & Technology capability for better work environment & processes (Digital Logger)", "old_team_id": 30, "old_measure_id": 107, "status": 1},
            {"title": "Enhance online data collection portal to include Telecom, Postal and Multimedia subsector. (Filemaker and Kompare site/ portal)", "old_team_id": 31, "old_measure_id": 107, "status": 1},
            {"title": "Improve Tools & Technology capability for better work environment & processes (Digital Logger)", "old_team_id": 32, "old_measure_id": 107, "status": 1},
            {"title": "Enhance coordination of RO internal stakeholders", "old_team_id": 4, "old_measure_id": 167, "status": 1},
            {"title": "Increase PIR systems and process efficiency", "old_team_id": 1, "old_measure_id": 156, "status": 1},
            {"title": "Improve Skills, Knowledge & Abilities", "old_team_id": 30, "old_measure_id": 168, "status": 1},
            {"title": "Improve Skills, Knowledge & Abilities", "old_team_id": 31, "old_measure_id": 168, "status": 1},
            {"title": "Improve documentation of Strategy and Business planning frameworks", "old_team_id": 2, "old_measure_id": 169, "status": 1},
            {"title": "Improve documentation of PIR frameworks", "old_team_id": 1, "old_measure_id": 169, "status": 1},
            {"title": "Improve productivity of Regional office staff", "old_team_id": 4, "old_measure_id": 157, "status": 1},
            {"title": "Improve Skills, Knowledge & Abilities", "old_team_id": 32, "old_measure_id": 168, "status": 1},
            {"title": "Improve Employee Satisfaction Score", "old_team_id": 33, "old_measure_id": 62, "status": 1},
            {"title": "Increase Employee Productivity", "old_team_id": 33, "old_measure_id": 67, "status": 1},
            {"title": "Improve Department Efficiency", "old_team_id": 33, "old_measure_id": 174, "status": 1},
        ]
        
        # Map old team IDs to team names (from teams SQL)
        old_team_id_to_name = {
            1: "PIR",
            2: "SBP",
            4: "Regional Offices",
            5: "Board Affairs",
            6: "Litigation Unit",
            7: "Legal Affairs",
            8: "Compliance and Enforcement",
            9: "Procurement",
            10: "Human Resources",
            11: "Administration",
            12: "Expenditure Unit",
            13: "Revenue Unit",
            14: "Management Accounts",
            17: "Risk and Compliance",
            18: "Assurance",
            20: "Communications Infrastructure Services",
            21: "Spectrum Management Division",
            23: "UCUSAF",
            24: "IT&S",
            25: "ISU",
            26: "CERT",
            27: "R&SD",
            30: "Multimedia and Content",
            31: "Economic Regulation and Competition",
            32: "Consumer Affairs",
            33: "Human Resource",
        }
        
        team_objectives_created = 0
        team_objectives_skipped = 0
        # Map old team_objective_id to new TeamObjective objects
        # Build this mapping as we create team objectives
        old_team_obj_id_to_team_obj = {}
        # Old team objective IDs in SQL (in order as they appear in team_objectives_data)
        # First 20: 13, 14, 15, 16, 17, 18, (19 skipped), 20, 21, 22, 23, 24, 25, 26, (27 skipped), 28, (29 skipped), 30, 31, 32, 33, 34
        # Then continuing: 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 62, 63, 64, 65, 67, 69, 70, 71, 72, 73, 75, 78, 79, 80, 81, 82, 83, 84, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 117, 118, 119, 121, 122, 127, 129, 130, 131, 132, 133, 134, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 205, 208, 209, 210, 211, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 265, 266, 267, 270, 271, 272, 273, 275, 276, 277, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289
        old_team_obj_ids_ordered = [13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 28, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 62, 63, 64, 65, 67, 69, 70, 71, 72, 73, 75, 78, 79, 80, 81, 82, 83, 84, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 117, 118, 119, 121, 122, 127, 129, 130, 131, 132, 133, 134, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 205, 208, 209, 210, 211, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 265, 266, 267, 270, 271, 272, 273, 275, 276, 277, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289]
        
        for idx, team_obj_data in enumerate(team_objectives_data):
            # Get team
            team_name = old_team_id_to_name.get(team_obj_data["old_team_id"])
            if not team_name:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping team objective '{team_obj_data['title']}' - team ID {team_obj_data['old_team_id']} not found")
                )
                team_objectives_skipped += 1
                continue
            
            team = team_name_map.get(team_name)
            if not team:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping team objective '{team_obj_data['title']}' - team '{team_name}' not found")
                )
                team_objectives_skipped += 1
                continue
            
            # Get KPI using old measure_id, then get its department_objective
            kpi = old_measure_id_to_kpi.get(team_obj_data["old_measure_id"])
            if not kpi:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping team objective '{team_obj_data['title']}' - measure ID {team_obj_data['old_measure_id']} (KPI) not found")
                )
                team_objectives_skipped += 1
                continue
            
            if not kpi.department_objective_id:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping team objective '{team_obj_data['title']}' - KPI '{kpi.name}' has no department_objective")
                )
                team_objectives_skipped += 1
                continue
            
            dept_objective = kpi.department_objective
            
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
                    self.stdout.write(f"  ✓ Updated team objective: {team_obj_data['title']} ({team_name})")
            else:
                team_objectives_created += 1
                self.stdout.write(f"  ✓ Created team objective: {team_obj_data['title']} ({team_name})")
            
            # Map old team_objective_id to new TeamObjective object
            if idx < len(old_team_obj_ids_ordered):
                old_team_obj_id_to_team_obj[old_team_obj_ids_ordered[idx]] = team_objective
        
        self.stdout.write(
            self.style.SUCCESS(f"✓ Created {team_objectives_created} team objectives")
        )
        if team_objectives_skipped > 0:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Skipped {team_objectives_skipped} team objectives")
            )

        # Map old team_objective_id to new TeamObjective objects
        # This mapping is based on the order in team_objectives_data and the SQL IDs
        old_team_obj_id_to_team_obj = {}
        team_objectives_list = list(TeamObjective.objects.filter(team__department__organization=organization).order_by('id'))
        # Map old team objective IDs to new TeamObjective objects
        # SQL team_objective IDs start from 13, 14, 15, etc. (first 20 uncommented ones)
        old_team_obj_ids_start = 13
        for idx, team_obj in enumerate(team_objectives_list[:20]):
            old_team_obj_id_to_team_obj[old_team_obj_ids_start + idx] = team_obj
        
        # For remaining team objectives, we need to map based on the order they appear in team_objectives_data
        # The SQL IDs continue from 20 onwards: 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 62, 63, 64, 65, 67, 69, 70, 71, 72, 73, 75, 78, 79, 80, 81, 82, 83, 84, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 117, 118, 119, 121, 122, 127, 129, 130, 131, 132, 133, 134, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 205, 208, 209, 210, 211, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 265, 266, 267, 270, 271, 272, 273, 275, 276, 277, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289
        remaining_old_team_obj_ids = [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 62, 63, 64, 65, 67, 69, 70, 71, 72, 73, 75, 78, 79, 80, 81, 82, 83, 84, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 117, 118, 119, 121, 122, 127, 129, 130, 131, 132, 133, 134, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 205, 208, 209, 210, 211, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 265, 266, 267, 270, 271, 272, 273, 275, 276, 277, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289]
        for idx, old_id in enumerate(remaining_old_team_obj_ids):
            if idx + 20 < len(team_objectives_list):
                old_team_obj_id_to_team_obj[old_id] = team_objectives_list[idx + 20]

                # 7. Create Team KPIs
        self.stdout.write("Creating Team KPIs...")
        # Read team_measures data from SQL (lines 576+)
        # Format: (id, measure, target, formula, score, team_objective_id, reporting_period_id, created_at, updated_at, status)
        # Only including uncommented entries with status=1
        team_kpis_data = [
            {"old_id": 21, "name": "Percentage of stakeholder querries addressed within 7 working days", "target": 70, "formula": "(Number of stakeholder querries addressed within 7 working days/Total Number of stakeholder querries addressed received)*100", "score": 55, "old_team_obj_id": 13, "status": 1},
            {"old_id": 22, "name": "%ge of received stakeholder requests resolved", "target": 85, "formula": "(Number of stakeholder requests addressed within 7 days/Total Number of External stakeholder requests received)*100", "score": 100, "old_team_obj_id": 14, "status": 1},
            {"old_id": 23, "name": "Percentage of stakeholder engagements undertaken", "target": 100, "formula": "(Number of stakeholder engagements undertaken/Total Number of engagements planned)*100", "score": 100, "old_team_obj_id": 15, "status": 1},
            {"old_id": 26, "name": "Percentage of documents received and dispatched within a day for commissions secretary signature", "target": 85, "formula": "(Number of documents received and dispatched within a day for commissions secretary signature/Total number of documents received)*100", "score": 61, "old_team_obj_id": 16, "status": 1},
            {"old_id": 27, "name": "Percentage of legal documents sealed", "target": 85, "formula": "(Number of legal documents sealed/Total Number of documents received)*100", "score": 20, "old_team_obj_id": 16, "status": 1},
            {"old_id": 28, "name": "Percentage of licensed operators updated in the database", "target": 85, "formula": "(Number of licensed operators updated in the database/Total Number of operators Licensed)*100", "score": 90, "old_team_obj_id": 16, "status": 1},
            {"old_id": 29, "name": "Percentage of minister reports submitted in set timelines", "target": 85, "formula": "(Number of Quarterly reports submitted to the minister by 6th day of the month after the quarter/Total Number of reports)*100", "score": 0, "old_team_obj_id": 17, "status": 1},
            {"old_id": 30, "name": "Percentage of planned meetings and engagement implemented", "target": 80, "formula": "(Number of meeting and engagements held/Total Number of meetings and engagements planned)*100", "score": 100, "old_team_obj_id": 18, "status": 1},
            {"old_id": 32, "name": "Percentage of licensing gaps addressed", "target": 80, "formula": "(Number of licensing gaps addressed/total number of license gaps identified) *100", "score": 75, "old_team_obj_id": 20, "status": 1},
            {"old_id": 33, "name": "Percentage of procurements within budget", "target": 80, "formula": "(Number of procurements within budget/Total Number of procurements made)*100", "score": 100, "old_team_obj_id": 21, "status": 1},
            {"old_id": 34, "name": "Percentage of planned procurements completed", "target": 80, "formula": "(Number of planned procurements completed/Total Number of procurements planned)*100", "score": 70, "old_team_obj_id": 21, "status": 1},
            {"old_id": 38, "name": "Percentage of non-compliant operators handled", "target": 70, "formula": "(Number of non-compliant operators handled within 7 days/Total Number of non-compliant operators forwarded to Legal)*100", "score": 95, "old_team_obj_id": 22, "status": 1},
            {"old_id": 39, "name": "Percentage of checklists issued", "target": 70, "formula": "(Number of checklists issued two months prior to the expiry of the License/Total Number of Licenses due for renewal)*100", "score": 80, "old_team_obj_id": 23, "status": 1},
            {"old_id": 40, "name": "Percentage of requests addressed and responded to", "target": 70, "formula": "(Number of enforcement requests addressed and responded to/Total Number of requests received)*100", "score": 75, "old_team_obj_id": 24, "status": 1},
            {"old_id": 41, "name": "Percentage of PPDA queries addressed", "target": 80, "formula": "(Number of PPDA querries addressed/Total Number of PPDA Querries raised)*100", "score": 100, "old_team_obj_id": 25, "status": 1},
            {"old_id": 42, "name": "Percentage of Internal Audit queries addressed", "target": 80, "formula": "(Number of Internal Audit querries addressed/Total Number of Internal Audit querries raised)*100", "score": 100, "old_team_obj_id": 26, "status": 1},
            {"old_id": 44, "name": "Percentage of cases and legal documents filed in court on time", "target": 70, "formula": "(Number of court matters filed within the statutory period/the total number of court matters requiring filing) *100", "score": 100, "old_team_obj_id": 28, "status": 1},
            {"old_id": 46, "name": "Percentage of complete license applications reviewed within 60 days", "target": 70, "formula": "(Number of complete applications processed within 60 days/ number of complete applications received) *100", "score": 45, "old_team_obj_id": 30, "status": 1},
            {"old_id": 47, "name": "Percentage of approved license applications processed within the stipulated 20 days", "target": 80, "formula": "(Number of approved applications processed within 20 days/ total number of approved applications) *100", "score": 67, "old_team_obj_id": 30, "status": 1},
            {"old_id": 48, "name": "Percentage of License agreements and or license certificates dispatched to operators within 7 days from date of printing or date of signing", "target": 80, "formula": "(Number of signed agreements and certificates issued within 7 days from date of signing/Total Number of licenses issued)*100", "score": 100, "old_team_obj_id": 30, "status": 1},
            {"old_id": 49, "name": "Percentage of notified user gliches cascaded to IT Department for resolution", "target": 70, "formula": "(Number of identified glitches resolved/Total Number of identified glitches)*100", "score": 100, "old_team_obj_id": 31, "status": 1},
            {"old_id": 50, "name": "Percentage of operators submitting applications through the system", "target": 50, "formula": "(Number of applications received and processed through the E-licensing system/Total Number of applications received)*100", "score": 98, "old_team_obj_id": 31, "status": 1},
            {"old_id": 51, "name": "Percentage of procurements done within set/planned timelines", "target": 70, "formula": "(Number of procurements done within set/planned timelines/Total Number of procurements done)*100", "score": 50, "old_team_obj_id": 32, "status": 1},
            {"old_id": 52, "name": "Percentage of board action papers/Resolutions disseminated to Directors for consideration in a timely manner", "target": 70, "formula": "(Number of board action papers/Resolutions submitted to directors 7 days after board meeting/Total Number of board action papers)*100", "score": 0, "old_team_obj_id": 33, "status": 1},
            {"old_id": 53, "name": "Percentage of board action papers with updates submitted to the board in a timely manner", "target": 70, "formula": "(Number of board action papers with updates submitted to the board within 14 days before board meeting/Total Number of board action papers)*100", "score": 0, "old_team_obj_id": 33, "status": 1},
            {"old_id": 54, "name": "Percentage of board minutes submitted to the board in a timely manner", "target": 70, "formula": "(Number of board minutes submitted to the board within 14 days before board meeting/Total Number of board minutes)*100", "score": 0, "old_team_obj_id": 33, "status": 1},
            {"old_id": 55, "name": "Percentage of board papers submitted to the board in a timely manner", "target": 70, "formula": "(Number of board papers submitted to the board within 14 days before board meeting/Total Number of board papers prepared)*100", "score": 0, "old_team_obj_id": 33, "status": 1},
            {"old_id": 56, "name": "Percentage of Board international travels and logistics coordinated within set schedules", "target": 70, "formula": "(Number of board international travels and logistics coordinated within set schedules/ Total number of Board international travels)*100", "score": 0, "old_team_obj_id": 33, "status": 1},
            {"old_id": 57, "name": "Percentage of reminders to board members on report writing on return from international trips", "target": 70, "formula": "(Number of formal Reminders made to board members within 2 weeks on return from a given international travels/Total Number of Board International Travels)*100", "score": 0, "old_team_obj_id": 33, "status": 1},
            {"old_id": 58, "name": "Percentage committee action papers with updates submitted in a timely manner", "target": 70, "formula": "(Number of committee action papers with updates submitted within 14 days before committee meeting/Total Number of committee action papers prepared)*100", "score": 0, "old_team_obj_id": 34, "status": 1},
            {"old_id": 59, "name": "Percentage of committee minutes submitted to the board in a timely manner", "target": 70, "formula": "(Number of committee minutes submitted to the board within 14 days before board meeting/Total Number of committee minutes prepared)*100", "score": 0, "old_team_obj_id": 34, "status": 1},
            {"old_id": 60, "name": "Percentage of committee papers submitted in a timely manner", "target": 70, "formula": "(Number of committee papers submitted within 14 days before committee meeting/Total Number of Committee papers prepared)*100", "score": 0, "old_team_obj_id": 34, "status": 1},
            {"old_id": 61, "name": "Percentage of board sitting allowances prepared on time", "target": 70, "formula": "(Number of board meetings with sitting allowances paid prior to the meeting/Total number of board meetings)*100", "score": 0, "old_team_obj_id": 34, "status": 1},
            {"old_id": 62, "name": "Percentage of committee sitting allowances prepared on time", "target": 70, "formula": "(Number of committee meetings with sitting allowances paid prior to the meeting/Total number of committee meetings held)*100", "score": 0, "old_team_obj_id": 34, "status": 1},
            {"old_id": 63, "name": "Percentage of cases handled within statutory periods", "target": 70, "formula": "(Number of cases handled within statutory timelines/Total Number of cases handled)*100", "score": 0, "old_team_obj_id": 20, "status": 1},
            {"old_id": 64, "name": "Percentage of cases handled within statutory periods", "target": 70, "formula": "(Number of cases handled within statutory timelines/Total Number of cases handled)*100", "score": 0, "old_team_obj_id": 35, "status": 1},
            {"old_id": 65, "name": "Percentage of Legal opinions provided within 7 working days", "target": 70, "formula": "(Number of Legal opinions provided within 7 working days/Total Number of legal issues Received)*100", "score": 89, "old_team_obj_id": 36, "status": 1},
            {"old_id": 66, "name": "Percentage of legal advisory requests responded to within 7 days from date of receipt", "target": 70, "formula": "(Number of request addressed in 7 days/ total number of internal legal requests) *100", "score": 0, "old_team_obj_id": 37, "status": 1},
            {"old_id": 67, "name": "Percentage of investigations concluded within set timelines", "target": 70, "formula": "(Number of investigations concluded within set timelines/Total Number of Investigations Carried out)*100", "score": 0, "old_team_obj_id": 38, "status": 1},
            {"old_id": 68, "name": "Percentage of investigations concluded within set timelines", "target": 70, "formula": "(Number of investigations concluded within set timelines/Total Number of Investigations Carried out)*100", "score": 75, "old_team_obj_id": 39, "status": 1},
            {"old_id": 69, "name": "Percentage of risks with adoptable mitigation measures", "target": 70, "formula": "(Number of risks with workable mitigation measures /Total Number of Risks Identified)*100", "score": 85, "old_team_obj_id": 40, "status": 1},
            {"old_id": 70, "name": "Percentage of identified litigation risks with mitigation measures", "target": 50, "formula": "(Number of risks mitigated/total number of risks identified) *100", "score": 100, "old_team_obj_id": 41, "status": 1},
            {"old_id": 71, "name": "Percentage of identified risks within the licensing process with workable mitigation measures in place", "target": 70, "formula": "(Number of risks in the licensing process with workable mitigants/ Total Number of risks in the licensing process identified) *100", "score": 100, "old_team_obj_id": 42, "status": 1},
            {"old_id": 72, "name": "Percentage of identified risks with mitigation measures", "target": 70, "formula": "(Number of identified risks with mitigation measures/Total Number of identified risks)*100", "score": 100, "old_team_obj_id": 43, "status": 1},
            {"old_id": 73, "name": "Percentage of Mitigation Measures with Updates", "target": 70, "formula": "(Number of mitigants with updates/ Total Number of Mitigants) *100", "score": 100, "old_team_obj_id": 44, "status": 1},
            {"old_id": 74, "name": "Percentage of Commission's Contracts and MOUs reviewed for completeness", "target": 70, "formula": "(Number of Commission's Contracts and MOUs reviewed for completeness/Total Number of agreements and MOUs received by Compliance and Enforcement Unit)*100", "score": 100, "old_team_obj_id": 45, "status": 1},
            {"old_id": 77, "name": "Percentage of service requests handled within 5 days", "target": 70, "formula": "(Number of service requests handled within 5 days/Total number of service requests handled)*100", "score": 0, "old_team_obj_id": 42, "status": 1},
            {"old_id": 80, "name": "Budget absorption rate", "target": 100, "formula": "(Actual Expenditure/Amount in administration Expenditure Budget)*100", "score": 74, "old_team_obj_id": 49, "status": 1},
            {"old_id": 83, "name": "Percentage of creditors below 30 days", "target": 80, "formula": "(Number of creditors below 30 days/Total Number of creditors)*100", "score": 51, "old_team_obj_id": 51, "status": 1},
            {"old_id": 84, "name": "Budget Absorption Rate", "target": 100, "formula": "(Actual Expenditure/Budgeted Amount)*100", "score": 106, "old_team_obj_id": 52, "status": 1},
            {"old_id": 85, "name": "Percentage Expenditure aligned to Strategy", "target": 100, "formula": "Percentage of analysis of actual vs strategy", "score": 100, "old_team_obj_id": 53, "status": 1},
            {"old_id": 87, "name": "Percentage Increase in Revenue", "target": 5, "formula": "Revenue Growth = 100*(Current FY Revenue - Previous FY Revenue)/Previous FY Revenue", "score": 0, "old_team_obj_id": 54, "status": 1},
            {"old_id": 88, "name": "Percentage of the amount spent within the budget", "target": 90, "formula": "(Amount spent/Amount budgeted)*100", "score": 75, "old_team_obj_id": 55, "status": 1},
            {"old_id": 89, "name": "Percentage of identified audit recommendations implemented", "target": 80, "formula": "(Number of audit recommendations implemented/ Total number of audit recommendations identified.)*100", "score": 93, "old_team_obj_id": 56, "status": 1},
            {"old_id": 91, "name": "Percentage of workforce that meet performance standards", "target": 88, "formula": "(Number of staff who scored above set standards 65/Total number of staff)*100", "score": 0, "old_team_obj_id": 58, "status": 1},
            {"old_id": 92, "name": "Percentage of Revenues Billed", "target": 100, "formula": "(Amount of Revenues Billed/Amount of Revenue Budgeted)*100", "score": 99, "old_team_obj_id": 59, "status": 1},
            {"old_id": 93, "name": "Staff Satisfaction Survey", "target": 80, "formula": "Satisfaction Survey score", "score": 0, "old_team_obj_id": 60, "status": 1},
            {"old_id": 95, "name": "Percentage of Revenues Collected", "target": 80, "formula": "(Amount of Revenues collected/Amount of Revenue Budgeted)*100", "score": 83, "old_team_obj_id": 62, "status": 1},
            {"old_id": 96, "name": "Percentage of Debtors below 90 days", "target": 85, "formula": "(Number of Debtors below 90 days/Total Number of Debtors)*100", "score": 89, "old_team_obj_id": 63, "status": 1},
            {"old_id": 98, "name": "Percentage of service requests handled within 5 days", "target": 70, "formula": "(Number of service requests handled within 5 days/Total number of service requests handled)*100", "score": 80, "old_team_obj_id": 64, "status": 1},
            {"old_id": 99, "name": "Percentage of Manpower plan implemented", "target": 100, "formula": "(Number of cavant positions filled within set timelines/Total number of vacant positions approved for recruitment in a year)*100", "score": 0, "old_team_obj_id": 65, "status": 1},
            {"old_id": 101, "name": "Percentage of status reports that have been prepared", "target": 80, "formula": "(Number of status reports prepared in a timely manner/Total number of status reports expected to be prepared)*100", "score": 58, "old_team_obj_id": 67, "status": 1},
            {"old_id": 103, "name": "Percentage of service reports that have been prepared on time", "target": 90, "formula": "(Number of service reports prepared in a timely manner/Total number status reports expected to be prepared)*100", "score": 67, "old_team_obj_id": 69, "status": 1},
            {"old_id": 104, "name": "Percentage of finance reports developed in line with the QA framework and submitted on agreed timelines", "target": 90, "formula": "(Number of finance reports developed in line with the QA framework and submitted on agreed timelines/ Total Number of Financial Reports produced)*100", "score": 93, "old_team_obj_id": 70, "status": 1},
            {"old_id": 105, "name": "Timeliness of budget preparation", "target": 100, "formula": "In accordance to PFMA", "score": 100, "old_team_obj_id": 71, "status": 1},
            {"old_id": 106, "name": "Percentage of operational documents that have been prepared", "target": 100, "formula": "(Number of operational documents prepared in a timely manner/Total number of operational documents expected to be prepared)*100", "score": 75, "old_team_obj_id": 72, "status": 1},
            {"old_id": 107, "name": "Annual budget Report Quality Score", "target": 100, "formula": "In accordance to PFMA", "score": 0, "old_team_obj_id": 73, "status": 1},
            {"old_id": 109, "name": "Percentage of timely implemented activities in the administration work plan", "target": 85, "formula": "(Number of activities executed on time/Total workplan activities)*100", "score": 64, "old_team_obj_id": 75, "status": 1},
            {"old_id": 112, "name": "Percentage of Creditors below 90 Days", "target": 90, "formula": "(Number of Creditors below 60 days/Total Number of Creditors)*100", "score": 82, "old_team_obj_id": 78, "status": 1},
            {"old_id": 114, "name": "Percentage of staff outstanding accountable advances below 60 days", "target": 80, "formula": "(Number of staff with outstanding accountable advances below 60 days/Total Number of staff with accountable advances)*100", "score": 75, "old_team_obj_id": 79, "status": 1},
            {"old_id": 115, "name": "Percentage of audit issues addressed", "target": 80, "formula": "(Number of audit issues resolved/Total number of audit reported) *100", "score": 0, "old_team_obj_id": 80, "status": 1},
            {"old_id": 116, "name": "Percentage of Litigation and Prosecution team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of litigation and prosecution team targets)*100", "score": 100, "old_team_obj_id": 81, "status": 1},
            {"old_id": 117, "name": "Percentage of Legal Affair team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of legal affairs team targets)*100", "score": 73, "old_team_obj_id": 82, "status": 1},
            {"old_id": 118, "name": "Percentage of Compliance and Enforcement team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of compliance and enforcement team targets)*100", "score": 64, "old_team_obj_id": 83, "status": 1},
            {"old_id": 119, "name": "Percentage of procurement team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of procurement team targets)*100", "score": 0, "old_team_obj_id": 84, "status": 1},
            {"old_id": 122, "name": "Number of critical positions identified for succession planning", "target": 100, "formula": "(Number of critical positions classified/Total number of positions identified)*100", "score": 0, "old_team_obj_id": 86, "status": 1},
            {"old_id": 123, "name": "Job description manual/Planned frameworks", "target": 100, "formula": "(Number of job description framework drafted/Total number of frameworks)*100", "score": 0, "old_team_obj_id": 87, "status": 1},
            {"old_id": 125, "name": "Proportion of planned governance systems reviewed as per schedule", "target": 80, "formula": "Number of governance systems reviewed/Total number of governance systems scheduled for review", "score": 0, "old_team_obj_id": 89, "status": 1},
            {"old_id": 127, "name": "Number of reports scheduled for submission to the audit committee, concluded three weeks prior to the meeting/", "target": 80, "formula": "Number of reports submitted to the audit committee or concluded three weeks prior to the meeting/Total Number of reports scheduled for submission to the audit committee, concluded three weeks prior to the meeting.", "score": 75, "old_team_obj_id": 89, "status": 1},
            {"old_id": 129, "name": "Percentage of staff using the HRA self service portals", "target": 80, "formula": "(Number of staff using HRA self service portals/Total number of staff)*100", "score": 0, "old_team_obj_id": 91, "status": 1},
            {"old_id": 144, "name": "Proportion of sensitizations/engagements with risk champions", "target": 80, "formula": "Number of sensitizations/engagements with risk champions conducted/ Total number of planned engagements", "score": 100, "old_team_obj_id": 104, "status": 1},
            {"old_id": 145, "name": "Proportion of Business units/departments sensitized on risk management", "target": 80, "formula": "No. of business units/departments sensitized on risk management/ Total no. of business units", "score": 0, "old_team_obj_id": 106, "status": 1},
            {"old_id": 146, "name": "Percentage of risk coordination reports meeting the quality standards/checklist (80 %)", "target": 80, "formula": "No. of risk assignments meeting 80% quality standard/Total No. of completed assignments", "score": 100, "old_team_obj_id": 107, "status": 1},
            {"old_id": 147, "name": "Percentage of the risk universe with updated risk information", "target": 80, "formula": "No. of risk universe with updated risk information / Total No. of risk universe", "score": 100, "old_team_obj_id": 108, "status": 1},
            {"old_id": 148, "name": "Percentage of scheduled business units with risk updates", "target": 80, "formula": "No. of scheduled business units with risk updates / Total No. of business units scheduled for risk updates", "score": 100, "old_team_obj_id": 108, "status": 1},
            {"old_id": 149, "name": "Percentage of business units with updated compliance registers", "target": 80, "formula": "No. of business units with updated compliance information/Total no. of business units scheduled for compliance reviews", "score": 100, "old_team_obj_id": 109, "status": 1},
            {"old_id": 150, "name": "Percentage of audit assignments/reports meeting the quality standards/checklist", "target": 80, "formula": "No. of audit assignments meeting 80% quality standard/Total No. of completed assignments", "score": 100, "old_team_obj_id": 110, "status": 1},
            {"old_id": 151, "name": "Percentage of activities delivered within the set timelines for the two QoS assessment exercises", "target": 80, "formula": "(Activities carried out within the set timelines)/ (total number of activities ) for the 2 exercises* 100", "score": 67, "old_team_obj_id": 111, "status": 1},
            {"old_id": 152, "name": "Percentage of audit assignments performed using the audit tools & technology", "target": 80, "formula": "No. of audit tasks performed using existing tools& technology / Total No. of audit tasks scheduled to use audit tools & technology", "score": 100, "old_team_obj_id": 112, "status": 1},
            {"old_id": 153, "name": "Percentage of audit assignments performed using the audit tools & technology", "target": 80, "formula": "No. of audit tasks performed using existing tools& technology / Total No. of audit tasks scheduled to use audit tools & technology", "score": 0, "old_team_obj_id": 113, "status": 1},
            {"old_id": 154, "name": "Proportion of Internal audit (assurance) staff trained as per the skills gap", "target": 70, "formula": "Number of assurance staff trained in the FY 2022-23/ Total number of assurance staff scheduled for training in the FY 2022-23", "score": 0, "old_team_obj_id": 114, "status": 1},
            {"old_id": 155, "name": "Proportion of risk and compliance staff trained as per the skills gap", "target": 70, "formula": "Number of risk and compliance staff trained in the FY 2022-23/ Total number of staff scheduled for training in the FY 2022-23", "score": 0, "old_team_obj_id": 115, "status": 1},
            {"old_id": 156, "name": "Proportion of Internal audit (assurance) staff attaining the 65% performance appraisal score", "target": 80, "formula": "Number of Assurance staff attaining 65% performance appraisal score in the FY 2022-23/Total of number of staff in the team in the FY 2022-23", "score": 0, "old_team_obj_id": 117, "status": 1},
            {"old_id": 157, "name": "Proportion of Risk and Compliance staff attaining the 65% performance appraisal score", "target": 80, "formula": "Number of Risk and Compliance staff attaining 65% performance appraisal score in the FY 2022-23/Total of number of staff in the team in the FY 2022-23", "score": 0, "old_team_obj_id": 118, "status": 1},
            {"old_id": 158, "name": "Percentage of cases of interference investigated and reported within the ECI Charter timelines", "target": 75, "formula": "(Number of cases of interference handled & reported/Total number of cases of interference received) *100", "score": 85, "old_team_obj_id": 119, "status": 1},
            {"old_id": 160, "name": "% of quarterly radio frequency utilization reports submitted in the financial year (X/(no. of quarters considered)", "target": 100, "formula": "Number of quarterly reports submitted/Total expected reports in a year*100", "score": 51, "old_team_obj_id": 121, "status": 1},
            {"old_id": 161, "name": "Percentage of assigned numbering resources in use", "target": 80, "formula": "(Number of assigned numbering resources per block in use/total number of assigned numbering resources per block)*100", "score": 38, "old_team_obj_id": 122, "status": 1},
            {"old_id": 168, "name": "Percentage of technical evaluations for licenses completed within the ECI specified time", "target": 83, "formula": "(Number of technical evaluations for licenses completed in line with the department charter/Total number of license applications received) *100", "score": 95, "old_team_obj_id": 127, "status": 1},
            {"old_id": 170, "name": "Percentage of Spectrum Assignees with information on compliance status not more than six months old", "target": 85, "formula": "(Number of licensees with Spectrum Assignees whose information is six months or less/total number of Spectrum Assignees) *100", "score": 94, "old_team_obj_id": 129, "status": 1},
            {"old_id": 173, "name": "Percentage of SMD workplan activities implemented as scheduled", "target": 85, "formula": "(Number of SMD workplan activities implemented as scheduled/total number of SMD workplan activities planned) *100", "score": 78, "old_team_obj_id": 132, "status": 1},
            {"old_id": 175, "name": "Percentage smd tools utilization as per agreed criteria", "target": 80, "formula": "(Number of SMD tools utilized as per agreed criteria/Total number of tools)*100", "score": 100, "old_team_obj_id": 134, "status": 1},
            {"old_id": 182, "name": "Stakeholder satisfaction score", "target": 80, "formula": "Snap short project surveys", "score": 83, "old_team_obj_id": 141, "status": 1},
            {"old_id": 183, "name": "Percentage of technical audit completed within three weeks", "target": 70, "formula": "Number od technical audits completed/Total number of technical audits*100%", "score": 95, "old_team_obj_id": 142, "status": 1},
            {"old_id": 184, "name": "Percentage of project monitoring activities completed as per schedule", "target": 80, "formula": "Number of project monitoring activities done/Total number of projects*100%", "score": 79, "old_team_obj_id": 143, "status": 1},
            {"old_id": 185, "name": "Percentage of projects initiated as per schedule/ workplan", "target": 90, "formula": "(Number of projects initiated/Total number of projects in the workplan)*100%", "score": 90, "old_team_obj_id": 144, "status": 1},
            {"old_id": 186, "name": "Percentage of projects executed as per schedule", "target": 90, "formula": "(Number of projects executed/Total number of projects in the schedule)*100", "score": 47, "old_team_obj_id": 145, "status": 1},
            {"old_id": 187, "name": "Percentage of Projects rolled over to the next year", "target": 25, "formula": "(Number of projects rolled over/Total number of projects implemented)*100", "score": 42, "old_team_obj_id": 146, "status": 1},
            {"old_id": 188, "name": "Percentage of correspondences completed as per the charter", "target": 80, "formula": "(Number of correspondences answered/Total number of correspondences received)*100%", "score": 61, "old_team_obj_id": 147, "status": 1},
            {"old_id": 189, "name": "User satisfaction score for ICT Services", "target": 80, "formula": "Percentage score attained", "score": 74, "old_team_obj_id": 148, "status": 1},
            {"old_id": 190, "name": "User satisfaction score for ISU Services", "target": 80, "formula": "Percentage score attained", "score": 64, "old_team_obj_id": 149, "status": 1},
            {"old_id": 191, "name": "User satisfaction score for CERT Services", "target": 80, "formula": "Percentage score attained", "score": 0, "old_team_obj_id": 150, "status": 1},
            {"old_id": 192, "name": "Percentage of queries responded to as per the charter", "target": 90, "formula": "(Number of querries responded to as per the charter/Total Number of Queries received)*100", "score": 95, "old_team_obj_id": 151, "status": 1},
            {"old_id": 193, "name": "Percentage of databases compiled within specified time", "target": 80, "formula": "(Number of databases compiled within the specified time/Total Number of databases set out to be done)*100", "score": 0, "old_team_obj_id": 152, "status": 1},
            {"old_id": 194, "name": "Percentage of queries responded to as per the charter", "target": 90, "formula": "(Number of querries responded to as per the charter/Total Number of Queries received)*100", "score": 0, "old_team_obj_id": 153, "status": 1},
            {"old_id": 195, "name": "Percentage of queries responded to as per the charter", "target": 90, "formula": "(Number of querries responded to as per the charter/Total Number of Querries received)*100", "score": 0, "old_team_obj_id": 154, "status": 1},
            {"old_id": 196, "name": "Proportion of digital initiatives implemented as per the agreed project plans/road maps", "target": 80, "formula": "(Number of Digital initiatives implemented as per agreed project plan/road map/Total No. of Digital initiatives scheduled to be implemented)*100", "score": 80, "old_team_obj_id": 155, "status": 1},
            {"old_id": 197, "name": "Percentage of quarterly reports produced on Implementation of sector cyber security strategy", "target": 20, "formula": "(Number of Quarterly reports produced/Total Number planned)*100", "score": 0, "old_team_obj_id": 156, "status": 1},
            {"old_id": 198, "name": "Commission Cyber Readiness index", "target": 75, "formula": "(Number of monthly reports presented to the Board/Total  reports planned)*100", "score": 0, "old_team_obj_id": 157, "status": 1},
            {"old_id": 199, "name": "Percentage Expenditure within budget", "target": 100, "formula": "(Actual IT team expenditure/Total budget allocation to IT Team)*100", "score": 100, "old_team_obj_id": 158, "status": 1},
            {"old_id": 200, "name": "Percentage Expenditure within budget", "target": 100, "formula": "(Actual ISU team expenditure/Total budget allocation to ISU Team)*100", "score": 0, "old_team_obj_id": 159, "status": 1},
            {"old_id": 201, "name": "Percentage Expenditure within budget", "target": 100, "formula": "(Actual CERT team expenditure/Total budget allocation to CERT Team)*100", "score": 0, "old_team_obj_id": 160, "status": 1},
            {"old_id": 202, "name": "Percentage Expenditure within budget", "target": 90, "formula": "(Actual Research team expenditure/Total budget allocation to Research Team)*100", "score": 100, "old_team_obj_id": 161, "status": 1},
            {"old_id": 203, "name": "Proportion of Budget Savings", "target": 2, "formula": "(Actual saved by IT team/Total budget allocation to IT Team)*100", "score": 3, "old_team_obj_id": 162, "status": 1},
            {"old_id": 204, "name": "Proportion of Budget Savings", "target": 20, "formula": "(Actual saved by ISU team/Total budget allocation to ISU Team)*100", "score": 0, "old_team_obj_id": 163, "status": 1},
            {"old_id": 205, "name": "Proportion of Budget Savings", "target": 20, "formula": "(Actual saved by CERT team/Total budget allocation to CERT Team)*100", "score": 0, "old_team_obj_id": 164, "status": 1},
            {"old_id": 206, "name": "Proportion of Budget Savings", "target": 20, "formula": "(Actual saved by Research team/Total budget allocation to Research Team)*100", "score": 0, "old_team_obj_id": 165, "status": 1},
            {"old_id": 207, "name": "Proportion of Audit issues issues identified and implemented", "target": 70, "formula": "(Number of Audit issues issues identified and implemented/Total Number of Audit Issues)*100", "score": 0, "old_team_obj_id": 166, "status": 1},
            {"old_id": 208, "name": "Proportion of Registers developed", "target": 50, "formula": "(No of departments with developed and updated registers /total No of Departments)*100", "score": 55, "old_team_obj_id": 166, "status": 1},
            {"old_id": 209, "name": "Proportion of Departments aligned to their respective processes in ERDMS", "target": 85, "formula": "(Number of departments aligned/Total number of departments)*100", "score": 60, "old_team_obj_id": 166, "status": 1},
            {"old_id": 210, "name": "Proportion of Information processed and organized in time as per the charter", "target": 85, "formula": "(Information processed and organized in charter timelines/Total information received)*100", "score": 90, "old_team_obj_id": 166, "status": 1},
            {"old_id": 211, "name": "Proportion of contracts/projects completed according to the specified terms of references", "target": 80, "formula": "(Number of contracts/projects completed according to the specified terms of references/ Total number in the FY)*100", "score": 54, "old_team_obj_id": 170, "status": 1},
            {"old_id": 212, "name": "Percentage Implementation of audit/risk recommendations within a financial year", "target": 80, "formula": "(Number of audit/risk recommendations implemented within a financial year/Total number of audit recommendations raised)*100", "score": 80, "old_team_obj_id": 171, "status": 1},
            {"old_id": 213, "name": "Percentage Implementation of audit/risk recommendations within a financial year", "target": 80, "formula": "Number of audit/risk recommendations implemented within a financial year/Total number of audit recommendations raised)*100", "score": 90, "old_team_obj_id": 172, "status": 1},
            {"old_id": 214, "name": "Percentage Implementation of audit/risk recommendations within a financial year", "target": 80, "formula": "(Number of audit/risk recommendations implemented within a financial year/Total number of audit recommendations raised)*100", "score": 0, "old_team_obj_id": 173, "status": 1},
            {"old_id": 215, "name": "Percentage of approved research reports", "target": 80, "formula": "(Number of approved research reports available( based on approved research agenda studies) for publication / Number of approved research agenda studies for FY 2022/23)*100", "score": 25, "old_team_obj_id": 174, "status": 1},
            {"old_id": 216, "name": "Proportion of information disseminated by the R&SD division versus studies conducted", "target": 80, "formula": "(Number of research studies conducted and disseminated/Total Number of studies conducted)*100", "score": 86, "old_team_obj_id": 175, "status": 1},
            {"old_id": 217, "name": "Proportion of Knowledge Sharings carried out", "target": 60, "formula": "(Number of Knwledge sharing sessions carried out/Total Number of Knowledge sharing sessions planned)*100", "score": 87, "old_team_obj_id": 176, "status": 1},
            {"old_id": 218, "name": "Proportion of Teams Service Charter KPIs attained", "target": 60, "formula": "(ICT Service Charter KPIs attained/Number of Service Charter KPIs)*100", "score": 0, "old_team_obj_id": 177, "status": 1},
            {"old_id": 219, "name": "Proportion of Teams Service Charter KPIs attained", "target": 60, "formula": "(ISU Service Charter KPIs attained/Number of Service Charter KPIs)*100", "score": 0, "old_team_obj_id": 178, "status": 1},
            {"old_id": 220, "name": "Proportion of Teams Service Charter KPIs attained", "target": 60, "formula": "(CERT Service Charter KPIs attained/Number of Service Charter KPIs)*100", "score": 0, "old_team_obj_id": 179, "status": 1},
            {"old_id": 221, "name": "Proportion of Teams Service Charter KPIs attained", "target": 60, "formula": "(Research Service Charter KPIs attained/Number of Service Charter KPIs)*100", "score": 0, "old_team_obj_id": 180, "status": 1},
            {"old_id": 222, "name": "Percentage of IT systems that are available", "target": 100, "formula": "(Number of IT systems available/ Number of IT systems monitored)*100", "score": 99, "old_team_obj_id": 181, "status": 1},
            {"old_id": 223, "name": "Percentage of Team processes and policies Reviewed", "target": 90, "formula": "(Number of IT Team processes and policies reviewed/Total Planned)*100", "score": 0, "old_team_obj_id": 182, "status": 1},
            {"old_id": 224, "name": "Percentage of Team processes and policies Reviewed", "target": 90, "formula": "(Number of ISU Team processes and policies reviewed/Total Planned)*100", "score": 0, "old_team_obj_id": 183, "status": 1},
            {"old_id": 225, "name": "Percentage of Team processes and policies Reviewed", "target": 90, "formula": "(Number of CERT Team processes and policies reviewed/Total Planned)*100", "score": 0, "old_team_obj_id": 184, "status": 1},
            {"old_id": 226, "name": "Percentage of trainings held", "target": 80, "formula": "(Number of trainings held/Total Number of planned trainings)*100", "score": 100, "old_team_obj_id": 185, "status": 1},
            {"old_id": 227, "name": "Proportion of information disseminated", "target": 80, "formula": "(Information disseminated/Number of studies conducted)*100", "score": 86, "old_team_obj_id": 186, "status": 1},
            {"old_id": 228, "name": "Percentage of tools and technologies used in execution of business processes", "target": 80, "formula": "(Number of tools and technologies used in execution of business processes/Total Number of tools and technologies available)*100", "score": 85, "old_team_obj_id": 187, "status": 1},
            {"old_id": 229, "name": "Percentage utilization of tools and technologies by staff for various Commission business processes", "target": 80, "formula": "(Number of tools and technologies used by staff for various Commission business processes/Total Number of tools and technologies available)*100", "score": 89, "old_team_obj_id": 187, "status": 1},
            {"old_id": 230, "name": "Percentage utilization of tools to execute division business processes", "target": 100, "formula": "(Number of tools used to execute division business processes/Total Number of tools available)*100", "score": 87, "old_team_obj_id": 187, "status": 1},
            {"old_id": 231, "name": "Percentage Increment in Usage of Resource Centre", "target": 75, "formula": "(Total No of Users in 2022/23/Total Number of users in 2021/22) -1*100", "score": 80, "old_team_obj_id": 190, "status": 1},
            {"old_id": 232, "name": "Proportion of Digitised information", "target": 80, "formula": "(Number of digitized information/ Total Physical Information Received)*100", "score": 0, "old_team_obj_id": 191, "status": 1},
            {"old_id": 233, "name": "Percentage of IT staff achieving 70% and above", "target": 70, "formula": "(Number of IT staff achieving 70% and above/Total Number of IT Staff)*100", "score": 100, "old_team_obj_id": 192, "status": 1},
            {"old_id": 234, "name": "Percentage of ISU staff achieving 70% and above", "target": 70, "formula": "(Number of ISU staff achieving 70% and above/Total Number of ISU Staff)*100", "score": 100, "old_team_obj_id": 193, "status": 1},
            {"old_id": 235, "name": "Percentage of CERT staff achieving 70% and above", "target": 70, "formula": "(Number of CERT staff achieving 70% and above/Total Number of ISU Staff)*100", "score": 0, "old_team_obj_id": 194, "status": 1},
            {"old_id": 236, "name": "Percentage of Research staff achieving 70% and above", "target": 70, "formula": "(Number of Research staff achieving 70% and above/Total Number of ISU Staff)*100", "score": 75, "old_team_obj_id": 195, "status": 1},
            {"old_id": 237, "name": "Percentage of IT team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of IT team targets)*100", "score": 60, "old_team_obj_id": 196, "status": 1},
            {"old_id": 238, "name": "Percentage of ISU team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of ISU team targets)*100", "score": 57, "old_team_obj_id": 197, "status": 1},
            {"old_id": 239, "name": "Percentage of CERT team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of CERT team targets)*100", "score": 0, "old_team_obj_id": 198, "status": 1},
            {"old_id": 240, "name": "Percentage of Research team targets achieved", "target": 80, "formula": "(Number of Targets Achieved/Total Number of Research team targets)*100", "score": 61, "old_team_obj_id": 199, "status": 1},
            {"old_id": 246, "name": "Percentage of updated contracts in the database", "target": 70, "formula": "(Number of contracts updated/Total number of contracts with pending issues)*100", "score": 0, "old_team_obj_id": 14, "status": 1},
            {"old_id": 247, "name": "Percentage of Insurance issues resolved", "target": 70, "formula": "(Number of Insurance claims addressed/total number of insurance claims filed)*100", "score": 0, "old_team_obj_id": 14, "status": 1},
            {"old_id": 248, "name": "Percentage of ratified treaties, agreements and resolutions adopted within the Commission", "target": 50, "formula": "(Number of legal and Regulatory obligations adopted within the Commission/Total number of international treaties, agreements and conventions)*100", "score": 30, "old_team_obj_id": 19, "status": 1},
            {"old_id": 250, "name": "Percentage of reports on unauthorized operations submitted on time", "target": 100, "formula": "(No. of quarterly reports of unauthorized reports submitted on time/No. of expected reports)*100", "score": 0, "old_team_obj_id": 119, "status": 1},
            {"old_id": 251, "name": "Percentage of identified Board/TMT recommendations implemented", "target": 80, "formula": "(Number of Board/TMT recommendations implemented/Total number of audit recommendations identified)*100", "score": 85, "old_team_obj_id": 56, "status": 1},
            {"old_id": 252, "name": "Annual Budget Quality Score", "target": 100, "formula": "As per PFMA standards", "score": 100, "old_team_obj_id": 71, "status": 1},
            {"old_id": 253, "name": "percentage of staff identified for recognition", "target": 50, "formula": "(number of staff identified for rewards and recognition/total number of staff in the Commission)*100", "score": 0, "old_team_obj_id": 88, "status": 1},
            {"old_id": 261, "name": "Percentage of content dissemination plan implemented", "target": 80, "formula": "(Number of contents disseminated/Number of contents planned)*100", "score": 75, "old_team_obj_id": 205, "status": 1},
            {"old_id": 262, "name": "Percentage of website content reports produced", "target": 70, "formula": "(Number of reports produced/Total number of reports planned)*100", "score": 0, "old_team_obj_id": 205, "status": 1},
            {"old_id": 269, "name": "Percentage of branding ideas whose procurements have been initiated", "target": 80, "formula": "(Number of branding initiatives whose procurements were initiated/Total Number of ideas identified)*100", "score": 60, "old_team_obj_id": 211, "status": 1},
            {"old_id": 271, "name": "Strategy and business workplan execution rate", "target": 80, "formula": "(Number of SBP planned activities executed/total SBP work plan activities)*100", "score": 71, "old_team_obj_id": 213, "status": 1},
            {"old_id": 272, "name": "Percentage of consumer related complaints concluded within the set timelines (2 weeks)", "target": 95, "formula": "(Number of complaints for which the UCC decision has been communicated to the consumer in the set time/total number of consumer complaints received (call centre, letters, email and social media))*100", "score": 85, "old_team_obj_id": 214, "status": 1},
            {"old_id": 273, "name": "Percentage of PIR workplan execution rate", "target": 80, "formula": "(Number of PIR planned activities executed/total PIR work plan activities)*100", "score": 71, "old_team_obj_id": 215, "status": 1},
            {"old_id": 274, "name": "Percentage of competition-related complaints resolved within 45 working days", "target": 85, "formula": "(Number of complaints for which a UCC ruling is issued to the complainant in the set time/total number of competition related complaints received)*100", "score": 80, "old_team_obj_id": 216, "status": 1},
            {"old_id": 275, "name": "Percentage of content related complaints concluded within 20 working days", "target": 80, "formula": "(Number of complaints for which a UCC ruling is communicated to the complainant in the set time/total number of content related complaints received.)*100", "score": 71, "old_team_obj_id": 217, "status": 1},
            {"old_id": 277, "name": "Percentage of quarterly Content and local quota assessment reports ready for publication in the month following the respective quarter", "target": 75, "formula": "(Number of quarterly reports approved for publication by ED the month following the respective quarter/4 (number of quarters in the year))*100", "score": 65, "old_team_obj_id": 219, "status": 1},
            {"old_id": 279, "name": "Percentage of reports ready for publication in the month following the respective quarter", "target": 75, "formula": "(Number of quarterly reports approved for publication by ED the month following the respective quarter/4 (number of quarters in the year))*100", "score": 75, "old_team_obj_id": 221, "status": 1},
            {"old_id": 280, "name": "Percentage of country proposals presented", "target": 60, "formula": "(Number of country proposals made/Total Number of international Travels made)*100", "score": 36, "old_team_obj_id": 222, "status": 1},
            {"old_id": 281, "name": "Percentage of consumer advisories issued", "target": 62, "formula": "(Number of weekly consumer notices put out/52 (number of weeks) planned)*100", "score": 60, "old_team_obj_id": 221, "status": 1},
            {"old_id": 282, "name": "Percentage of consumer advisories issued", "target": 62, "formula": "(Number of daily consumer advisories made on the online presence/365 days planned)*100", "score": 60, "old_team_obj_id": 221, "status": 1},
            {"old_id": 283, "name": "Percentage of SBP Scorecard targets met", "target": 80, "formula": "(Number of SBP scorecard targets achieved/total SBP scorecard targets)*100", "score": 67, "old_team_obj_id": 223, "status": 1},
            {"old_id": 285, "name": "Percentage of market reports ready for publication in the month following the respective quarter", "target": 75, "formula": "(Number of quarterly reports approved for publication by ED the month following the respective quarter/4 (number of quarters in the year))*100", "score": 50, "old_team_obj_id": 225, "status": 1},
            {"old_id": 287, "name": "Percentage of available quarterly reports of competition market scans undertaken", "target": 50, "formula": "(Number of quarterly competition reports presented to TMT in the month following the respective quarter/4 (number of quarters in the year))*100", "score": 45, "old_team_obj_id": 225, "status": 1},
            {"old_id": 288, "name": "Regional offices Annual Workplan execution rate", "target": 80, "formula": "(Number of activities done/Total number of activities planned)*100", "score": 68, "old_team_obj_id": 226, "status": 1},
            {"old_id": 291, "name": "Percentage of cost centres in which a saving has been achieved versus budget (Publications, Events, Outreach, Consultancies, Field work, Tools and equipment)", "target": 66, "formula": "(Number of cost centers implemented with at least 2% savings relative to budget/6 (number of cost centers))*100", "score": 60, "old_team_obj_id": 229, "status": 1},
            {"old_id": 292, "name": "Percentage of cost centres in which a saving has been achieved versus budget (Publications, Events, Outreach, Consultancies, Field work, Tools and equipment)", "target": 66, "formula": "(Number of cost centers implemented with at least 2% savings relative to budget/6 (number of cost centers))*100", "score": 80, "old_team_obj_id": 230, "status": 1},
            {"old_id": 293, "name": "Percentage of identified regulatory frameworks/standards completed •Content distribution and exhibition", "target": 80, "formula": "(Number of identified regulatory frameworks completed/total number of frameworks identified for review)*100", "score": 65, "old_team_obj_id": 231, "status": 1},
            {"old_id": 294, "name": "Percentage of identified regulatory frameworks/standards completed", "target": 80, "formula": "(Number of identified regulatory frameworks completed/total number of frameworks identified for review)*100", "score": 60, "old_team_obj_id": 232, "status": 1},
            {"old_id": 295, "name": "PPercentage of identified regulatory frameworks/standards completed", "target": 80, "formula": "(Number of identified regulatory frameworks completed/total number of frameworks identified for review)*100", "score": 70, "old_team_obj_id": 233, "status": 1},
            {"old_id": 296, "name": "Percentage of licensees with compliance status (based on report submitted & audits/inspections conducted) of not more than six months old", "target": 70, "formula": "(Number of licensees with compliance information/total number of licensees)*100", "score": 60, "old_team_obj_id": 234, "status": 1},
            {"old_id": 297, "name": "Percentage of licensees with compliance status (based on report submitted & audits/inspections conducted) of not more than six months old(Competition obligations, postal)", "target": 70, "formula": "(Number of licensees with compliance status (of not more than six months old/ Total number of Licensees)*100", "score": 61, "old_team_obj_id": 235, "status": 1},
            {"old_id": 298, "name": "Percentage of licensees with compliance status (based on report submitted & audits/inspections conducted) of not more than six months old", "target": 70, "formula": "(Number of licensees with compliance information/total number of licensees)*100", "score": 65, "old_team_obj_id": 236, "status": 1},
            {"old_id": 299, "name": "Percentage of technical evaluations for licenses completed within the 14 days", "target": 70, "formula": "(Number of technical evaluations for licenses completed in line within the set timelines/Total number of license applications received)*100", "score": 60, "old_team_obj_id": 237, "status": 1},
            {"old_id": 300, "name": "Percentage of technical/commercial evaluations for new license applications reviewed within the 14 days", "target": 70, "formula": "(Number of technical/commercial evaluations for new license applications reviewed within the 14 days/ Total number of applications received)*100", "score": 62, "old_team_obj_id": 238, "status": 1},
            {"old_id": 301, "name": "Percentage of unit workplan activities implemented as scheduled", "target": 80, "formula": "(Number of unit workplan activities implemented as scheduled/ Total number of workplan activities identified for implementation)*100", "score": 76, "old_team_obj_id": 239, "status": 1},
            {"old_id": 302, "name": "Percentage of unit workplan activities implemented as scheduled", "target": 80, "formula": "(Number of unit workplan activities implemented as scheduled/ Total number of workplan activities identified for implementation)*100", "score": 71, "old_team_obj_id": 240, "status": 1},
            {"old_id": 303, "name": "Percentage of unit workplan activities implemented as scheduled", "target": 80, "formula": "(Number of unit workplan activities implemented as scheduled/ Total number of workplan activities identified for implementation)*100", "score": 90, "old_team_obj_id": 241, "status": 1},
            {"old_id": 304, "name": "Average Availability Score", "target": 65, "formula": "(No. of equipment meeting the established criteria/ total number of equipment) *100", "score": 55, "old_team_obj_id": 248, "status": 1},
            {"old_id": 305, "name": "Percentage of data collection portals developed to include the telecom, postal, multimedia and broadcast sectors", "target": 70, "formula": "(Number of portals developed / Number of portals identified for development)*100", "score": 58, "old_team_obj_id": 249, "status": 1},
            {"old_id": 306, "name": "Average Availability Score", "target": 65, "formula": " (No. of equipment meeting the established criteria/ total number of equipment) *100", "score": 60, "old_team_obj_id": 250, "status": 1},
            {"old_id": 309, "name": "Internal stakeholder engagement score", "target": 75, "formula": "(Number of staakeholder engagements implemented/Total number of stakeholder engagements planned)*100", "score": 90, "old_team_obj_id": 253, "status": 1},
            {"old_id": 310, "name": "PIR charter score", "target": 70, "formula": "(Number of PIR Charter targets achieved/Total number of PIR Charter targets)*100", "score": 90, "old_team_obj_id": 254, "status": 1},
            {"old_id": 313, "name": "Percentage of planned frameworks developed", "target": 70, "formula": "(Number of frameworks developed/Number of expected frameworks)*100", "score": 60, "old_team_obj_id": 257, "status": 1},
            {"old_id": 315, "name": "Regional offices productivity score (% of staff meeting performance targets)", "target": 80, "formula": "(Number of staff meeting performance targets/Total number of staff)*100", "score": 61, "old_team_obj_id": 259, "status": 1},
            {"old_id": 324, "name": "Staff Satisfaction Survey", "target": 80, "formula": "Satisfaction Survey Score", "score": 75, "old_team_obj_id": 265, "status": 1},
            {"old_id": 325, "name": "Percentage of workforce that meet performance standards", "target": 88, "formula": "Number of staff who scored above set standards 65/Total number of staff*100%", "score": 57, "old_team_obj_id": 266, "status": 1},
            {"old_id": 327, "name": "Number of critical positions identified for succession planning", "target": 100, "formula": "Number of critical positions classified/Total number of positions identified*100%", "score": 0, "old_team_obj_id": 270, "status": 1},
            {"old_id": 328, "name": "Percentage of staff using the HRA self service portals", "target": 80, "formula": "Number of staff using HRA self service portals/Total number of staff*100", "score": 100, "old_team_obj_id": 271, "status": 1},
            {"old_id": 329, "name": "Percentage of Management Accounts Unit staff trained", "target": 100, "formula": "(Number of Unit Staff trained/Total Number planned to be trained)*100", "score": 100, "old_team_obj_id": 262, "status": 1},
            {"old_id": 330, "name": "Percentage of Management Accounts unit staff scoring above 70%", "target": 70, "formula": "(Number of Management Accounts unit staff scoring above 70%/Total  number of staff in the unit)*100", "score": 100, "old_team_obj_id": 273, "status": 1},
            {"old_id": 331, "name": "Percentage of Expenditure Unit Staff Trained", "target": 100, "formula": "(Number of Expenditure Unit Staff Trained/Total Number of Staff in the Unit)*100", "score": 100, "old_team_obj_id": 272, "status": 1},
            {"old_id": 332, "name": "Percentage of Revenue Unit Staff Scoring above 70%", "target": 70, "formula": "(Number of Revenue Unit Staff Scoring above 70%/Total Number of staff in the unit)*100", "score": 100, "old_team_obj_id": 275, "status": 1},
            {"old_id": 333, "name": "Percentage of Revenue Unit staff trained", "target": 100, "formula": "(Number of Revenue Unit staff trained/Total Number of staff in the Unit)*100", "score": 100, "old_team_obj_id": 276, "status": 1},
            {"old_id": 334, "name": "Percentage Increase in Revenue", "target": 5, "formula": "Revenue Growth = 100*(Current FY Revenue - Previous FY Revenue)/Previous FY Revenue", "score": 2, "old_team_obj_id": 277, "status": 1},
            {"old_id": 338, "name": "Proportion of scheduled team outputs accomplished", "target": 80, "formula": "(Number of assignments accomplished/Total Number of planned planned assignments as per the workplan)*100", "score": 72, "old_team_obj_id": 103, "status": 1},
            {"old_id": 340, "name": "Percentage of manpower plan implemented", "target": 100, "formula": "Number of vacant positions filled within set timelines/Total number of vacant positions approved for recruitment in a year*100", "score": 43, "old_team_obj_id": 280, "status": 1},
            {"old_id": 341, "name": "Job description manual/Planned Frameworks", "target": 100, "formula": "Number of job description frameworks drafted/Total number of frameworks*100", "score": 100, "old_team_obj_id": 270, "status": 1},
            {"old_id": 342, "name": "Percentage of Team Targets achieved", "target": 80, "formula": "(Number of Team Targets achieved/Total Number of team scorecard targets)*100", "score": 0, "old_team_obj_id": 279, "status": 1},
            {"old_id": 345, "name": "Percentage of training plans implemented", "target": 90, "formula": "Number of trainings conducted, budgeted and implemented within set timelines/Total number of trainings*100", "score": 100, "old_team_obj_id": 283, "status": 1},
            {"old_id": 346, "name": "Customer Satisfaction Score", "target": 60, "formula": "Implementation of customer feedback mechanism for admin seervices", "score": 79, "old_team_obj_id": 284, "status": 1},
            {"old_id": 347, "name": "Percentage of items procured within budget", "target": 95, "formula": "Number of items that were purchased within budget/Total number of items in the Estates and Administration Expenditure budget*100", "score": 90, "old_team_obj_id": 285, "status": 1},
            {"old_id": 348, "name": "Percentage of audit issues resolved", "target": 100, "formula": "Number of audit issues resolved/Total number of audit reported*100", "score": 75, "old_team_obj_id": 286, "status": 1},
            {"old_id": 349, "name": "Percentage of HR systems used by staff", "target": 80, "formula": "Number of HR systems used by staff/Total number of systems*100", "score": 100, "old_team_obj_id": 271, "status": 1},
            {"old_id": 350, "name": "Percentage of content adhering to QA standard", "target": 80, "formula": "Number of contents adhering to QA standard/Total Number of contents received or created)*100", "score": 90, "old_team_obj_id": 205, "status": 1},
            {"old_id": 351, "name": "Percentage of PIR workplan execution rate", "target": 80, "formula": "(Number of PIR planned activities executed/total PIR work plan activities)*100", "score": 77, "old_team_obj_id": 287, "status": 1},
            {"old_id": 352, "name": "Percentage of PIR targets met", "target": 70, "formula": "(Number of PIR targets met/Total Number of PIR scorecard targets)*100", "score": 68, "old_team_obj_id": 288, "status": 1},
            {"old_id": 353, "name": "Percentage of partner objectives met ( Local and International)", "target": 75, "formula": "(Number of partner objectives met/Total number of stakeholder/partner objectives planned)*100", "score": 30, "old_team_obj_id": 222, "status": 1},
            {"old_id": 354, "name": "Percentage of planned internal staff engagements undertaken", "target": 75, "formula": "(Number of internal staff engagements undertaken/Total Number of staff engagements planned)*100", "score": 80, "old_team_obj_id": 222, "status": 1},
            {"old_id": 355, "name": "Internal Stakeholder engagement score", "target": 75, "formula": "Percentage of planned internal policy engagements undertaken", "score": 50, "old_team_obj_id": 289, "status": 1},
            {"old_id": 356, "name": "Strategy and Business Workplan execution rate", "target": 80, "formula": "(Number of SBP planned activities executed/total SBP work plan activities)*100", "score": 70, "old_team_obj_id": 290, "status": 1},
            {"old_id": 357, "name": "strategy alignment score = (percentage of business units with aligned scorecards)", "target": 85, "formula": "(Number of business units with aligned scorecards/total number of business units)*100", "score": 100, "old_team_obj_id": 291, "status": 1},
            {"old_id": 358, "name": "Internal Stakeholder engagement score", "target": 75, "formula": "Percentage of planned internal policy engagements undertaken", "score": 90, "old_team_obj_id": 292, "status": 1},
            {"old_id": 359, "name": "Percentage of planned performance reports developed within set timelines", "target": 80, "formula": "(Number of performance reports delivered on time/total planned performance reports)*100", "score": 92, "old_team_obj_id": 293, "status": 1},
            {"old_id": 360, "name": "Accuracy of UCC content", "target": 80, "formula": "(Number of Stakeholder content approved as Relevant & accurate by HoD/Total content received & produced by head of units)*100", "score": 90, "old_team_obj_id": 210, "status": 1},
            {"old_id": 361, "name": "Regional Offices Annual Workplan execution rate", "target": 80, "formula": "(Number of activities done/Total number of activities planned)*100", "score": 85, "old_team_obj_id": 294, "status": 1},
            {"old_id": 362, "name": "Tools and Technology utilization score", "target": 75, "formula": "(Number of correspondences routed through ERDMS/Total number of correspondences received by senior officer staff)*100", "score": 65, "old_team_obj_id": 295, "status": 1},
            {"old_id": 363, "name": "Proportion of reports scheduled for submission to the audit committee, concluded three weeks prior to the meeting", "target": 80, "formula": "(Number of reports submitted to the audit committee, concluded three weeks prior to the meeting/ Total Number of reports scheduled for submission to the audit committee, concluded three weeks prior to the meeting)*100", "score": 75, "old_team_obj_id": 92, "status": 1},
            {"old_id": 364, "name": "Percentage of Board and management decisions followed up within agreed timelines", "target": 80, "formula": "(Number of Board/Management minutes followed up within set timelines/Total No. of Board/management minutes in a period)*100", "score": 75, "old_team_obj_id": 93, "status": 1},
            {"old_id": 365, "name": "Proportion of business units sensitized on the audit role", "target": 90, "formula": "(Number of business units sensitized/ Total Number of business units scheduled /planned for sensitization)*100", "score": 100, "old_team_obj_id": 94, "status": 1},
            {"old_id": 368, "name": "Percentage of budgeted funds utilized within market assessed values", "target": 90, "formula": "(Funds utilized within market assessed values/Total amount of funds allocated/budgeted)*100", "score": 81, "old_team_obj_id": 95, "status": 1},
            {"old_id": 369, "name": "Proportion of procurement requests initiated three months before the scheduled time as per the procurement plan", "target": 80, "formula": "(Number of procurement requests initiated in time/Total number of procurements initiated by the team in the FY)*100", "score": 100, "old_team_obj_id": 95, "status": 1},
            {"old_id": 370, "name": "Proportion of contracts implemented as per the contract management plans", "target": 85, "formula": "(Number of contracts implemented as per the contract management plans/ Total Number of contracts implemented)*100", "score": 100, "old_team_obj_id": 95, "status": 1},
            {"old_id": 371, "name": "Proportion of contracts implemented as per the contract management plans", "target": 85, "formula": "(Number of contracts implemented as per the contract management plans/ Total Number of contracts implemented)*100", "score": 100, "old_team_obj_id": 97, "status": 1},
            {"old_id": 372, "name": "Percentage of assignments completed within set timelines", "target": 70, "formula": "(Number of assignments completed within set timelines/Total Number of planned assignments)*100", "score": 72, "old_team_obj_id": 98, "status": 1},
            {"old_id": 377, "name": "Percentage of the risk/audit universe with updated risk information", "target": 80, "formula": "(Number of risk/audit universe with updated risk information/Total Number of audit universe)*100", "score": 0, "old_team_obj_id": 301, "status": 1},
            {"old_id": 379, "name": "Proportion of audits accomplished within set quality standards", "target": 80, "formula": "(Number of audit, compliance & risk assignments accomplished as per the set quality standards during FY 2022-23/ Total number of audit, compliance, and risk assignments implemented during the FY 2022-23)*100", "score": 100, "old_team_obj_id": 99, "status": 1},
            {"old_id": 380, "name": "Proportion of investigations achieved per schedule", "target": 80, "formula": "(Number of investigations executed during the FY 2022-23/ Total number of investigations scheduled in the FY 2022-23)*100", "score": 100, "old_team_obj_id": 100, "status": 1},
            {"old_id": 381, "name": "Percentage of audit assignments/reports wit status updates on agreed actions", "target": 80, "formula": "(Number of audit assignments with status updates on actions /Total Number of scheduled audit report for follow up up)*100", "score": 0, "old_team_obj_id": 101, "status": 1},
            {"old_id": 382, "name": "Proportion of scheduled team outputs accomplished", "target": 80, "formula": "(Number of assignments accomplished/ Total number of planned assignments as per the workplan)*100", "score": 79, "old_team_obj_id": 102, "status": 1},
            {"old_id": 384, "name": "Resolution of IT&S Customer Issues", "target": 90, "formula": "Satisfaction Score", "score": 77, "old_team_obj_id": 148, "status": 1},
            {"old_id": 385, "name": "Commission Cyber Readiness index", "target": 75, "formula": "Commission Cyber Readiness index", "score": 0, "old_team_obj_id": 302, "status": 1},
            {"old_id": 386, "name": "Implementation of sector cyber security strategy", "target": 20, "formula": "Implementation of sector cyber security strategy", "score": 0, "old_team_obj_id": 302, "status": 1},
            {"old_id": 389, "name": "Percentage of Team processes and policies Reviewed", "target": 90, "formula": "(Number of Team processes and policies Reviewed/Total Number planned for review)*100", "score": 95, "old_team_obj_id": 304, "status": 1},
            {"old_id": 390, "name": "Proportion of digitised information", "target": 80, "formula": "(Number of Digitized information/Total Number of Physical information Received)*100", "score": 83, "old_team_obj_id": 190, "status": 1},
            {"old_id": 391, "name": "Percentage of querries responded to as per the charter", "target": 80, "formula": "(Number of querries responded to as per the charter/Total Number of Queries received)*100", "score": 100, "old_team_obj_id": 149, "status": 1},
            {"old_id": 392, "name": "Percentage of databases compiled within specified time", "target": 80, "formula": "(Number of databases compiled within the specified time/Total Number of databases set out to be done)*100", "score": 75, "old_team_obj_id": 149, "status": 1},
            {"old_id": 393, "name": "Proportion of information disseminated by the R&SD division versus studies conducted", "target": 80, "formula": "(Number of research studies conducted and disseminated/Total Number of studies conducted)*100", "score": 86, "old_team_obj_id": 174, "status": 1},
            {"old_id": 394, "name": "Percentage of available quarterly reports of competition market scans undertaken", "target": 50, "formula": "(Number of competition market scan reports presented to TMT in a year/Total Number of planned Market reports)*100", "score": 45, "old_team_obj_id": 306, "status": 1},
            {"old_id": 395, "name": "Percentage of competition related complaints resolved within 45 working days", "target": 85, "formula": "(Number of complaints for which an opinion was issued to the Legal Department in the set time/total number of competition related complaints received)*100", "score": 80, "old_team_obj_id": 307, "status": 1},
            {"old_id": 399, "name": "Percentage of Expenditure Unit Staff scoring above 70%", "target": 70, "formula": "(Number of Unit staff scoring above 70%/Total Number of staff in the unit)*100", "score": 100, "old_team_obj_id": 274, "status": 1},
            {"old_id": 400, "name": "Percentage of items procured within the budget", "target": 95, "formula": "(Number of items that were procured within budget/Total number of items in the Estates & Administration Expenditure budget)*100", "score": 88, "old_team_obj_id": 308, "status": 1},
            {"old_id": 401, "name": "Percentage of contracts that are renewed on time (4 months before individual tracker Renewal)", "target": 95, "formula": "(Number of contracts that are renewed on time/Total number of expected contracts to be renewed)*100", "score": 65, "old_team_obj_id": 309, "status": 1},
            {"old_id": 402, "name": "Percentage of amount spent within budget", "target": 90, "formula": "(Amount spent/Amount budgeted)*100", "score": 74, "old_team_obj_id": 310, "status": 1},
            {"old_id": 403, "name": "Percentage of technical evaluations for Licenses completed", "target": 83, "formula": "(Number of technical evaluations for licences completed in line with the department charter/Total number of license applications received) *100", "score": 92, "old_team_obj_id": 311, "status": 1},
            {"old_id": 404, "name": "Percentage of Spectrum applications processed in line with the department charter", "target": 85, "formula": "(Number of Spectrum Applications processed in line with service charter (Aircrafts, Amateur and VSATs)/total number of license applications received) *100", "score": 92, "old_team_obj_id": 312, "status": 1},
            {"old_id": 405, "name": "Percentage of SMD tools utilisation as per agreed criteria", "target": 80, "formula": "Average Availability Score = (FSQ[1]1+ FSQ2+ FSQ3+ FSQ4)/4(Number of SMD tools utilised as per agreed criteria/Total number of tools)*100", "score": 92, "old_team_obj_id": 313, "status": 1},
            {"old_id": 406, "name": "Percentage of applications (resources & type approval) processed in line with the department charter", "target": 85, "formula": "(Number of applications (resources & type approvals) processed/Total resources received in line with the department charter)*100", "score": 96, "old_team_obj_id": 314, "status": 1},
            {"old_id": 407, "name": "Percentage of operators with information on compliance status not more than six months old", "target": 85, "formula": "(Number of operators with updated information at that time/total number of operators at the time of evaluation)*100", "score": 0, "old_team_obj_id": 315, "status": 1},
            {"old_id": 408, "name": "Improve timeliness of CIS BusinessProcesses", "target": 80, "formula": "(Number of CIS workplan activities implemented as scheduled/total number of CIS workplan activities planned) *100", "score": 83, "old_team_obj_id": 316, "status": 1},
        ]

        team_kpis_created = 0
        team_kpis_skipped = 0
        kpi_scores_created = 0

        for kpi_data in team_kpis_data:
            # Get team objective using old team_objective_id
            team_objective = old_team_obj_id_to_team_obj.get(kpi_data["old_team_obj_id"])
            if not team_objective:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Skipping Team KPI '{kpi_data['name']}' - team objective ID {kpi_data['old_team_obj_id']} not found")
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
                        "notes": f"Initial value from legacy data (old measure ID: {kpi_data.get('old_id', 'N/A')})",
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