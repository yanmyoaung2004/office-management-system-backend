"""Models for School Office Management System."""
from django.contrib.auth.models import AbstractUser
from django.db import models
from .utils import generate_id
from django.conf import settings
from django.utils import timezone
import uuid

DEPARTMENT_NAMES = [
    ('ADMIN', 'Admin'),
    ('HR', 'HR'),
    ('FINANCE', 'Finance'),
    ('EXAM', 'Exam'),
    ('PLANNING', 'Planning'),
]

USER_ROLES = [
    ('admin', 'Admin'),
    ('staff', 'Staff'),
]


class BaseIDModel(models.Model):
    """Abstract base model with custom ID field"""
    id = models.CharField(
        max_length=20,
        primary_key=True,
        editable=False,
        unique=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.id:
            # Generate ID based on model class name
            prefix = self.__class__.__name__[:2].upper()
            # This is a simplified version - in production you'd want a more robust ID generation
            self.id = f"{prefix}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class Department(BaseIDModel):
    name = models.CharField(max_length=20, choices=DEPARTMENT_NAMES, unique=True)

    def __str__(self):
        return self.get_name_display()

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"

class Role(BaseIDModel):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"


class RolePermission(BaseIDModel):
    # role = models.CharField(max_length=20, choices=USER_ROLES)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    
    module = models.CharField(max_length=50)  # student, finance, exam, etc.
    action = models.CharField(max_length=20)  # view, create, update, approve

    def __str__(self):
        return f"{self.get_role_display()} - {self.module} - {self.action}"

    class Meta:
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"
        unique_together = ('role', 'module', 'action')



class User(AbstractUser):
    """Custom user model with role and display name."""
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True, related_name='users')
    is_superuser = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('U', User)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

class Major(models.Model):
    """Major/Program of study."""
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('MAJ', Major)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Year(models.Model):
    """Academic year within a major"""
    TYPE_CHOICES = [
        ('FOUNDATION', 'Foundation'),
        ('NORMAL', 'Normal'),
    ]
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    major = models.ForeignKey(Major, on_delete=models.CASCADE, related_name='years')
    name = models.CharField(max_length=255)
    yearNumber = models.IntegerField(null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='NORMAL')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('major', 'yearNumber')
        ordering = ['yearNumber']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('Y', Year)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.major.code} - {self.name}"

class Semester(models.Model):
    """Semester within a year"""
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    year = models.ForeignKey(
        Year, on_delete=models.CASCADE, related_name='semesters'
    )
    semester_number = models.PositiveSmallIntegerField(null=True, blank=True)
    name = models.CharField(max_length=50)  # Fall, Spring, Summer
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('year', 'semester_number')
        ordering = ['semester_number']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('SEM', Semester)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.year.name} - {self.name}"

class Intake(models.Model):
    """Intake/batch for a major."""
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    code = models.CharField(max_length=20)
    major = models.ForeignKey(Major, on_delete=models.CASCADE, related_name='intakes')
    year = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    current_semester = models.ForeignKey(
        'Semester', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='current_intakes'
    )
    capacity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('INT', Intake)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.major.name}"

class IntakeSemester(models.Model):
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE, related_name='scheduled_semesters')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('intake', 'semester')
        ordering = ['start_date']
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('ISEM', IntakeSemester)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.intake.code} - {self.semester.name} ({self.start_date} to {self.end_date})"
    
class Enquiry(models.Model):
    """Student enquiry."""
    ENQUIRY_TYPE_CHOICES = [
        ('Enquiry', 'Enquiry'),
        ('Walk-in', 'Walk-in'),
        ('Phone', 'Phone'),
        ('Facebook', 'Facebook'),
    ]
    SOURCE_CHOICES = [
        ('Friend', 'Friend'),
        ('Facebook', 'Facebook'),
        ('Pamphlet', 'Pamphlet'),
        ('Newspaper', 'Newspaper'),
        ('Others', 'Others'),
    ]


    id = models.CharField(primary_key=True, max_length=20, editable=False)
    date = models.DateField()
    desired_program = models.CharField(max_length=255)
    student_name = models.CharField(max_length=255)
    education_level = models.CharField(max_length=255)
    student_contact_no = models.CharField(max_length=50)
    parent_name = models.CharField(max_length=255)
    parent_contact_no = models.CharField(max_length=50)
    address = models.TextField()
    enquiry_type = models.CharField(max_length=20, choices=ENQUIRY_TYPE_CHOICES)
    source_of_information = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    remark = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('ENQ', Enquiry)
        super().save(*args, **kwargs)

    @property
    def follow_up_count(self):
        return self.followups.count()

    def __str__(self):
        return f"{self.student_name} - {self.desired_program}"

