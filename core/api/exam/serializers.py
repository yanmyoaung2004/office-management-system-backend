from rest_framework import serializers
from core.models import Exam, ExamPaper, Semester, Major, Intake, Subject, ExamResult, Student, Enrollment
from django.db import transaction



class ExamPaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamPaper
        fields = ['id', 'subject', 'duration', 'type', 'total_marks', 'exam_date']

class ExamCreateSerializer(serializers.ModelSerializer):
    papers = ExamPaperSerializer(many=True)

    class Meta:
        model = Exam
        fields = ['id', 'title', 'semester', 'date_started', 'papers', 'intake']

    def create(self, validated_data):
        papers_data = validated_data.pop('papers')
        exam = Exam.objects.create(**validated_data)
        for paper_data in papers_data:
            ExamPaper.objects.create(exam=exam, **paper_data)
            
        return exam
    def update(self, instance, validated_data):
        papers_data = validated_data.pop('papers', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if papers_data is not None:
            instance.papers.all().delete()
            for paper_data in papers_data:
                ExamPaper.objects.create(exam=instance, **paper_data)

        return instance

class SubjectMinimalSerializer(serializers.ModelSerializer):
    """Provides a concise view of subjects linked to a semester."""
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code']    

class IntakeSemesterScheduleSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    semester_id = serializers.CharField(max_length=20)
    semester_name = serializers.CharField(source='semester.name', read_only=True)
    year = serializers.CharField(source='semester.year.name', read_only=True)
    subjects = serializers.SerializerMethodField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def get_subjects(self, obj):
        """
        Retrieves subjects associated with the semester.
        Note: Ensure 'obj' is the schedule instance that has access to the semester.
        """
        semester = obj.semester if hasattr(obj, 'semester') else None
        if semester:
            return SubjectMinimalSerializer(semester.subjects.all(), many=True).data
        return []
    
    def validate(self, data):
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError("end_date must be after start_date")
        if not Semester.objects.filter(id=data['semester_id']).exists():
            raise serializers.ValidationError(f"Semester {data['semester_id']} does not exist")
        
        return data    


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

class ExamPaperListSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')

    class Meta:
        model = ExamPaper
        fields = ['id', 'subject', 'subject_name', 'duration', 'type', 'total_marks', 'exam_date']

class ExamListSerializer(serializers.ModelSerializer):
    # 'papers' matches the related_name in your ForeignKey
    papers = ExamPaperListSerializer(many=True, read_only=True)
    intake_name = serializers.ReadOnlyField(source='intake.name')
    semester_name = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = ['id', 'title', 'intake', 'intake_name', 'semester', 'semester_name', 'date_started', 'papers']

    def get_semester_name(self, obj):
        """Combines Year and Semester into one string."""
        if obj.semester:
            year_name = obj.semester.year.name if obj.semester.year else ""
            sem_name = obj.semester.name
            return f"{year_name} - {sem_name}"
        return "N/A"


class ExamPaperUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamPaper
        fields = ['question_file', 'total_marks', 'exam_date', 'duration', 'type']
        
    def validate_question_file(self, value):
        limit = 5 * 1024 * 1024
        if value.size > limit:
            raise serializers.ValidationError("File size too large. Max size is 5MB.")
        return value
    

class ExamResultItemSerializer(serializers.ModelSerializer):
    # We use a nested serializer for the individual students
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())

    class Meta:
        model = ExamResult
        fields = ['student', 'marks_obtained', 'status', 'remarks']

class BulkExamResultSerializer(serializers.Serializer):
    exam_paper = serializers.PrimaryKeyRelatedField(queryset=ExamPaper.objects.all())
    results = ExamResultItemSerializer(many=True)

    def create(self, validated_data):
        exam_paper = validated_data['exam_paper']
        results_data = validated_data['results']
        
        exam_results = []
        for item in results_data:
            if item['marks_obtained'] > exam_paper.total_marks:
                raise serializers.ValidationError(
                    f"Student {item['student'].id} marks exceed paper limit."
                )
                
            exam_results.append(
                ExamResult(
                    id=ExamResult.generate_custom_id(),  # CRITICAL FIX
                    exam_paper=exam_paper,
                    student=item['student'],
                    marks_obtained=item['marks_obtained'],
                    status=item['status'],
                    remarks=item.get('remarks', '')
                )
            )

        with transaction.atomic():
            return ExamResult.objects.bulk_create(exam_results)
        

        
class EnrollmentStudentMinimalSerializer(serializers.ModelSerializer):
    student_id = serializers.ReadOnlyField(source='student.id')
    fullName = serializers.ReadOnlyField(source='student.full_name')
    studentSchoolId = serializers.ReadOnlyField(source='student.school_id')
    student_roll = serializers.ReadOnlyField(source='student.roll_number')
    class Meta:
        model = Enrollment
        fields = ['id', 'student_id', 'studentSchoolId', 'fullName', 'student_roll', 'status']

