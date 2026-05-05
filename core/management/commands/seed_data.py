from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from core.models import User, Role, Department, Major

class Command(BaseCommand):
    help = 'Seed initial data using built-in auth permissions and Directorate role'

    def handle(self, *args, **options):
        self.stdout.write('Starting strictly organized seed process...')

        # Use a transaction to ensure database integrity
        with transaction.atomic():
            
            # 1. Departments - Fixed naming and unique IDs
            departments_data = [
                ("DIRECTORATE", "Directorate Office"),
                ("ADMISSIONS", "Admissions Department"),
                ("HR", "Human Resources"),
                ("FINANCE", "Finance Department"),
                ("EXAM", "Examination Department"),
                ("PLANNING", "Planning Department"),
                ("OPERATION", "Operation Department"),
            ]
            
            depts = {}
            for code, name in departments_data:
                dept, _ = Department.objects.update_or_create(
                    name=code,
                    defaults={'id': f'DEP-{code}'}
                )
                depts[code] = dept
            self.stdout.write('Departments seeded.')

            # 2. Roles - Bridging custom roles to auth.Permission
            # We look up by SLUG now to prevent IntegrityErrors if you rename the Name
            roles_config = [
                ("Directorate", "directorate-admin"),
                ("Admissions", "admission-staff"),
                ("HR Staff", "hr-staff"),
                ("Finance Staff", "finance-staff"),
                ("Exam Staff", "exam-staff"),
                ("Operation Staff", "operation-staff"),
                ("General Staff", "general-staff"),
            ]
            
            roles = {}
            for name, slug in roles_config:
                role, created = Role.objects.get_or_create(
                    name=name,
                    defaults={'slug': slug}
                )
                roles[name] = role
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created role: {name}'))

            self.stdout.write('Roles seeded.')

            # 3. Permissions Assignment Logic
            def assign_perms(role_obj, model_name, actions):
                """Helper to link real Django permissions to our Role model."""
                try:
                    # ContentType is the link between strings and database models
                    ct = ContentType.objects.get(app_label='core', model=model_name.lower())
                    for action in actions:
                        codename = f"{action}_{model_name.lower()}"
                        perm = Permission.objects.get(content_type=ct, codename=codename)
                        role_obj.permissions.add(perm)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Notice: Could not assign {action} {model_name}: {e}"))

            # Assigning keys to the bundles (Roles)
            dir_role = roles["Directorate"]
            # Directorate gets full CRUD on core business logic
            for model in ["user", "department", "role", "major", "student", "enrollment", "dropout", "enquiry", "intake"]:
                assign_perms(dir_role, model, ["add", "change", "delete", "view"])

            # Admissions Role permissions
            for model in ["student", "enrollment", "dropout", "enquiry", "major"]:
                assign_perms(roles["Admissions"], model, ["add", "change", "delete", "view"])
            
            # Exam Role permissions
            for model in ["intake"]:
                assign_perms(roles["Exam Staff"], model, ["add", "change", "delete", "view"])
            
            # assign_perms(, "department", ["view"])Exam Staff

            # 4. Majors
            majors_data = [
                ('Computer Science', 'CS', 'Computing and Software Systems'),
                ('Business', 'BE', 'Strategic Management and Finance'),
                ('Architecture', 'AR', 'Sustainable Design'),
            ]
            for name, code, desc in majors_data:
                Major.objects.update_or_create(
                    code=code,
                    defaults={'id': f'MAJ-{code}', 'name': name, 'description': desc}
                )
            self.stdout.write('Majors seeded.')

            # 5. Users - Connecting everything together
            users_data = [
                {
                    'username': 'yma',
                    'full_name': 'Yan Myo Aung',
                    'email': 'yma@sti.edu.mm',
                    'role': 'Directorate',
                    'dept': 'DIRECTORATE',
                    'is_admin': True
                },
                {
                    'username': 'admission_staff',
                    'full_name': 'U Myat Kyaw',
                    'email': 'admission@sti.edu.mm',
                    'role': 'Admissions',
                    'dept': 'ADMISSIONS',
                    'is_admin': False
                }
            ]

            for u in users_data:
                user = User.objects.filter(username=u['username']).first()
                if not user:
                    user = User.objects.create_user(
                        username=u['username'],
                        email=u['email'],
                        password='password123',
                        full_name=u['full_name']
                    )
                
                user.is_staff = u['is_admin']
                user.is_superuser = u['is_admin']
                user.role = roles[u['role']]
                user.department = depts[u['dept']]
                user.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded with Directorate role and full permissions.'))