class FollowUpSession(models.Model):
    """Follow-up session for an enquiry."""
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    enquiry = models.ForeignKey(
        Enquiry, on_delete=models.CASCADE, related_name='followups'
    )
    date = models.DateField()
    handled_by = models.CharField(max_length=255)
    walkup_followup = models.BooleanField(default=False)
    remark = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('FUP', FollowUpSession)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Follow-up {self.id} for {self.enquiry.student_name}"

class DailyReport(models.Model):
    """Daily activity report."""
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reports'
    )
    date = models.DateField()
    activities = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('R', DailyReport)
        super().save(*args, **kwargs)

    @property
    def enquiry_count(self):
        return self.report_enquiries.count()

    def __str__(self):
        return f"Report {self.id} - {self.user.full_name} - {self.date}"

class ReportEnquiry(models.Model):
    """Link between report and enquiries handled."""
    report = models.ForeignKey(
        DailyReport, on_delete=models.CASCADE, related_name='report_enquiries'
    )
    enquiry = models.ForeignKey(
        Enquiry, on_delete=models.CASCADE, related_name='report_mentions'
    )
    action = models.CharField(max_length=255)

    class Meta:
        unique_together = ['report', 'enquiry']
        verbose_name_plural = 'Report enquiries'

class Student(models.Model):
    """Core Identity: Data that stays with the person regardless of intake."""
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    school_id = models.CharField(max_length=255, unique=True)
    full_name = models.CharField(max_length=255)
    education_level = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    nrc = models.CharField(max_length=50)
    birth_date = models.DateField()
    student_phone_no = models.CharField(max_length=50)
    parent_name = models.CharField(max_length=255)
    parent_phone_no = models.CharField(max_length=50)
    email = models.EmailField()
    referral_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('STU', Student)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name

class Enrollment(models.Model):
    """Academic Instance: Data specific to a student joining a specific intake."""
    STATUS_CHOICES = [
        ('Enrolled', 'Enrolled'),
        ('Dropout', 'Dropout'),
        ('Graduated', 'Graduated'),
        ('Interrupted', 'Interrupted')
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    intake = models.ForeignKey('Intake', on_delete=models.CASCADE, related_name='enrollments')
    
    # These fields moved from Student to here to allow different values per intake
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Enrolled')
    enrolled_date = models.DateField()
    scholar = models.BooleanField(default=False)
    registration_fee = models.BooleanField(default=False)
    first_installment_fee = models.BooleanField(default=False)
    nrc_copy = models.BooleanField(default=False)
    census_copy = models.BooleanField(default=False)
    passport_photo = models.BooleanField(default=False)
    education_certificate = models.BooleanField(default=False)
    remark = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.intake.name}"

class Dropout(models.Model):

    """Event Record: Linked to a specific Enrollment, not just the student."""
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    enrollment = models.OneToOneField(
        Enrollment, on_delete=models.CASCADE, related_name='dropout_record'
    )
    dropout_date = models.DateField()
    followup_date = models.DateField()
    reason = models.CharField(max_length=255)
    remark = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('DRP', Dropout)
        super().save(*args, **kwargs)

    def create(self, validated_data):
        resulting_status = validated_data.pop('resultingStatus')
        dropout = super().create(validated_data)

        enrollment = dropout.enrollment
        enrollment.status = resulting_status
        enrollment.save(update_fields=['status'])

        return dropout


    def __str__(self):
        return f"Dropout: {self.enrollment.student.full_name}"
    
class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        null=True, blank=True
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE, 
        null=True, blank=True,
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    alert_type = models.CharField(max_length=50, default='FOLLOW_UP')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] 

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d')}"