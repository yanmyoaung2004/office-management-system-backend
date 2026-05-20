from datetime import timedelta
from rest_framework import serializers
from core.models import Exam, ExamPaper, Semester, Major, Intake, Subject, ExamResult, ExamResultShareLink, Student, Enrollment
from django.db import transaction
from django.utils import timezone



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
            with transaction.atomic():
                incoming_ids = {p['subject'].pk for p in papers_data}

                for paper in instance.papers.all():
                    if paper.subject_id not in incoming_ids and not paper.results.exists():
                        paper.delete()

                for paper_data in papers_data:
                    subject = paper_data['subject']
                    existing = instance.papers.filter(subject=subject).first()
                    if existing:
                        for attr, val in paper_data.items():
                            if attr not in ('id', 'subject'):
                                setattr(existing, attr, val)
                        existing.save()
                    else:
                        ExamPaper.objects.create(
                            exam=instance,
                            subject=subject,
                            duration=paper_data.get('duration'),
                            type=paper_data.get('type'),
                            total_marks=paper_data.get('total_marks', 100),
                            exam_date=paper_data.get('exam_date'),
                        )

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
    # Use SlugRelatedField to look up by school_id instead of the database PK
    student = serializers.SlugRelatedField(
        slug_field='school_id',
        queryset=Student.objects.all()
    )

    class Meta:
        model = ExamResult
        fields = ['student', 'marks_obtained', 'status', 'remarks']
        
class BulkExamResultSerializer(serializers.Serializer):
    exam_paper = serializers.PrimaryKeyRelatedField(queryset=ExamPaper.objects.all())
    results = ExamResultItemSerializer(many=True)

    def create(self, validated_data):
        exam_paper = validated_data['exam_paper']
        results_data = validated_data['results']

        created = []
        updated = []

        with transaction.atomic():
            for item in results_data:
                if item['marks_obtained'] > exam_paper.total_marks:
                    raise serializers.ValidationError(
                        f"Student {item['student'].id} marks exceed paper limit."
                    )

                result, is_new = ExamResult.objects.update_or_create(
                    exam_paper=exam_paper,
                    student=item['student'],
                    defaults={
                        'marks_obtained': item['marks_obtained'],
                        'status': item['status'],
                        'remarks': item.get('remarks', ''),
                    }
                )
                if is_new:
                    created.append(result)
                else:
                    updated.append(result)

        verb = "Created" if created else "Updated"
        return {**validated_data, '_created': created, '_updated': updated}
        
        

class ExamPaperResultInfoSerializer(serializers.Serializer):
    id = serializers.CharField()
    subject_name = serializers.CharField()
    duration = serializers.DurationField()
    type = serializers.CharField()
    total_marks = serializers.IntegerField()
    exam_date = serializers.DateTimeField()

class ExamResultInfoSerializer(serializers.ModelSerializer):
    examPaper = serializers.SerializerMethodField()
    marksObtained = serializers.DecimalField(source='marks_obtained', max_digits=5, decimal_places=2)

    class Meta:
        model = ExamResult
        fields = ['examPaper', 'marksObtained', 'status', 'remarks']

    def get_examPaper(self, obj):
        paper = obj.exam_paper
        return {
            'id': paper.id,
            'subject_name': paper.subject.name,
            'duration': paper.duration,
            'type': paper.type,
            'total_marks': paper.total_marks,
            'exam_date': paper.exam_date,
        }

class EnrollmentStudentMinimalSerializer(serializers.ModelSerializer):
    student_id = serializers.ReadOnlyField(source='student.id')
    fullName = serializers.ReadOnlyField(source='student.full_name')
    studentSchoolId = serializers.ReadOnlyField(source='student.school_id')
    examResults = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ['id', 'student_id', 'studentSchoolId', 'fullName', 'status', 'examResults']

    def get_examResults(self, obj):
        results = getattr(obj.student, 'results_for_this_exam', [])
        return ExamResultInfoSerializer(results, many=True).data

class ShareLinkCreateSerializer(serializers.Serializer):
    exam_paper = serializers.PrimaryKeyRelatedField(queryset=ExamPaper.objects.all())
    expires_in_days = serializers.IntegerField(required=False, default=7, min_value=1, max_value=365)

    def create(self, validated_data):
        expires_in = validated_data.pop('expires_in_days', 7)
        link = ExamResultShareLink.objects.create(
            exam_paper=validated_data['exam_paper'],
            expires_at=timezone.now() + timedelta(days=expires_in)
        )
        return link

class ShareLinkSerializer(serializers.ModelSerializer):
    code = serializers.UUIDField(read_only=True)
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = ExamResultShareLink
        fields = ['id', 'exam_paper', 'code', 'is_active', 'is_expired', 'expires_at', 'created_at']

class ShareLinkDataSerializer(serializers.Serializer):
    exam = ExamListSerializer()
    paper = ExamPaperListSerializer()
    eligible_students = EnrollmentStudentMinimalSerializer(many=True)

class ShareLinkResultSubmitSerializer(serializers.Serializer):
    results = ExamResultItemSerializer(many=True)

    def create(self, validated_data):
        exam_paper = self.context['exam_paper']
        results_data = validated_data['results']

        created = []
        updated = []

        with transaction.atomic():
            for item in results_data:
                if item['marks_obtained'] > exam_paper.total_marks:
                    raise serializers.ValidationError(
                        f"Student {item['student'].id} marks exceed paper limit."
                    )

                result, is_new = ExamResult.objects.update_or_create(
                    exam_paper=exam_paper,
                    student=item['student'],
                    defaults={
                        'marks_obtained': item['marks_obtained'],
                        'status': item['status'],
                        'remarks': item.get('remarks', ''),
                    }
                )
                if is_new:
                    created.append(result)
                else:
                    updated.append(result)

        return {'_created': created, '_updated': updated}

