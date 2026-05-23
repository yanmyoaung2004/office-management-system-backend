
from django.utils import timezone
from rest_framework.generics import ListCreateAPIView
from rest_framework import generics, parsers, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils.decorators import method_decorator
from django.db.models import Prefetch
from core.decorators import role_required 
from .serializers import  ExamListSerializer
from rest_framework.views import APIView
from core.models import Intake, Exam, ExamPaper, ExamPaperComponent, ExamResult, ExamResultShareLink, Enrollment, Year, Semester, IntakeSemester
from core.utils import paginate_response
from .serializers import  IntakeSerializer, ExamCreateSerializer, ExamPaperUploadSerializer, BulkExamResultSerializer, EnrollmentStudentMinimalSerializer, ShareLinkCreateSerializer, ShareLinkSerializer, ShareLinkDataSerializer, ShareLinkResultSubmitSerializer, SubjectBulkResultSerializer
from django.shortcuts import get_object_or_404
from django.conf import settings
from core.utils import success_response, error_response


class IntakeSemesterListView(APIView):
    permission_classes = [IsAuthenticated]
    @method_decorator(role_required('view_intake'))
    def get(self, request):
        qs = Intake.objects.select_related('major').prefetch_related('scheduled_semesters').all()
        major = request.query_params.get('major')
        if major:
            qs = qs.filter(major_id=major)
        
        return paginate_response(qs, IntakeSerializer, request)


class ExamListCreateView(ListCreateAPIView):
    queryset = Exam.objects.all().prefetch_related('papers', 'papers__components', 'papers__subject').select_related('intake', 'semester')
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Exam.objects.all().select_related(
            'intake', 
            'semester'
        ).prefetch_related(
            'papers', 
            'papers__components',
            'papers__subject'
        ).order_by('-date_started')

    @method_decorator(role_required('view_exam'))
    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return paginate_response(qs, ExamListSerializer, request)

    @method_decorator(role_required('add_exam'))
    def post(self, request, *args, **kwargs):
        serializer = ExamCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                error=serializer.errors,
                code='VALIDATION_ERROR',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        self.perform_create(serializer)
        return success_response(
            message="Exam created successfully.",
            status_code=status.HTTP_201_CREATED
        )


class ExamDetailView(APIView):
    
    permission_classes = [IsAuthenticated]
    def get_object(self, pk):
        return get_object_or_404(Exam, pk=pk)

    @method_decorator(role_required('view_exam'))
    def get(self, request, pk):
        exam_obj = self.get_object(pk)
        exam_components = ExamPaperComponent.objects.filter(
            exam_paper__exam=exam_obj
        ).select_related('exam_paper__subject')

        active_enrollments = Enrollment.objects.filter(
            intake=exam_obj.intake,
            status='Enrolled'
        ).select_related('student').prefetch_related(
            Prefetch(
                'student__exam_results',
                queryset=ExamResult.objects.filter(
                    component__in=exam_components
                ).select_related('component__exam_paper__subject'),
                to_attr='results_for_this_exam'
            )
        )

        exam_serializer = ExamListSerializer(exam_obj)
        enrollment_serializer = EnrollmentStudentMinimalSerializer(
            active_enrollments, many=True
        )

        return success_response(data={
            "exam": exam_serializer.data,
            "eligible_students": enrollment_serializer.data
        })

    @method_decorator(role_required('change_exam')) 
    def put(self, request, pk):
        instance = self.get_object(pk)
        serializer = ExamCreateSerializer(instance, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return error_response(
                error=serializer.errors,
                code='VALIDATION_ERROR',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()
        return success_response(
            message="Exam updated successfully."
        )

    @method_decorator(role_required('delete_exam'))    
    def delete(self, request, pk):
        obj = self.get_object(pk)
        obj.delete()
        return success_response(message='Exam deleted successfully')
    

role_required('change_exam')
class ExamPaperComponentUploadView(generics.UpdateAPIView):
    queryset = ExamPaperComponent.objects.all()
    serializer_class = ExamPaperUploadSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    lookup_field = 'id'

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
    
class ExamResultView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('change_exam'))
    def post(self, request, *args, **kwargs):
        serializer = BulkExamResultSerializer(data=request.data)
        if serializer.is_valid():
            try:
                result = serializer.save()
                created = len(result.get('_created', []))
                updated = len(result.get('_updated', []))
                msg = f"{'Created ' + str(created) if created else ''}{' and ' if created and updated else ''}{'Updated ' + str(updated) if updated else ''} record(s)."
                return success_response(message=msg)
            except Exception as e:
                return error_response(
                    error=str(e),
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        return error_response(
                error=serializer.errors,
                code='VALIDATION_ERROR',
                status_code=status.HTTP_400_BAD_REQUEST
            )     


class SubjectBulkResultView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('change_exam'))
    def post(self, request):
        serializer = SubjectBulkResultSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                error=serializer.errors,
                code='VALIDATION_ERROR',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = serializer.save()
            created = len(result.get('_created', []))
            updated = len(result.get('_updated', []))
            parts = []
            if created:
                parts.append(f'Created {created}')
            if updated:
                parts.append(f'Updated {updated}')
            msg = ' and '.join(parts) + ' record(s).'
            return success_response(message=msg)
        except Exception as e:
            return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)


class ShareLinkCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_exam'))
    def post(self, request):
        serializer = ShareLinkCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, 'VALIDATION_ERROR', status.HTTP_400_BAD_REQUEST)
        link = serializer.save()
        link_data = ShareLinkSerializer(link).data
        link_data['url'] = f"/api/exam/share-links/{link.code}"
        return success_response(data=link_data, status_code=status.HTTP_201_CREATED)


class ShareLinkAccessView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, code):
        try:
            link = ExamResultShareLink.objects.select_related(
                'component__exam_paper__exam__intake',
                'component__exam_paper__exam__semester',
                'component__exam_paper__subject'
            ).get(code=code, is_active=True)
        except ExamResultShareLink.DoesNotExist:
            return error_response('Share link not found or inactive.', 'NOT_FOUND', status.HTTP_404_NOT_FOUND)
        if link.is_expired:
            return error_response('Share link has expired.', 'LINK_EXPIRED', status.HTTP_410_GONE)

        component = link.component
        exam_paper = component.exam_paper
        exam_obj = exam_paper.exam

        enrollments = Enrollment.objects.filter(
            intake=exam_obj.intake,
            status='Enrolled'
        ).select_related('student').prefetch_related(
            Prefetch(
                'student__exam_results',
                queryset=ExamResult.objects.filter(
                    component=component
                ).select_related('component__exam_paper__subject'),
                to_attr='results_for_this_exam'
            )
        )

        data = ShareLinkDataSerializer({
            'exam': exam_obj,
            'paper': exam_paper,
            'eligible_students': enrollments,
        }).data

        return success_response(data=data)


class ShareLinkResultSubmitView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, code):
        try:
            link = ExamResultShareLink.objects.get(code=code, is_active=True)
        except ExamResultShareLink.DoesNotExist:
            return error_response('Share link not found or inactive.', 'NOT_FOUND', status.HTTP_404_NOT_FOUND)
        if link.is_expired:
            return error_response('Share link has expired.', 'LINK_EXPIRED', status.HTTP_410_GONE)

        serializer = ShareLinkResultSubmitSerializer(
            data=request.data,
            context={'component': link.component}
        )
        if not serializer.is_valid():
            return error_response(serializer.errors, 'VALIDATION_ERROR', status.HTTP_400_BAD_REQUEST)

        try:
            result = serializer.save()
            created = len(result.get('_created', []))
            updated = len(result.get('_updated', []))
            msg = f"{'Created ' + str(created) if created else ''}{' and ' if created and updated else ''}{'Updated ' + str(updated) if updated else ''} record(s)."
            return success_response(message=msg)
        except Exception as e:
            return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)


class IntakeYearResultsView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_exam'))
    def get(self, request, intake_id, year_number):
        intake = get_object_or_404(Intake, pk=intake_id)
        year = get_object_or_404(Year, major=intake.major, yearNumber=year_number)

        semesters = list(Semester.objects.filter(year=year).order_by('semester_number'))

        semester_data = []
        subject_to_sem_idx = {}
        for sem in semesters:
            subjects = list(sem.subjects.all().order_by('code'))
            semester_data.append({
                'semester_number': sem.semester_number,
                'name': sem.name,
                'subjects': [{'name': s.name, 'code': s.code} for s in subjects],
            })
            for s in subjects:
                subject_to_sem_idx[s.code] = semesters.index(sem)

        enrollments = list(Enrollment.objects.filter(
            intake=intake, status='Enrolled'
        ).select_related('student').order_by('student__full_name'))

        exams = Exam.objects.filter(intake=intake)
        papers = ExamPaper.objects.filter(exam__in=exams)
        components = ExamPaperComponent.objects.filter(exam_paper__in=papers)

        results = ExamResult.objects.filter(
            component__in=components
        ).select_related('student', 'component__exam_paper__subject')

        student_subject_scores = {}
        for r in results:
            sid = r.student_id
            subj_code = r.component.exam_paper.subject.code
            if sid not in student_subject_scores:
                student_subject_scores[sid] = {}
            student_subject_scores[sid][subj_code] = (
                student_subject_scores[sid].get(subj_code, 0) + float(r.marks_obtained)
            )

        students_data = []
        for i, enrollment in enumerate(enrollments):
            student = enrollment.student
            scores = student_subject_scores.get(student.id, {})

            s1_marks = {}
            s2_marks = {}
            for subj_code, total in scores.items():
                sem_idx = subject_to_sem_idx.get(subj_code)
                if sem_idx == 0:
                    s1_marks[subj_code] = total
                elif sem_idx == 1:
                    s2_marks[subj_code] = total

            students_data.append({
                'no': i + 1,
                'rollNo': i + 1,
                'studentId': student.school_id or '',
                'name': student.full_name,
                's1Marks': s1_marks,
                's2Marks': s2_marks,
            })

        return success_response(data={
            'intake': {'code': intake.code, 'major_name': intake.major.name},
            'year': {'name': year.name, 'yearNumber': year.yearNumber, 'type': year.type},
            'semesters': semester_data,
            'students': students_data,
        })


