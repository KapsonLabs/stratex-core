"""
Management command to set up initial system data:
- Modules: Strategy, Reporting, Budgeting
- Sub Modules under Strategy: Perspectives, Objectives, Departments, DepartmentObjectives, Teams, Team Objectives, KPIs
- System Module Permissions for all sub modules
- Base Licence with all modules
- UCC Tenant with Base Licence
- Main Office organization
- Admin role with all permissions
- main_admin user
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth import get_user_model

from tenants.models import (
    Module,
    SubModule,
    SystemModulePermission,
    Licence,
    LicenceModule,
    Tenant,
    TenantSettings,
)
from accounts.models import Role, RolePermission
from strategy.models import Organization

User = get_user_model()


class Command(BaseCommand):
    help = "Set up initial system data: modules, submodules, permissions, licence, and tenant"

    def handle(self, *args, **options):
        self.stdout.write("Setting up initial system data...")

        # 1. Create Modules
        self.stdout.write("Creating modules...")
        strategy_module, _ = Module.objects.get_or_create(
            code="strategy",
            defaults={
                "name": "Strategy",
                "description": "Strategic planning and execution module",
                "is_active": True,
            },
        )
        reporting_module, _ = Module.objects.get_or_create(
            code="reporting",
            defaults={
                "name": "Reporting",
                "description": "Reporting and analytics module",
                "is_active": True,
            },
        )
        budgeting_module, _ = Module.objects.get_or_create(
            code="budgeting",
            defaults={
                "name": "Budgeting",
                "description": "Budget planning and management module",
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"✓ Created modules: Strategy, Reporting, Budgeting"))

        # 2. Create Sub Modules under Strategy
        self.stdout.write("Creating sub modules under Strategy...")
        strategy_submodules = [
            ("perspectives", "Perspectives", "Strategic perspectives management"),
            ("objectives", "Objectives", "Strategic objectives management"),
            ("departments", "Departments", "Department management"),
            ("department_objectives", "Department Objectives", "Department objectives management"),
            ("teams", "Teams", "Team management"),
            ("team_objectives", "Team Objectives", "Team objectives management"),
            ("kpis", "KPIs", "Key Performance Indicators management"),
        ]

        created_submodules = {}
        for code, name, description in strategy_submodules:
            submodule, created = SubModule.objects.get_or_create(
                module=strategy_module,
                name=name,
                defaults={
                    "description": description,
                    "is_active": True,
                },
            )
            created_submodules[code] = submodule
            if created:
                self.stdout.write(f"  ✓ Created submodule: {name}")

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(created_submodules)} sub modules under Strategy"))

        # 3. Create System Module Permissions for each submodule
        self.stdout.write("Creating system module permissions...")
        actions = ["create", "read", "update", "delete"]
        permissions_created = 0

        for submodule_code, submodule in created_submodules.items():
            for action in actions:
                # Generate codename from submodule name and action
                codename = f"{slugify(submodule.name).replace('-', '_')}_{action}"
                permission, created = SystemModulePermission.objects.get_or_create(
                    codename=codename,
                    defaults={
                        "resource": submodule,
                        "action": action,
                        "is_active": True,
                    },
                )
                if created:
                    permissions_created += 1

        self.stdout.write(
            self.style.SUCCESS(f"✓ Created {permissions_created} system module permissions")
        )

        # 4. Create Base Licence
        self.stdout.write("Creating Base Licence...")
        base_licence, created = Licence.objects.get_or_create(
            name="Base Licence",
            defaults={
                "is_active": True,
                "max_users": 50,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✓ Created Base Licence"))
        else:
            self.stdout.write("  Base Licence already exists")

        # 5. Create LicenceModule entries
        self.stdout.write("Linking modules to Base Licence...")
        modules_to_link = [strategy_module, reporting_module, budgeting_module]
        licence_modules_created = 0

        for module in modules_to_link:
            licence_module, created = LicenceModule.objects.get_or_create(
                licence=base_licence,
                module=module,
            )
            if created:
                licence_modules_created += 1
                self.stdout.write(f"  ✓ Linked {module.name} to Base Licence")

        self.stdout.write(
            self.style.SUCCESS(f"✓ Linked {licence_modules_created} modules to Base Licence")
        )

        # 6. Create UCC Tenant
        self.stdout.write("Creating UCC tenant...")
        ucc_tenant, created = Tenant.objects.get_or_create(
            name="UCC",
            defaults={
                "licence": base_licence,
                "is_active": True,
            },
        )
        if created:
            # Auto-generate slug
            ucc_tenant.slug = slugify(ucc_tenant.name)
            ucc_tenant.save()
            self.stdout.write(self.style.SUCCESS("✓ Created UCC tenant"))
        else:
            self.stdout.write("  UCC tenant already exists")

        # 7. Create TenantSettings for UCC
        self.stdout.write("Creating tenant settings for UCC...")
        TenantSettings.objects.get_or_create(
            tenant=ucc_tenant,
            defaults={
                "timezone": "UTC",
                "locale": "en-US",
                "theme": "light",
            },
        )
        self.stdout.write(self.style.SUCCESS("✓ Created tenant settings for UCC"))

        # 8. Create Main Office organization
        self.stdout.write("Creating Main Office organization...")
        main_office, created = Organization.objects.get_or_create(
            tenant=ucc_tenant,
            name="Main Office",
            defaults={
                "location": "Main Office",
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✓ Created Main Office organization"))
        else:
            self.stdout.write("  Main Office organization already exists")

        # 9. Create Admin role
        self.stdout.write("Creating Admin role...")
        admin_role, created = Role.objects.get_or_create(
            code="admin",
            defaults={
                "name": "Admin",
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✓ Created Admin role"))
        else:
            self.stdout.write("  Admin role already exists")

        # 10. Attach all permissions to Admin role
        self.stdout.write("Attaching permissions to Admin role...")
        all_permissions = SystemModulePermission.objects.filter(is_active=True)
        role_permissions_created = 0
        
        for permission in all_permissions:
            role_permission, created = RolePermission.objects.get_or_create(
                role=admin_role,
                permission=permission,
                defaults={
                    "is_active": True,
                },
            )
            if created:
                role_permissions_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f"✓ Attached {role_permissions_created} permissions to Admin role")
        )

        # 11. Create main_admin user
        self.stdout.write("Creating main_admin user...")
        main_admin, created = User.objects.get_or_create(
            username="main_admin",
            defaults={
                "email": "main_admin@ucc.com",
                "tenant": ucc_tenant,
                "role": admin_role,
                "organization": main_office,
                "is_active": True,
                "is_staff": True,
            },
        )
        if created:
            # Set a default password (should be changed on first login)
            main_admin.set_password("admin123")
            main_admin.save()
            self.stdout.write(self.style.SUCCESS("✓ Created main_admin user"))
            self.stdout.write(self.style.WARNING("  Default password: admin123 (please change on first login)"))
        else:
            self.stdout.write("  main_admin user already exists")

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Initial data setup completed successfully!"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Modules: {Module.objects.count()}")
        self.stdout.write(f"Sub Modules: {SubModule.objects.count()}")
        self.stdout.write(f"System Permissions: {SystemModulePermission.objects.count()}")
        self.stdout.write(f"Licences: {Licence.objects.count()}")
        self.stdout.write(f"Licence Modules: {LicenceModule.objects.count()}")
        self.stdout.write(f"Tenants: {Tenant.objects.count()}")
        self.stdout.write(f"Organizations: {Organization.objects.count()}")
        self.stdout.write(f"Roles: {Role.objects.count()}")
        self.stdout.write(f"Role Permissions: {RolePermission.objects.count()}")
        self.stdout.write(f"Users: {User.objects.count()}")
        self.stdout.write("=" * 60)

