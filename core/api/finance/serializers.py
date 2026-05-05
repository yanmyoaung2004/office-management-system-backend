

"""Serializers for School Office Management API."""
from rest_framework import serializers
from core.models import Enrollment, Major, Intake, Semester


class IntakeSemesterScheduleSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    semester_id = serializers.CharField(max_length=20)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    def validate(self, data):
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError("end_date must be after start_date")
        if not Semester.objects.filter(id=data['semester_id']).exists():
            raise serializers.ValidationError(f"Semester {data['semester_id']} does not exist")
        
        return data
    


class StudentListSerializer(serializers.ModelSerializer):
    # Data from the related Student model
    studentId = serializers.ReadOnlyField(source='student.id')
    fullName = serializers.CharField(source='student.full_name', read_only=True)
    schoolId = serializers.CharField(source='student.school_id', read_only=True)
    studentPhoneNo = serializers.CharField(source='student.student_phone_no', read_only=True)
    parentPhoneNo = serializers.CharField(source='student.parent_phone_no', read_only=True)
    # Data from the related Intake model
    intakeId = serializers.ReadOnlyField(source='intake.id')
    intakeCode = serializers.CharField(source='intake.code', read_only=True)
    majorName = serializers.CharField(source='intake.major.name', read_only=True)
    # Data directly on the Enrollment model (Local fields)
    currentStatus = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            'id', 'studentId', 'schoolId', 'fullName',
            'studentPhoneNo', 'majorName', 
            'parentPhoneNo','intakeId', 'intakeCode', 'currentStatus',
        ]
    
    def get_dropout(self, obj):
        if hasattr(obj, 'dropout_record'):
            return {
                "intakeId": obj.intake.id,
                "reason": obj.dropout_record.reason,
                "remark": obj.dropout_record.remark
            }
        return None

    def get_currentStatus(self, obj):
        """Combines Year and Semester from the Intake related to this Enrollment."""
        intake = obj.intake
        if intake and intake.current_semester:
            year_name = intake.current_semester.year.name if intake.current_semester.year else ""
            sem_name = intake.current_semester.name
            return f"{year_name} - {sem_name}".strip(" - ")
        return "N/A"
    

class IntakeSerializer(serializers.ModelSerializer):
    majorId = serializers.PrimaryKeyRelatedField(
        source='major', queryset=Major.objects.all()
    )
    majorName = serializers.CharField(source='major.name', read_only=True)
    currentStatus = serializers.SerializerMethodField()
    currentSemId  = serializers.CharField(source='current_semester.id', read_only=True)
    semester_schedules = IntakeSemesterScheduleSerializer(many=True, read_only=True, source='scheduled_semesters')
    
    class Meta:
        model = Intake
        fields = [
            'id', 'code', 'majorId', 'majorName', 'year',
            'startDate', 'endDate', 'capacity', 'createdAt', 
            'currentStatus', 'currentSemId', 'enrollments',
            'semester_schedules'
        ]
        extra_kwargs = {
            'startDate': {'source': 'start_date'},
            'endDate': {'source': 'end_date'},
            'createdAt': {'source': 'created_at', 'read_only': True},
        }

    def get_currentStatus(self, obj):
        """Combines Year and Semester into one string."""
        if obj.current_semester:
            year_name = obj.current_semester.year.name if obj.current_semester.year else ""
            sem_name = obj.current_semester.name
            return f"{year_name} - {sem_name}"
        return "N/A"
