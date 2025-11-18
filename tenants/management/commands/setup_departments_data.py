"""
Management command to set up departments and department objectives from legacy SQL data.
"""

from django.core.management.base import BaseCommand
from decimal import Decimal

from strategy.models import Organization, Objective
from departments.models import Department, DepartmentObjective, Team, KPI, TeamObjective, KPIScore


class Command(BaseCommand):
    help = "Set up departments and department objectives from legacy SQL data"

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
            {"title": "Increase Stakeholder satisfaction", "dept_name": "Legal", "composite_weight": 70, "objective_name": "Increase Communications User satisfaction", "status": "active"},
            {"title": "Strengthen Regulatory Frameworks", "dept_name": "Legal", "composite_weight": 80, "objective_name": "Improve Regulatory Processes", "status": "active"},
            {"title": "Optimize Resources", "dept_name": "Legal", "composite_weight": 80, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve Board, Legal and PDU Compliance Management", "dept_name": "Legal", "composite_weight": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve Board, Legal and PDU Process Efficiency", "dept_name": "Legal", "composite_weight": 70, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Strengthen Legal and PDU Risk Management", "dept_name": "Legal", "composite_weight": 70, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Promote use of communication services", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 11, "objective_name": "Increase Communications User satisfaction", "status": "active"},
            {"title": "Improve UCUSAF operational efficiency", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 11, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Increase project monitoring turnaround", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 80, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve project conceptualization", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 90, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve contract management", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 90, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve Resource Mobilisation and Use", "dept_name": "Finance", "composite_weight": 100, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Increase Customer & Stakeholder Satisfaction", "dept_name": "Finance", "composite_weight": 80, "objective_name": "Increase Communications User satisfaction", "status": "active"},
            {"title": "Decrease Number of Rolled Over projects", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 25, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Enhance Financial Accountability", "dept_name": "Finance", "composite_weight": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Strengthen stakeholder relationships", "dept_name": "Uganda Communications Universal Service Access Fund", "composite_weight": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve Revenue Management", "dept_name": "Finance", "composite_weight": 100, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve customer & stakeholder satisfaction", "dept_name": "Human Resources and Administration", "composite_weight": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Strengthen Expenditure Management", "dept_name": "Finance", "composite_weight": 85, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Strengthen Financial Reporting", "dept_name": "Finance", "composite_weight": 90, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Increase employee productivity", "dept_name": "Human Resources and Administration", "composite_weight": 88, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Optimize HRA resources", "dept_name": "Human Resources and Administration", "composite_weight": 95, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Enhance Planning & Budgeting", "dept_name": "Finance", "composite_weight": 100, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve DF Skills, Knowledge & Abilities", "dept_name": "Finance", "composite_weight": 100, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Improve HRA operational efficiency", "dept_name": "Human Resources and Administration", "composite_weight": 11, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Enhance UCC Business success", "dept_name": "Legal", "composite_weight": 80, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Staff Performance", "dept_name": "Legal", "composite_weight": 80, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Improve/Promote good governance", "dept_name": "Internal Audit", "composite_weight": 75, "objective_name": "Maximize Stakeholder Value", "status": "active"},
            {"title": "Improve HRA tools & Technology", "dept_name": "Human Resources and Administration", "composite_weight": 11, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Improve timely conclusion of complaints •Consumer complaints •Content complaints •Licensee disputes", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve the timely availability of information to stakeholders •Market reports •Consumer advisories •Content quota reports •Competition scans", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Reduce cost of doing business/operation", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Enhance Stakeholder Collaboration", "dept_name": "Internal Audit", "composite_weight": 75, "objective_name": "Maximize Stakeholder Value", "status": "active"},
            {"title": "Optimise Financial Resource Use", "dept_name": "Internal Audit", "composite_weight": 90, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve quality of audit services", "dept_name": "Internal Audit", "composite_weight": 80, "objective_name": "Maximize Stakeholder Value", "status": "active"},
            {"title": "Enhance UCC business process", "dept_name": "Internal Audit", "composite_weight": 70, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Strengthen coordination of Risk management", "dept_name": "Internal Audit", "composite_weight": 70, "objective_name": "Maximize Stakeholder Value", "status": "active"},
            {"title": "Improve responsiveness of the regulatory frameworks and standards", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "objective_name": "Improve Regulatory Processes", "status": "active"},
            {"title": "Improve the timeliness of DIAC's plan execution, compliance activities and assessment decisions", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "objective_name": "Improve Regulatory Processes", "status": "active"},
            {"title": "Improve IAC Tools & Technology capability for better work environment & processes •Online data portal •Digital logger •Call Centre", "dept_name": "Industry Affairs and Content", "composite_weight": 11, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Strengthen Internal Compliance Monitoring", "dept_name": "Internal Audit", "composite_weight": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve Quality of Communication services offered by Licensees", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 11, "objective_name": "Promote Sector Competitiveness", "status": "active"},
            {"title": "Improve IA Tools and Technologies", "dept_name": "Internal Audit", "composite_weight": 80, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Improve IA Skills, knowledge and Abilities", "dept_name": "Internal Audit", "composite_weight": 75, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Improve utilization of Communication Resources (Spectrum, Numbering and Electronic Addressing/LCNs)", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 80, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve the timeliness of ECI's actions, compliance activities and assessment decisions", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 83, "objective_name": "Improve Regulatory Processes", "status": "active"},
            {"title": "Improve availability of our technical tools to be used when required", "dept_name": "Engineering & Communication Infrastructure", "composite_weight": 80, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Improve customer and stakeholder satisfaction", "dept_name": "ICT & Research", "composite_weight": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve cyber security", "dept_name": "ICT & Research", "composite_weight": 60, "objective_name": "Increase Communications User satisfaction", "status": "active"},
            {"title": "Optimize ICT&R resources", "dept_name": "ICT & Research", "composite_weight": 100, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Strengthen risk Management", "dept_name": "ICT & Research", "composite_weight": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Enhance Knowledge Management", "dept_name": "ICT & Research", "composite_weight": 67, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Improve Operational efficiency", "dept_name": "ICT & Research", "composite_weight": 60, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve Tools and Technology", "dept_name": "ICT & Research", "composite_weight": 80, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Enhance Staff Performance", "dept_name": "ICT & Research", "composite_weight": 70, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
            {"title": "Enhance UCC Business success", "dept_name": "ICT & Research", "composite_weight": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Improve stakeholder awareness", "dept_name": "Corporate Affairs", "composite_weight": 70, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Enhance visibility and image of UCC Brand", "dept_name": "Corporate Affairs", "composite_weight": 80, "objective_name": "Enhance Organizational Culture", "status": "active"},
            {"title": "Enhance UCC Business Success", "dept_name": "Corporate Affairs", "composite_weight": 80, "objective_name": "Promote Sector Competitiveness", "status": "active"},
            {"title": "Minimize Budget Variance", "dept_name": "Corporate Affairs", "composite_weight": 90, "objective_name": "Optimize Resources", "status": "active"},
            {"title": "Improve Corporate Performance Reporting", "dept_name": "Corporate Affairs", "composite_weight": 80, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Enhance coordination of CA Internal stakeholders", "dept_name": "Corporate Affairs", "composite_weight": 75, "objective_name": "Strengthen Stakeholder Collaboration", "status": "active"},
            {"title": "Increase CA System & Process Efficiency", "dept_name": "Corporate Affairs", "composite_weight": 70, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Improve productivity of Corporate Affairs Staff", "dept_name": "Corporate Affairs", "composite_weight": 80, "objective_name": "Improve Staff Skills Knowledge and Abilities", "status": "active"},
            {"title": "Improve CA Tools & Technology", "dept_name": "Corporate Affairs", "composite_weight": 50, "objective_name": "Improve Tools & Technology", "status": "active"},
            {"title": "Improve Skills, Knowledge & Abilities", "dept_name": "Industry Affairs and Content", "composite_weight": 70, "objective_name": "Improve Knowledge Skills and Abilities", "status": "active"},
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
                target=dept_obj_data["title"],
                defaults={
                    "composite_weight": Decimal(str(dept_obj_data["composite_weight"])),
                    "status": status,
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

            # Create KPI with level="department" linked to department_objective
            kpi, created = KPI.objects.get_or_create(
                department_objective=dept_objective,
                name=kpi_data["name"],
                defaults={
                    "level": "department",
                    "formula": kpi_data["formula"],
                    "target_value": Decimal(str(kpi_data["target"])) if kpi_data["target"] else None,
                    "current_value": Decimal(str(kpi_data["current_value"])) if kpi_data.get("current_value") is not None else None,
                    "unit": "%",  # Most KPIs are percentages
                },
            )
            if created:
                kpis_created += 1
                self.stdout.write(f"  ✓ Created KPI: {kpi.name}")
            
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
            
            # Create team objective
            team_objective, created = TeamObjective.objects.get_or_create(
                team=team,
                dept_objective=dept_objective,
                defaults={
                    "status": status,
                },
            )
            if created:
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

            # Map status: 1 -> "On Track"
            kpi_status = "On Track" if kpi_data["status"] == 1 else "Behind"

            # Create team KPI
            kpi, created = KPI.objects.get_or_create(
                team_objective=team_objective,
                name=kpi_data["name"],
                defaults={
                    "level": "team",
                    "formula": kpi_data["formula"],
                    "target_value": Decimal(str(kpi_data["target"])) if kpi_data["target"] else None,
                    "unit": "%",
                    "status": kpi_status,
                    "owner_id": team_objective.team.lead_id if team_objective.team.lead_id else None,
                },
            )
            if created:
                team_kpis_created += 1
                self.stdout.write(f"  ✓ Created Team KPI: {kpi.name}")

            # Create KPIScore if score exists
            if kpi_data.get("score") is not None and kpi_data["score"] > 0:
                score, score_created = KPIScore.objects.get_or_create(
                    kpi=kpi,
                    value=Decimal(str(kpi_data["score"])),
                    defaults={
                        "period_label": "",  # Ignoring reporting_period_id for now
                        "notes": f"Initial score from legacy data (old measure ID: {kpi_data['old_id']})",
                    },
                )
                if score_created:
                    kpi_scores_created += 1
                    # Update KPI current_value if not set
                    if not kpi.current_value:
                        kpi.current_value = Decimal(str(kpi_data["score"]))
                        kpi.save(update_fields=["current_value"])

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
        self.stdout.write(f"Department KPIs: {KPI.objects.filter(level='department', department_objective__department__organization=organization).count()}")
        self.stdout.write(f"Team KPIs: {KPI.objects.filter(level='team', team_objective__team__department__organization=organization).count()}")
        self.stdout.write(f"KPI Scores: {KPIScore.objects.filter(kpi__team_objective__team__department__organization=organization).count()}")
        self.stdout.write("=" * 60)