
from django.utils import timezone
from rest_framework.generics import ListCreateAPIView
from rest_framework import generics, parsers, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.db.models import Prefetch
from core.decorators import role_required 
from .serializers import  ExamListSerializer
from rest_framework.views import APIView
from core.models import Intake, Exam, ExamPaper, ExamPaperComponent, ExamResult, ExamResultShareLink, Enrollment, Year, Semester, IntakeSemester, Teacher, TeacherAvailability, IntakeSubjectFrequency, ClassSchedule
from core.utils import paginate_response
from .serializers import  (
    IntakeSerializer, ExamCreateSerializer, ExamPaperUploadSerializer, BulkExamResultSerializer, 
    EnrollmentStudentMinimalSerializer, ShareLinkCreateSerializer, ShareLinkSerializer, ShareLinkDataSerializer, 
    ShareLinkResultSubmitSerializer, SubjectBulkResultSerializer, TeacherSerializer, TeacherAvailabilitySerializer, 
    TeacherAvailabilityBatchSerializer, IntakeSubjectFrequencySerializer, ClassScheduleSerializer)
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

class SemesterProgressExcelView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_exam'))
    def get(self, request, intake_id, semester_id):
        intake = get_object_or_404(Intake, pk=intake_id)
        semester = get_object_or_404(Semester, pk=semester_id)
        year = semester.year

        subjects = list(semester.subjects.all().order_by('code'))
        enrollments = list(Enrollment.objects.filter(
            intake=intake, status='Enrolled'
        ).select_related('student').order_by('student__full_name'))

        exams = Exam.objects.filter(intake=intake, semester=semester)
        papers = ExamPaper.objects.filter(exam__in=exams, subject__in=subjects)
        components = ExamPaperComponent.objects.filter(exam_paper__in=papers)

        results = ExamResult.objects.filter(
            component__in=components
        ).select_related('student', 'component__exam_paper__subject')

        student_scores = {}
        for r in results:
            sid = r.student_id
            subj_code = r.component.exam_paper.subject.code
            marks = float(r.marks_obtained)
            allocated = float(r.component.marks_allocated)
            if sid not in student_scores:
                student_scores[sid] = {}
            if subj_code not in student_scores[sid]:
                student_scores[sid][subj_code] = {'obtained': 0.0, 'allocated': 0.0}
            student_scores[sid][subj_code]['obtained'] += marks
            student_scores[sid][subj_code]['allocated'] += allocated

        courses = [{'name': s.name, 'code': s.code} for s in subjects]

        students_data = []
        for enrollment in enrollments:
            student = enrollment.student
            scores = []
            for subject in subjects:
                subj_scores = student_scores.get(student.id, {}).get(subject.code)
                if subj_scores and subj_scores['allocated'] > 0:
                    pct = round((subj_scores['obtained'] / subj_scores['allocated']) * 100, 2)
                    scores.append(pct)
                else:
                    scores.append(0)
            students_data.append({
                'id': student.school_id or '',
                'name': student.full_name,
                'scores': scores,
            })

        intake_label = f"{intake.code} - {year.name} ({semester.name})"

        return Response({
            'campus': settings.COLLEGE_NAME,
            'program': intake.major.name,
            'intake': intake_label,
            'courses': courses,
            'students': students_data,
        })

class TeacherListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_exam'))
    def get(self, request):
        qs = Teacher.objects.prefetch_related('subjects').all()
        serializer = TeacherSerializer(qs, many=True)
        return success_response(data=serializer.data)

    @method_decorator(role_required('change_exam'))
    def post(self, request):
        serializer = TeacherSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(error=serializer.errors, code='VALIDATION_ERROR', status_code=400)
        serializer.save()
        return success_response(data=serializer.data, message="Teacher created.", status_code=201)

class TeacherDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Teacher.objects.prefetch_related('subjects'), pk=pk)

    @method_decorator(role_required('view_exam'))
    def get(self, request, pk):
        obj = self.get_object(pk)
        return success_response(data=TeacherSerializer(obj).data)

    @method_decorator(role_required('change_exam'))
    def put(self, request, pk):
        obj = self.get_object(pk)
        serializer = TeacherSerializer(obj, data=request.data)
        if not serializer.is_valid():
            return error_response(error=serializer.errors, code='VALIDATION_ERROR', status_code=400)
        serializer.save()
        return success_response(data=serializer.data, message="Teacher updated.")

    @method_decorator(role_required('change_exam'))
    def delete(self, request, pk):
        obj = self.get_object(pk)
        obj.delete()
        return success_response(message="Teacher deleted.")

class TeacherAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, teacher_pk):
        return get_object_or_404(Teacher, pk=teacher_pk)

    @method_decorator(role_required('view_exam'))
    def get(self, request, teacher_pk):
        teacher = self.get_object(teacher_pk)
        avail_qs = TeacherAvailability.objects.filter(teacher=teacher).order_by('day_of_week', 'slot')

        schedules = ClassSchedule.objects.filter(teacher=teacher).select_related('intake', 'subject')
        schedule_map = {}
        for s in schedules:
            schedule_map[(s.day_of_week, s.slot)] = {
                'intake': s.intake.code,
                'subject': s.subject.code,
            }

        data = []
        for a in avail_qs:
            entry = TeacherAvailabilitySerializer(a).data
            scheduled = schedule_map.get((a.day_of_week, a.slot))
            entry['intake'] = scheduled['intake'] if scheduled else None
            entry['subject'] = scheduled['subject'] if scheduled else None
            data.append(entry)

        return success_response(data=data)

    @method_decorator(role_required('change_exam'))
    def post(self, request, teacher_pk):
        teacher = self.get_object(teacher_pk)
        serializer = TeacherAvailabilityBatchSerializer(
            data=request.data, context={'teacher': teacher}
        )
        if not serializer.is_valid():
            return error_response(error=serializer.errors, code='VALIDATION_ERROR', status_code=400)
        serializer.save()
        return success_response(message="Availability saved.")

class SubjectFrequencyView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_exam'))
    def get(self, request, intake_id, semester_id):
        intake = get_object_or_404(Intake, pk=intake_id)
        semester = get_object_or_404(Semester, pk=semester_id)
        qs = IntakeSubjectFrequency.objects.filter(intake=intake, semester=semester)\
            .select_related('subject')
        return success_response(data=IntakeSubjectFrequencySerializer(qs, many=True).data)

    @method_decorator(role_required('change_exam'))
    def post(self, request, intake_id, semester_id):
        intake = get_object_or_404(Intake, pk=intake_id)
        semester = get_object_or_404(Semester, pk=semester_id)
        data = request.data.copy()
        if isinstance(data, list):
            items = data
        else:
            items = [data]
        results = []
        errors = []
        for item in items:
            item['intake'] = intake.id
            item['semester'] = semester.id
            ser = IntakeSubjectFrequencySerializer(data=item)
            if ser.is_valid():
                obj, _ = IntakeSubjectFrequency.objects.update_or_create(
                    intake=intake, semester=semester, subject=ser.validated_data['subject'],
                    defaults={'frequency': ser.validated_data['frequency']}
                )
                results.append(IntakeSubjectFrequencySerializer(obj).data)
            else:
                errors.append(ser.errors)
        if errors and not results:
            return error_response(error=errors, code='VALIDATION_ERROR', status_code=400)
        return success_response(data=results, message="Subject frequencies saved.")

    @method_decorator(role_required('change_exam'))
    def delete(self, request, intake_id, semester_id):
        intake = get_object_or_404(Intake, pk=intake_id)
        semester = get_object_or_404(Semester, pk=semester_id)
        subject_id = request.query_params.get('subject')
        if subject_id:
            IntakeSubjectFrequency.objects.filter(
                intake=intake, semester=semester, subject_id=subject_id
            ).delete()
        else:
            IntakeSubjectFrequency.objects.filter(intake=intake, semester=semester).delete()
        return success_response(message="Frequencies deleted.")

class TimetableGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('change_exam'))
    def post(self, request, intake_id, semester_id):
        intake = get_object_or_404(Intake, pk=intake_id)
        semester = get_object_or_404(Semester, pk=semester_id)

        frequencies = list(
            IntakeSubjectFrequency.objects.filter(intake=intake, semester=semester)
            .select_related('subject')
        )
        if not frequencies:
            return error_response(
                error="No subject frequencies configured. Set frequencies first.",
                code='NO_FREQUENCIES', status_code=400
            )

        total_classes = sum(f.frequency for f in frequencies)
        if total_classes > 15:
            return error_response(
                error=f"Total classes ({total_classes}) exceed available weekly slots (15).",
                code='OVERBOOKED', status_code=400
            )

        # Map subject -> teachers who can teach it
        teacher_subjects = {}
        for t in Teacher.objects.prefetch_related('subjects').all():
            for s in t.subjects.all():
                teacher_subjects.setdefault(s.id, []).append(t)

        # Restore availability for this intake's old slots
        old_schedules = ClassSchedule.objects.filter(intake=intake, semester=semester)
        for cs in old_schedules:
            TeacherAvailability.objects.filter(
                teacher=cs.teacher, day_of_week=cs.day_of_week, slot=cs.slot
            ).update(is_available=True)
        old_schedules.delete()

        # Available slots per teacher (from TeacherAvailability.is_available=True)
        avail_rows = list(
            TeacherAvailability.objects.filter(is_available=True)
            .values_list('teacher_id', 'day_of_week', 'slot')
        )
        teacher_free = {}
        for t_id, dow, slot in avail_rows:
            teacher_free.setdefault(t_id, set()).add((dow, slot))

        # Existing bookings from OTHER intakes (to prevent double-booking)
        other_bookings = ClassSchedule.objects.exclude(
            intake=intake, semester=semester
        ).values_list('teacher_id', 'day_of_week', 'slot')
        teacher_booked_other = {}
        for t_id, dow, slot in other_bookings:
            teacher_booked_other.setdefault(t_id, set()).add((dow, slot))

        ALL_SLOTS = [(d, s) for d in range(1, 6) for s in ['9-11', '12-2', '2-4']]
        assigned_slots = set()
        all_assignments = []
        errors = []

        frequencies.sort(key=lambda f: -f.frequency)

        for freq in frequencies:
            subject = freq.subject
            needed = freq.frequency

            # Collect all candidate slots across the week
            candidates = []
            for dow, slot_key in ALL_SLOTS:
                if (dow, slot_key) in assigned_slots:
                    continue
                for t in teacher_subjects.get(subject.id, []):
                    # Teacher already booked at this slot by another intake?
                    if (dow, slot_key) in teacher_booked_other.get(t.id, set()):
                        continue
                    # Teacher available at this slot?
                    if teacher_free.get(t.id) and (dow, slot_key) not in teacher_free[t.id]:
                        continue
                    candidates.append((dow, slot_key, t))
                    break

            if len(candidates) < needed:
                errors.append(
                    f"Subject '{subject.code}' needs {needed} slots but only {len(candidates)} are available. "
                    f"Add more teachers or reduce frequency."
                )
                continue

            # Sort to spread across the week: slot-type first, then day
            # e.g. Mon9-11, Tue9-11, Wed9-11, Thu9-11, Fri9-11, Mon12-2, ...
            slot_order = {'9-11': 0, '12-2': 1, '2-4': 2}
            candidates.sort(key=lambda x: (slot_order[x[1]], x[0]))

            for dow, slot_key, teacher in candidates[:needed]:
                assigned_slots.add((dow, slot_key))
                teacher_booked_other.setdefault(teacher.id, set()).add((dow, slot_key))
                all_assignments.append(ClassSchedule(
                    intake=intake, semester=semester,
                    subject=subject, teacher=teacher,
                    day_of_week=dow, slot=slot_key
                ))

        if errors:
            # Don't save — restore availability and return errors
            # (old schedules were already deleted, but nothing was created)
            return error_response(error=errors, code='TIMETABLE_ERRORS', status_code=400)

        ClassSchedule.objects.bulk_create(all_assignments)

        # Mark assigned slots as unavailable
        for cs in all_assignments:
            TeacherAvailability.objects.filter(
                teacher=cs.teacher, day_of_week=cs.day_of_week, slot=cs.slot
            ).update(is_available=False)

        schedules = ClassSchedule.objects.filter(intake=intake, semester=semester)\
            .select_related('subject', 'teacher').order_by('day_of_week', 'slot')

        grid = []
        for dow in range(1, 6):
            day_label = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'][dow-1]
            row = {'day': dow, 'day_label': day_label, 'slots': []}
            for slot_key in ['9-11', '12-2', '2-4']:
                entry = next(
                    (s for s in schedules if s.day_of_week == dow and s.slot == slot_key),
                    None
                )
                row['slots'].append({
                    'slot': slot_key,
                    'subject_code': entry.subject.code if entry else None,
                    'subject_name': entry.subject.name if entry else None,
                    'teacher_name': entry.teacher.name if entry else None,
                })
            grid.append(row)

        return success_response(data={
            'intake': intake.id,
            'semester': semester.id,
            'timetable': grid,
        }, message="Timetable generated.")

