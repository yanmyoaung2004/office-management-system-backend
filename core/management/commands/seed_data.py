"""Seed initial data for development."""
from django.core.management.base import BaseCommand
from core.models import User, Major


class Command(BaseCommand):
    help = 'Seed initial data for development'

    def handle(self, *args, **options):
        self.stdout.write('Seeding data...')

        # Create admin user if not exists
        if not User.objects.filter(username='yma').exists():
            User.objects.create_user(
                username='yma',
                password='ymanig',
                full_name='Yan Myo Aung',
                email='yma@sti.edu.mm',
                role='admin',
                is_superuser=True,
            )
            self.stdout.write(self.style.SUCCESS('Created admin user (yma/ymanig)'))

        # if not User.objects.filter(username='staff').exists():
        #     User.objects.create_user(
        #         username='staff',
        #         password='staff123',
        #         full_name='U Min Thu',
        #         email='minthuu@stimy.edu.mm',
        #         role='staff'
        #     )
        #     self.stdout.write(self.style.SUCCESS('Created staff user (staff/staff123)'))

        # Majors
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

        # # Intakes
        # major_cs = Major.objects.get(code='CS')
        # if not Intake.objects.filter(code='2024-01', major=major_cs).exists():
        #     Intake.objects.create(
        #         code='2024-01',
        #         major=major_cs,
        #         year=2024,
        #         start_date=date(2024, 1, 15),
        #         end_date=date(2024, 9, 15),
        #         capacity=50
        #     )
        #     self.stdout.write(self.style.SUCCESS('Created intake 2024-01'))

        # # Sample student
        # intake = Intake.objects.first()
        # if intake and not Student.objects.exists():
        #     Student.objects.create(
        #         no=1,
        #         full_name='Aung Kyaw',
        #         education_level='Tertiary',
        #         program_duration='8 Months',
        #         gender='Male',
        #         nrc='12/ABCDE(N)123456',
        #         birth_date=date(1998, 5, 15),
        #         program='Computer Science',
        #         student_phone_no='+260-96-555-1001',
        #         parent_name='U Ko Win',
        #         parent_phone_no='+260-96-555-1002',
        #         email='aungkyaw@example.com',
        #         total_school_fee=500000,
        #         enrolled_date=date(2024, 9, 1),
        #         major=intake.major,
        #         intake=intake,
        #         nrc_copy=True,
        #         census_copy=True,
        #         passport_photo=True,
        #         referral_name='Ma Soe',
        #         birth_month=5,
        #         remark='Excellent student'
        #     )
        #     self.stdout.write(self.style.SUCCESS('Created sample student'))

        # # Sample enquiry
        # if not Enquiry.objects.exists():
        #     eq = Enquiry.objects.create(
        #         date=date(2024, 10, 15),
        #         desired_program='Computer Science',
        #         student_name='Aung Kyaw',
        #         education_level='Tertiary',
        #         student_contact_no='+260-96-555-1001',
        #         parent_name='U Ko Win',
        #         parent_contact_no='+260-96-555-1002',
        #         address='123 Yangon Street, Yangon',
        #         enquiry_type='Walk-in',
        #         source_of_information='Friend',
        #         remark='Promising candidate'
        #     )
        #     FollowUpSession.objects.create(
        #         enquiry=eq,
        #         date=date(2024, 10, 22),
        #         handled_by='Ma Thidar',
        #         walkup_followup=True,
        #         remark='Student interested, shared program details'
        #     )
        #     self.stdout.write(self.style.SUCCESS('Created sample enquiry and follow-up'))

        self.stdout.write(self.style.SUCCESS('Seed complete!'))