def _ordinal_suffix(day):
    if 11 <= day <= 13:
        return 'th'
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')


def _format_date(date_obj):
    day = date_obj.day
    return f"{day}{_ordinal_suffix(day)} {date_obj.strftime('%B %Y')}"


class SemesterProgressResultView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_exam'))
    def get(self, request, intake_id, semester_id):
        intake = get_object_or_404(Intake, pk=intake_id)
        semester = get_object_or_404(Semester, pk=semester_id)

        intake_sem = get_object_or_404(IntakeSemester, intake=intake, semester=semester)
        year = semester.year

        intake_label = f"{intake.code} - {year.name} ({semester.name})"

        subjects = list(semester.subjects.all().order_by('code'))

        enrollments = list(Enrollment.objects.filter(
            intake=intake, status='Enrolled'
        ).select_related('student').order_by('student__full_name'))

        exams = Exam.objects.filter(intake=intake, semester=semester)
        papers = ExamPaper.objects.filter(exam__in=exams, subject__in=subjects).select_related('subject')
        components = ExamPaperComponent.objects.filter(exam_paper__in=papers)

        results = ExamResult.objects.filter(
            component__in=components
        ).select_related('student', 'component__exam_paper__subject')

        student_subject_results = {}
        for r in results:
            sid = r.student_id
            subj_code = r.component.exam_paper.subject.code
            subj_name = r.component.exam_paper.subject.name
            ctype = r.component.type
            marks = float(r.marks_obtained)
            allocated = r.component.marks_allocated
            if sid not in student_subject_results:
                student_subject_results[sid] = {}
            if subj_code not in student_subject_results[sid]:
                student_subject_results[sid][subj_code] = {
                    'name': subj_name,
                    'components': {}
                }
            student_subject_results[sid][subj_code]['components'][ctype] = {
                'marks_obtained': marks,
                'marks_allocated': allocated,
                'passed': marks >= allocated * 0.5
            }

        seen_subjects = set()
        remark_subjects = []
        for p in papers:
            label = f"{p.subject.code}- {p.subject.name}"
            if p.subject.code not in seen_subjects:
                seen_subjects.add(p.subject.code)
                remark_subjects.append(label)
        remark_subjects.sort()

        students_data = []
        for enrollment in enrollments:
            student = enrollment.student
            subs = student_subject_results.get(student.id, {})

            resubmit = []
            resit = []

            for subj_code, subj_info in subs.items():
                comps = subj_info['components']
                subject_label = f"{subj_code}- {subj_info['name']}"

                failed_assign_pres = any(
                    comps[t]['marks_obtained'] < comps[t]['marks_allocated'] * 0.5
                    for t in ('ASSIGNMENT', 'PRESENTATION') if t in comps
                )
                if failed_assign_pres:
                    resubmit.append(subject_label)

                if 'ONPAPER' in comps and comps['ONPAPER']['marks_obtained'] < comps['ONPAPER']['marks_allocated'] * 0.5:
                    resit.append(subject_label)

            students_data.append({
                'student_id': student.school_id or '',
                'name': student.full_name,
                'resubmit_modules': resubmit,
                'resit_modules': resit,
            })

        return success_response(data={
            'college_name': settings.COLLEGE_NAME,
            'faculty': 'Faculty of Engineering and Technology',
            'program': intake.major.name,
            'intake': intake_label,
            'date': _format_date(timezone.now()),
            'departments': [
                {
                    'name': intake.major.name,
                    'students': students_data,
                }
            ],
            'remark_subjects': remark_subjects,
        })