class TimetableView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_exam'))
    def get(self, request, intake_id, semester_id):
        intake = get_object_or_404(Intake, pk=intake_id)
        semester = get_object_or_404(Semester, pk=semester_id)
        schedules = ClassSchedule.objects.filter(intake=intake, semester=semester)\
            .select_related('subject', 'teacher').order_by('day_of_week', 'slot')

        grid = []
        for dow in range(1, 6):
            day_label = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'][dow-1]
            row = {'day': dow, 'day_label': day_label, 'slots': []}
            for slot_key in ['9-11', '12-2', '2-4']:
                entry = next(
                    (s for s in schedules if s.day_of_week == dow and s.slot == slot_key),
                    None
                )
                row['slots'].append({
                    'slot': slot_key,
                    'subject_code': entry.subject.code if entry else None,
                    'subject_name': entry.subject.name if entry else None,
                    'teacher_name': entry.teacher.name if entry else None,
                })
            grid.append(row)

        return success_response(data={
            'intake': intake.id,
            'semester': semester.id,
            'timetable': grid,
        })

    @method_decorator(role_required('change_exam'))
    def put(self, request, intake_id, semester_id):
        intake = get_object_or_404(Intake, pk=intake_id)
        semester = get_object_or_404(Semester, pk=semester_id)
        serializer = ClassScheduleSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(error=serializer.errors, code='VALIDATION_ERROR', status_code=400)
        data = serializer.validated_data
        # Restore old slot's availability
        old = ClassSchedule.objects.filter(
            intake=intake, semester=semester,
            day_of_week=data['day_of_week'], slot=data['slot']
        ).first()
        if old:
            TeacherAvailability.objects.filter(
                teacher=old.teacher, day_of_week=old.day_of_week, slot=old.slot
            ).update(is_available=True)
        # Save the new assignment
        ClassSchedule.objects.update_or_create(
            intake=intake, semester=semester,
            day_of_week=data['day_of_week'],
            slot=data['slot'],
            defaults={
                'subject': data['subject'],
                'teacher': data['teacher'],
            }
        )
        # Mark new slot as unavailable
        TeacherAvailability.objects.filter(
            teacher=data['teacher'], day_of_week=data['day_of_week'], slot=data['slot']
        ).update(is_available=False)
        return success_response(message="Schedule slot updated.")

    @method_decorator(role_required('change_exam'))
    def delete(self, request, intake_id, semester_id):
        intake = get_object_or_404(Intake, pk=intake_id)
        semester = get_object_or_404(Semester, pk=semester_id)
        schedules = ClassSchedule.objects.filter(intake=intake, semester=semester)
        for cs in schedules:
            TeacherAvailability.objects.filter(
                teacher=cs.teacher, day_of_week=cs.day_of_week, slot=cs.slot
            ).update(is_available=True)
        schedules.delete()
        return success_response(message="Timetable cleared.")
