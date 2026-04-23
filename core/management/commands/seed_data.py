"""Seed initial data for development."""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from core.models import User, Major, Department, Intake, Student, Enrollment

class Command(BaseCommand):
    help = 'Seed initial data for development'

    def handle(self, *args, **options):
        self.stdout.write('Seeding data...')

        # 1. Create Departments (Based on SOP Requirements)
        deps_data = [
            ('Operations', 'OPS'),
            ('Finance', 'FIN'),
            ('Planning & Exam', 'PEX'),
            ('Administration', 'ADM'),
            ('Admission', 'ADMS'),
        ]
        departments = {}
        for name, code in deps_data:
            dept, _ = Department.objects.get_or_create(code=code, defaults={'name': name})
            departments[code] = dept
        self.stdout.write(self.style.SUCCESS('Created departments'))

        # 2. Create Admin User
        if not User.objects.filter(username='yma').exists():
            User.objects.create_superuser(
                username='yma',
                password='ymanig',
                full_name='Yan Myo Aung',
                email='yma@sti.edu.mm',
                role='ADMINISTRATOR',
                department=departments['ADM']
            )
            self.stdout.write(self.style.SUCCESS('Created admin user (yma/ymanig)'))

        # 3. Create Staff Users (Representing SOP Roles)
        staff_data = [
            ('staff_ops', 'staff123', 'Sint Sint Tun', 'ops@sti.edu.mm', 'OFFICER', 'OPS'),
            ('staff_fin', 'staff123', 'Finance Staff', 'fin@sti.edu.mm', 'ACCOUNT_MANAGER', 'FIN'),
        ]
        for uname, pwd, fname, email, role, d_code in staff_data:
            if not User.objects.filter(username=uname).exists():
                User.objects.create_user(
                    username=uname,
                    password=pwd,
                    full_name=fname,
                    email=email,
                    role=role,
                    department=departments[d_code]
                )
        self.stdout.write(self.style.SUCCESS('Created staff users'))

        # 4. Create Majors
        majors_data = [
            ('Computer Science', 'CS', 'Computing, AI, and Software Systems Development'),
            ('Public Health', 'PH', 'Global Health, Epidemiology, and Community Wellness'),
            ('Business', 'BE', 'Strategic Management, Finance, and Entrepreneurship'),
            ('Architectural Engineering', 'AE', 'Sustainable Building Systems and Design'),
            ('Civil Engineering', 'CE', 'Infrastructure Design, Urban Planning, and Structural Engineering'),
        ]
        for name, code, desc in majors_data:
            Major.objects.get_or_create(code=code, defaults={'name': name, 'description': desc})
        self.stdout.write(self.style.SUCCESS('Created majors'))

        # 5. Create Sample Intake (SOP: Preparation for New Class)
        major_cs = Major.objects.get(code='CS')
        intake, created = Intake.objects.get_or_create(
            code='2024-CS-JAN',
            defaults={
                'major': major_cs,
                'start_date': date(2024, 1, 15),
                'capacity': 50,
                'academic_calendar_received': True,
                'timetable_received': True,
                'textbooks_ordered': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created intake {intake.code}'))

        # 6. Create Sample Student and Enrollment (SOP: Induction)
        if not Student.objects.filter(email='aungkyaw@example.com').exists():
            student = Student.objects.create(
                full_name='Aung Kyaw',
                nrc='12/ABCDE(N)123456',
                student_phone_no='+95912345678',
                parent_name='U Ko Win',
                parent_phone_no='+95987654321',
                email='aungkyaw@example.com'
            )
            
            Enrollment.objects.create(
                student=student,
                intake=intake,
                status='Enrolled',
                contract_signed=True,
                id_card_ordered=True,
                parent_present_at_induction=True
            )
            self.stdout.write(self.style.SUCCESS('Created sample student & enrollment'))

        self.stdout.write(self.style.SUCCESS('Seed complete!'))