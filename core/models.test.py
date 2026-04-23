from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .utils import generate_id  # Ensure this utility is in your utils.py

# ==========================================
# BASE & AUTH MODELS
# ==========================================

class BaseIDModel(models.Model):
    """Abstract base to handle custom ID generation and timestamps for all models."""
    id = models.CharField(primary_key=True, max_length=20, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class User(AbstractUser, BaseIDModel):
    """Custom user model with role-based access control."""
    ROLE_CHOICES = [('admin', 'admin'), ('staff', 'staff')]
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')
    email = models.EmailField(unique=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('U', User)
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'users'

# ==========================================
# ACADEMIC STRUCTURE (SOP: Preparation for New Class)
# ==========================================

class Major(BaseIDModel):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('MAJ', Major)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Year(BaseIDModel):
    major = models.ForeignKey(Major, on_delete=models.CASCADE, related_name='years')
    name = models.CharField(max_length=255)
    yearNumber = models.IntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ('major', 'yearNumber')
        ordering = ['yearNumber']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('Y', Year)
        super().save(*args, **kwargs)

class Semester(BaseIDModel):
    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='semesters')
    semester_number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=50) # Fall, Spring, Summer

    class Meta:
        unique_together = ('year', 'semester_number')
        ordering = ['semester_number']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('SEM', Semester)
        super().save(*args, **kwargs)

class Intake(BaseIDModel):
    code = models.CharField(max_length=20)
    major = models.ForeignKey(Major, on_delete=models.CASCADE)
    start_date = models.DateField()
    capacity = models.PositiveIntegerField()
    
    # SOP: Preparation for New Class tracking
    academic_calendar_received = models.BooleanField(default=False)
    timetable_received = models.BooleanField(default=False)
    textbooks_ordered = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('INT', Intake)
        super().save(*args, **kwargs)

# ==========================================
# STUDENT & ENROLLMENT (SOP: Induction & Data Verification)
# ==========================================

class Student(BaseIDModel):
    full_name = models.CharField(max_length=255)
    nrc = models.CharField(max_length=50)
    student_phone_no = models.CharField(max_length=50)
    parent_name = models.CharField(max_length=255)
    parent_phone_no = models.CharField(max_length=50)
    email = models.EmailField()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('STU', Student)
        super().save(*args, **kwargs)

class Enrollment(models.Model):
    """Links Student to Intake and tracks SOP requirements like ID cards."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='Enrolled')
    
    # SOP: Induction requirements
    contract_signed = models.BooleanField(default=False)
    id_card_ordered = models.BooleanField(default=False)
    id_card_issued = models.BooleanField(default=False)
    
    # SOP: Induction Verification
    parent_present_at_induction = models.BooleanField(default=False)
    student_present_at_induction = models.BooleanField(default=False)

# ==========================================
# DOCUMENT WORKFLOW (SOP: Recommendation & Transcripts)
# ==========================================

class DocumentRequest(BaseIDModel):
    """Supports 'Applying Letter of Recommendation/Transcript' SOP."""
    TYPE_CHOICES = [('REC', 'Recommendation'), ('TRN', 'Transcript'), ('CRT', 'Certificate')]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    
    # Approval Flow
    finance_approved = models.BooleanField(default=False)
    admin_ref_number = models.CharField(max_length=50, blank=True, help_text="Reference number from Admin Dept")
    
    # Collection tracking
    is_collected = models.BooleanField(default=False)
    date_ready = models.DateField(null=True, blank=True)
    follow_up_needed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('REQ', DocumentRequest)
        
        # SOP Logic: If not collected within 14 days of being ready, flag for follow-up
        if self.date_ready and not self.is_collected:
            if timezone.now().date() > (self.date_ready + timedelta(days=14)):
                self.follow_up_needed = True
        
        super().save(*args, **kwargs)

# ==========================================
# ACADEMIC MONITORING (SOP: Overseas Records L6-7)
# ==========================================

class OverseasRecord(BaseIDModel):
    """Tracks certificates and transcripts coming from Partner Universities."""
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    waybill_number = models.CharField(max_length=100)
    document_types = models.CharField(max_length=255, help_text="e.g. Certificate, Award Letter")
    received_from_partner_date = models.DateField()
    scanned_copy = models.FileField(upload_to='overseas_docs/', null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id('OVR', OverseasRecord)
        super().save(*args, **kwargs)

# ==========================================
# NOTIFICATIONS
# ==========================================

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']