
from rest_framework.generics import ListCreateAPIView
from rest_framework import generics, parsers, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils.decorators import method_decorator
from django.db.models import Prefetch
from core.decorators import role_required 
from .serializers import  ExamListSerializer
from rest_framework.views import APIView
from core.models import Intake, Exam, ExamPaper, ExamResult, ExamResultShareLink, Enrollment
from core.utils import paginate_response
from .serializers import  IntakeSerializer, ExamCreateSerializer, ExamPaperUploadSerializer, BulkExamResultSerializer, EnrollmentStudentMinimalSerializer, ShareLinkCreateSerializer, ShareLinkSerializer, ShareLinkDataSerializer, ShareLinkResultSubmitSerializer
from django.shortcuts import get_object_or_404
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
    queryset = Exam.objects.all().prefetch_related('papers', 'papers__subject').select_related('intake', 'semester')
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Exam.objects.all().select_related(
            'intake', 
            'semester'
        ).prefetch_related(
            'papers', 
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
        exam_papers = ExamPaper.objects.filter(exam=exam_obj).select_related('subject')

        active_enrollments = Enrollment.objects.filter(
            intake=exam_obj.intake,
            status='Enrolled'
        ).select_related('student').prefetch_related(
            Prefetch(
                'student__exam_results',
                queryset=ExamResult.objects.filter(
                    exam_paper__in=exam_papers
                ).select_related('exam_paper__subject'),
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
class ExamPaperUploadView(generics.UpdateAPIView):
    queryset = ExamPaper.objects.all()
    serializer_class = ExamPaperUploadSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    lookup_field = 'id'  # Using your custom CharField ID

    def patch(self, request, *args, **kwargs):
        """
        Handles partial updates (e.g., just uploading the file).
        """
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Handles full updates.
        """
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
                'exam_paper__exam__intake',
                'exam_paper__exam__semester',
                'exam_paper__subject'
            ).get(code=code, is_active=True)
        except ExamResultShareLink.DoesNotExist:
            return error_response('Share link not found or inactive.', 'NOT_FOUND', status.HTTP_404_NOT_FOUND)
        if link.is_expired:
            return error_response('Share link has expired.', 'LINK_EXPIRED', status.HTTP_410_GONE)

        exam_paper = link.exam_paper
        exam_obj = exam_paper.exam

        enrollments = Enrollment.objects.filter(
            intake=exam_obj.intake,
            status='Enrolled'
        ).select_related('student').prefetch_related(
            Prefetch(
                'student__exam_results',
                queryset=ExamResult.objects.filter(
                    exam_paper=exam_paper
                ).select_related('exam_paper__subject'),
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
            context={'exam_paper': link.exam_paper}
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


