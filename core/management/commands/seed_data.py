from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from core.models import User, Role, Department, Major, Semester, Year, Subject, SemesterSubject

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
            for model in ["user", "department", "role", "major", "student", "enrollment", "dropout", "enquiry", "intake", "exam", "subject", "semester", "exampaper", "examresult"]:
                assign_perms(dir_role, model, ["add", "change", "delete", "view"])

            # Admissions Role permissions
            for model in ["student", "enrollment", "dropout", "enquiry", "major"]:
                assign_perms(roles["Admissions"], model, ["add", "change", "delete", "view"])
            assign_perms(roles["Admissions"], "intake", ["view"])
            assign_perms(roles["Finance Staff"], "student", ["view"]) #72 44 72
            assign_perms(roles["Finance Staff"], "intake", ["view"]) 
            assign_perms(roles["Finance Staff"], "schoolfee", ["view", "add"]) 
            
            # Exam Role permissions
            for model in ["intake", "exam", "student", "subject", "exampaper", "examresult"]:
                assign_perms(roles["Exam Staff"], model, ["add", "change", "delete", "view"])

            # 4. Majors
            majors_data = [
                ('Computer Science', 'CS', 'Computing and Software Systems'),
            ]
            
            majors = {}
            for name, code, desc in majors_data:
                major, _ = Major.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': name, 
                        'description': desc
                    }
                )
                majors[code] = major # Store object, not just ID
            self.stdout.write('Majors seeded.')

            # 5. Subjects (Independent Core Data)
            subjects_data = [
                ('Programming 101', 'CS101', 'Introduction to Programming'),
                ('Data Structures', 'CS102', 'Fundamental Data Structures'),
            ]
            
            subjects = {}
            for name, code, desc in subjects_data:
                subject, _ = Subject.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': name,
                        'description': desc
                    }
                )
                subjects[code] = subject
            self.stdout.write('Subjects seeded.')
        
            # 6. Years
            # Structure: (Major_Code, Year_Name, Year_Number, Type)
            year_config = [
                ('CS', 'Year-1', 1, 'FOUNDATION'),
                ('CS', 'Year-2', 2, 'NORMAL'),
            ]
    
            years = {}
            for m_code, y_name, y_num, y_type in year_config:
                year, _ = Year.objects.get_or_create(
                    major=majors[m_code], # Pass the actual Major instance
                    yearNumber=y_num,
                    defaults={
                        'name': y_name, 
                        'type': y_type
                    }
                )
                years[f"{m_code}-{y_num}"] = year
            self.stdout.write('Years seeded.')

            # Semesters
            # Structure: (Year_Key, Sem_Number, Sem_Name)
            semester_data = [
                ('CS-1', 1, 'SEMESTER 1'),
                ('CS-1', 1, 'SEMESTER 2'),
            ]
            semesters = {}
            for y_key, s_num, s_name in semester_data:
                semester, _ = Semester.objects.get_or_create(
                    year=years[y_key], # Pass the actual Year instance
                    semester_number=s_num,
                    defaults={'name': s_name}
                )
                semesters[s_name] = semester
            self.stdout.write('Semesters seeded.')

            # semester subject
            for name, code, desc in subjects_data:
                semesterSubject, _  = SemesterSubject.objects.get_or_create(
                    semester=semesters['SEMESTER 1'],
                    subject=subjects[code]
                )

            self.stdout.write('SemesterSubject seeded.')

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
                    'username': 'admission',
                    'full_name': 'U Myat Kyaw',
                    'email': 'admission@sti.edu.mm',
                    'role': 'Admissions',
                    'dept': 'ADMISSIONS',
                    'is_admin': False
                },
                {
                    'username': 'finance',
                    'full_name': 'U Myat Kyaw',
                    'email': 'finance@sti.edu.mm',
                    'role': 'Finance Staff',
                    'dept': 'FINANCE',
                    'is_admin': False
                },
                {
                    'username': 'exam',
                    'full_name': 'Ma Shwe Yee',
                    'email': 'exam@sti.edu.mm',
                    'role': 'Exam Staff',
                    'dept': 'EXAM',
                    'is_admin': False
                }
            ]

            for u in users_data:
                user = User.objects.filter(username=u['username']).first()
                if not user:
                    user = User.objects.create_user(
                        username=u['username'],
                        email=u['email'],
                        password='password',
                        full_name=u['full_name']
                    )
                
                user.is_staff = u['is_admin']
                user.is_superuser = u['is_admin']
                user.role = roles[u['role']]
                user.department = depts[u['dept']]
                user.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded with Directorate role and full permissions.'))