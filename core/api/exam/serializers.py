from datetime import timedelta
from rest_framework import serializers
from core.models import Exam, ExamPaper, ExamPaperComponent, Semester, Major, Intake, Subject, ExamResult, ExamResultShareLink, Student, Enrollment
from django.db import transaction
from django.utils import timezone



class ExamPaperComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamPaperComponent
        fields = ['id', 'type', 'exam_date', 'duration', 'marks_allocated', 'question_file']

class ExamPaperSerializer(serializers.ModelSerializer):
    components = ExamPaperComponentSerializer(many=True)

    class Meta:
        model = ExamPaper
        fields = ['id', 'subject', 'components']

class ExamCreateSerializer(serializers.ModelSerializer):
    papers = ExamPaperSerializer(many=True)

    class Meta:
        model = Exam
        fields = ['id', 'title', 'semester', 'date_started', 'papers', 'intake']

    def create(self, validated_data):
        papers_data = validated_data.pop('papers')
        exam = Exam.objects.create(**validated_data)
        for paper_data in papers_data:
            components_data = paper_data.pop('components', [])
            paper = ExamPaper.objects.create(exam=exam, subject=paper_data['subject'])
            for comp_data in components_data:
                ExamPaperComponent.objects.create(exam_paper=paper, **comp_data)
        return exam

    def update(self, instance, validated_data):
        papers_data = validated_data.pop('papers', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if papers_data is not None:
            with transaction.atomic():
                incoming_subjects = {p['subject'].pk for p in papers_data}
                for paper in instance.papers.all():
                    if paper.subject_id not in incoming_subjects and not paper.components.exists():
                        paper.delete()

                for paper_data in papers_data:
                    components_data = paper_data.pop('components', [])
                    subject = paper_data['subject']
                    paper, _ = ExamPaper.objects.get_or_create(
                        exam=instance, subject=subject
                    )
                    incoming_types = {c['type'] for c in components_data}
                    paper.components.exclude(type__in=incoming_types).delete()
                    for comp_data in components_data:
                        ExamPaperComponent.objects.update_or_create(
                            exam_paper=paper,
                            type=comp_data['type'],
                            defaults={
                                'exam_date': comp_data['exam_date'],
                                'duration': comp_data['duration'],
                                'marks_allocated': comp_data.get('marks_allocated', 100),
                            }
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

class ExamPaperComponentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamPaperComponent
        fields = ['id', 'type', 'exam_date', 'duration', 'marks_allocated', 'question_file']

class ExamPaperListSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')
    components = ExamPaperComponentListSerializer(many=True, read_only=True)

    class Meta:
        model = ExamPaper
        fields = ['id', 'subject', 'subject_name', 'components']

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
        model = ExamPaperComponent
        fields = ['question_file', 'marks_allocated', 'exam_date', 'duration', 'type']
        
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
    component = serializers.PrimaryKeyRelatedField(queryset=ExamPaperComponent.objects.all())
    results = ExamResultItemSerializer(many=True)

    def create(self, validated_data):
        component = validated_data['component']
        results_data = validated_data['results']
        created = []
        updated = []

        with transaction.atomic():
            for item in results_data:
                if item['marks_obtained'] > component.marks_allocated:
                    raise serializers.ValidationError(
                        f"Student {item['student'].id} marks exceed component limit."
                    )
                result, is_new = ExamResult.objects.update_or_create(
                    component=component,
                    student=item['student'],
                    defaults={
                        'marks_obtained': item['marks_obtained'],
                        'status': item.get('status', 'PENDING'),
                        'remarks': item.get('remarks', ''),
                    }
                )
                if is_new:
                    created.append(result)
                else:
                    updated.append(result)
        return {'_created': created, '_updated': updated}
        
        

class ExamPaperComponentResultInfoSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    subject_name = serializers.CharField()
    duration = serializers.DurationField()
    marks_allocated = serializers.IntegerField()
    exam_date = serializers.DateTimeField()

class ExamResultInfoSerializer(serializers.ModelSerializer):
    component = serializers.SerializerMethodField()
    marksObtained = serializers.DecimalField(source='marks_obtained', max_digits=5, decimal_places=2)

    class Meta:
        model = ExamResult
        fields = ['component', 'marksObtained', 'status', 'remarks']

    def get_component(self, obj):
        c = obj.component
        return {
            'id': c.id,
            'type': c.type,
            'subject_name': c.exam_paper.subject.name,
            'duration': c.duration,
            'marks_allocated': c.marks_allocated,
            'exam_date': c.exam_date,
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
    component = serializers.PrimaryKeyRelatedField(queryset=ExamPaperComponent.objects.all())
    expires_in_days = serializers.IntegerField(required=False, default=7, min_value=1, max_value=365)

    def create(self, validated_data):
        expires_in = validated_data.pop('expires_in_days', 7)
        link = ExamResultShareLink.objects.create(
            component=validated_data['component'],
            expires_at=timezone.now() + timedelta(days=expires_in)
        )
        return link

class ShareLinkSerializer(serializers.ModelSerializer):
    code = serializers.UUIDField(read_only=True)
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = ExamResultShareLink
        fields = ['id', 'component', 'code', 'is_active', 'is_expired', 'expires_at', 'created_at']

class ShareLinkDataSerializer(serializers.Serializer):
    exam = ExamListSerializer()
    paper = ExamPaperListSerializer()
    eligible_students = EnrollmentStudentMinimalSerializer(many=True)

class ShareLinkResultSubmitSerializer(serializers.Serializer):
    results = ExamResultItemSerializer(many=True)

    def create(self, validated_data):
        component = self.context['component']
        results_data = validated_data['results']

        created = []
        updated = []

        with transaction.atomic():
            for item in results_data:
                if item['marks_obtained'] > component.marks_allocated:
                    raise serializers.ValidationError(
                        f"Student {item['student'].id} marks exceed component limit."
                    )

                result, is_new = ExamResult.objects.update_or_create(
                    component=component,
                    student=item['student'],
                    defaults={
                        'marks_obtained': item['marks_obtained'],
                        'status': item.get('status', 'PENDING'),
                        'remarks': item.get('remarks', ''),
                    }
                )
                if is_new:
                    created.append(result)
                else:
                    updated.append(result)

        return {'_created': created, '_updated': updated}


class SubjectResultStudentSerializer(serializers.Serializer):
    student = serializers.SlugRelatedField(
        slug_field='school_id',
        queryset=Student.objects.all()
    )
    marks_obtained = serializers.DecimalField(max_digits=5, decimal_places=2)
    status = serializers.ChoiceField(
        choices=ExamResult.Status.choices, required=False, default='PENDING'
    )
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class SubjectResultComponentSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=ExamPaperComponent.ExamType.choices)
    students = SubjectResultStudentSerializer(many=True)


class SubjectBulkResultSerializer(serializers.Serializer):
    exam = serializers.PrimaryKeyRelatedField(queryset=Exam.objects.all())
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())
    results = SubjectResultComponentSerializer(many=True)

    def validate(self, data):
        exam = data['exam']
        subject = data['subject']

        try:
            paper = ExamPaper.objects.get(exam=exam, subject=subject)
        except ExamPaper.DoesNotExist:
            raise serializers.ValidationError(
                f"No exam paper found for exam '{exam.id}' and subject '{subject.id}'."
            )
        data['_paper'] = paper

        available_types = set(
            paper.components.values_list('type', flat=True)
        )
        requested_types = {r['type'] for r in data['results']}
        missing = requested_types - available_types
        if missing:
            raise serializers.ValidationError(
                f"Component type(s) {missing} not found in paper '{paper.id}'. "
                f"Available: {available_types}"
            )

        components = {
            c.type: c
            for c in paper.components.filter(type__in=requested_types)
        }
        data['_components'] = components

        for item in data['results']:
            comp = components[item['type']]
            for s in item['students']:
                if s['marks_obtained'] > comp.marks_allocated:
                    raise serializers.ValidationError(
                        f"Student '{s['student'].school_id}' marks {s['marks_obtained']} "
                        f"exceed component '{comp.type}' limit of {comp.marks_allocated}."
                    )

        return data

    def create(self, validated_data):
        results_data = validated_data.pop('results')
        components = validated_data.pop('_components')
        validated_data.pop('_paper')

        created = []
        updated = []

        with transaction.atomic():
            for item in results_data:
                comp = components[item['type']]
                for s in item['students']:
                    result, is_new = ExamResult.objects.update_or_create(
                        component=comp,
                        student=s['student'],
                        defaults={
                            'marks_obtained': s['marks_obtained'],
                            'status': s.get('status', 'PENDING'),
                            'remarks': s.get('remarks', ''),
                        }
                    )
                    if is_new:
                        created.append(result)
                    else:
                        updated.append(result)

        return {'_created': created, '_updated': updated}