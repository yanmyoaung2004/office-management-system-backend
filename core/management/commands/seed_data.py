"""Seed initial data for development with RBAC system support."""
from django.core.management.base import BaseCommand
from core.models import User, Role, RolePermission, Department, Major
from datetime import date


class Command(BaseCommand):
    help = 'Seed initial data for development including RBAC system'

    def handle(self, *args, **options):
        self.stdout.write('Seeding initial data with RBAC system...')

        # Create departments
        departments_data = [
            ("DERECTORATE", "Directors Of all Department"), # Replaced Executive            
            ("ADMISSIONS", "Admissions Department"),
            ("HR", "Human Resources"),
            ("FINANCE", "Finance Department"),
            ("EXAM", "Examination Department"),
            ("PLANNING", "Planning Department"),
            ("OPERATION", "Operation Department"),
        ]

        departments = {}
        for code, name in departments_data:
            department, created = Department.objects.get_or_create(
                name=code,
                defaults={'id': f'DEP-{code[:2]}'}
            )
            departments[code] = department
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created department: {name}'))

        # Create RBAC roles
        roles_data = [
            ("Directorate", "Executive-director", "Full access to all system features"),
            ("Admissions", "admission-staff", "Admissions department access"),
            ("HR Staff", "hr-staff", "Human Resources department limited access"),
            ("Finance Staff", "finance-staff", "Finance department access"),
            ("Exam Staff", "exam-staff", "Examination department access"),
            ("Operation Staff", "operation-staff", "Operation department access"),
            ("General Staff", "general-staff", "General office staff access"),
        ]

        roles = {}
        for name, slug, description in roles_data:
            role, created = Role.objects.get_or_create(
                name=name,
                defaults={'slug': slug}
            )
            roles[name] = role
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created role: {name}'))

        # Create RBAC permissions for Admin role
        admin_role = roles["Directorate"]
        admin_permissions = [
            # Student management
            ("student", "view"), ("student", "create"), ("student", "update"), ("student", "delete"),
            # Enquiry management
            ("enquiry", "view"), ("enquiry", "create"), ("enquiry", "update"), ("enquiry", "delete"),
            # Finance management
            ("finance", "view"), ("finance", "create"), ("finance", "update"), ("finance", "approve"),
            # Exam management
            ("exam", "view"), ("exam", "create"), ("exam", "update"), ("exam", "approve"),
            # User management
            ("user", "view"), ("user", "create"), ("user", "update"), ("user", "delete"),
            # Report management
            ("report", "view"), ("report", "create"), ("report", "update"), ("report", "delete"),
            # Operation management
            ("operation", "view"), ("operation", "create"), ("operation", "update"), ("operation", "delete"),
        ]

        for module, action in admin_permissions:
            permission, created = RolePermission.objects.get_or_create(
                role=admin_role,
                module=module,
                action=action
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {action} {module}'))

        # Create users with RBAC roles
        users_data = [
            {
                'username': 'yma',
                'password': 'password',
                'full_name': 'Yan Myo Aung',
                'email': 'yma@sti.edu.mm',
                'role': 'Directorate',
                'department': 'DERECTORATE',
                'is_superuser': True,
            },
             {
                'username': 'admission',
                'password': 'password',
                'full_name': 'U Myat Kyaw',
                'email': 'admission@sti.edu.mm',
                'role': 'Admissions',
                'department': 'ADMISSIONS',
                'is_superuser': False,
            },
            {
                'username': 'hr',
                'password': 'password',
                'full_name': 'U Hla Oo',
                'email': 'hr@sti.edu.mm',
                'role': 'HR Staff',
                'department': 'HR',
                'is_superuser': False,
            },
            {
                'username': 'finance',
                'password': 'password',
                'full_name': 'Daw Mya',
                'email': 'finance@sti.edu.mm',
                'role': 'Finance Staff',
                'department': 'FINANCE',
                'is_superuser': False,
            },
            {
                'username': 'exam',
                'password': 'password',
                'full_name': 'U Ko Ko',
                'email': 'exam@sti.edu.mm',
                'role': 'Exam Staff',
                'department': 'EXAM',
                'is_superuser': False,
            },
            {
                'username': 'operation',
                'password': 'password',
                'full_name': 'U Ko Ko',
                'email': 'operation@sti.edu.mm',
                'role': 'Operation Staff',
                'department': 'OPERATION',
                'is_superuser': False,
            },
        ]

        for user_data in users_data:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    full_name=user_data['full_name'],
                    is_superuser=user_data['is_superuser'],
                    is_staff=user_data['is_superuser']
                )
                user.role = roles[user_data['role']]
                user.department = departments[user_data['department']]
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created user: {user_data["username"]} ({user_data["full_name"]})'
                    )
                )
            else:
                self.stdout.write(f'User {user_data["username"]} already exists')

        # Create majors
        majors_data = [
            ('Computer Science', 'CS', 'Computing, AI, and Software Systems Development'),
            ('Public Health', 'PH', 'Global Health, Epidemiology, and Community Wellness'),
            ('Business', 'BE', 'Strategic Management, Finance, and Entrepreneurship'),
            ('Architectural Engineering', 'AE', 'Sustainable Building Systems and Design'),
            ('Civil Engineering', 'CE', 'Infrastructure Design, Urban Planning, and Structural Engineering'),
        ]

        for name, code, desc in majors_data:
            major, created = Major.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': desc, 'id': f'MAJ-{code}'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created major: {name}'))

        # Create RBAC permissions for HR staff
        hr_role = roles["HR Staff"]
        hr_permissions = [
            ("student", "view"), ("student", "create"), ("student", "update"),
            ("enquiry", "view"), ("enquiry", "create"), ("enquiry", "update"),
            ("report", "view"), ("report", "create"),
        ]

        for module, action in hr_permissions:
            permission, created = RolePermission.objects.get_or_create(
                role=hr_role,
                module=module,
                action=action
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created HR permission: {action} {module}'))

        # Create RBAC permissions for Finance staff
        finance_role = roles["Finance Staff"]
        finance_permissions = [
            ("student", "view"),
            ("finance", "view"), ("finance", "create"),
            ("report", "view"), ("report", "create"),
        ]

        for module, action in finance_permissions:
            permission, created = RolePermission.objects.get_or_create(
                role=finance_role,
                module=module,
                action=action
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Finance permission: {action} {module}'))

        # Create RBAC permissions for Exam staff
        exam_role = roles["Exam Staff"]
        exam_permissions = [
            ("student", "view"),
            ("exam", "view"), ("exam", "create"),
            ("report", "view"), ("report", "create"),
        ]

        for module, action in exam_permissions:
            permission, created = RolePermission.objects.get_or_create(
                role=exam_role,
                module=module,
                action=action
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Exam permission: {action} {module}'))

        # Create RBAC permissions for Operation staff
        operation_role = roles["Operation Staff"]
        operation_permissions = [
            ("student", "view"),
            ("operation", "view"), ("operation", "create"), ("operation", "update"), ("operation", "delete"),
            ("report", "view"), ("report", "create"),
        ]

        for module, action in operation_permissions:
            permission, created = RolePermission.objects.get_or_create(
                role=operation_role,
                module=module,
                action=action
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Operation permission: {action} {module}'))

        self.stdout.write(self.style.SUCCESS('\nSeed complete! RBAC system ready with:'))
        self.stdout.write('  - 5 departments created')
        self.stdout.write('  - 5 roles created')
        self.stdout.write('  - 5 different user types (admin, HR, finance, exam, operation)')
        self.stdout.write('  - Role-based permissions assigned')
        self.stdout.write('  - 5 majors created')
        self.stdout.write('\nAdmin credentials: yma/ymanig')
        self.stdout.write('HR credentials: hr_staff/hr123')
        self.stdout.write('Finance credentials: finance_staff/finance123')
        self.stdout.write('Exam credentials: exam_staff/exam123')