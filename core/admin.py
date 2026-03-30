from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Major, Intake, Student, Enquiry,
    FollowUpSession, DailyReport, ReportEnquiry, Dropout, Enrollment, Notification
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['id', 'username', 'full_name', 'email', 'role']
    list_filter = ['role']
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('full_name', 'role')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('full_name', 'email', 'role')}),
    )


@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code']


@admin.register(Intake)
class IntakeAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'major', 'year', 'start_date', 'end_date', 'capacity']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    # REMOVE 'status' and 'intake' from here
    list_display = ('id', 'full_name', 'get_status', 'get_intake') 

    def get_status(self, obj):
        # Reach into the related enrollment
        last_enrollment = obj.enrollments.order_by('-created_at').first()
        return last_enrollment.status if last_enrollment else "No Enrollment"
    get_status.short_description = 'Status'

    def get_intake(self, obj):
        last_enrollment = obj.enrollments.order_by('-created_at').first()
        return last_enrollment.intake if last_enrollment else "N/A"
    get_intake.short_description = 'Intake'


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ['id', 'student_name', 'desired_program', 'enquiry_type', 'date']


@admin.register(FollowUpSession)
class FollowUpSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'enquiry', 'date', 'handled_by']


class ReportEnquiryInline(admin.TabularInline):
    model = ReportEnquiry
    extra = 1


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'date', 'enquiry_count']
    inlines = [ReportEnquiryInline]


# @admin.register(Dropout)
# class DropoutAdmin(admin.ModelAdmin):
#     list_display = ['id', 'student', 'dropout_date', 'reason']

@admin.register(Dropout)
class DropoutAdmin(admin.ModelAdmin):
    # Change 'student' to 'get_student' or 'enrollment'
    list_display = ('id', 'get_student', 'dropout_date', 'reason')

    def get_student(self, obj):
        return obj.enrollment.student.full_name
    get_student.short_description = 'Student'

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'intake', 'status', 'enrolled_date')
    list_filter = ('status', 'intake')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_read', 'created_at')
    list_filter = ('is_read', 'alert_type')
    search_fields = ('message', 'student__first_name', 'student__last_name')