
from rest_framework.generics import ListCreateAPIView
from rest_framework import generics, parsers, status
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from core.decorators import role_required 
from .serializers import  ExamListSerializer
from rest_framework.views import APIView
from core.models import Intake, Exam, ExamPaper, Enrollment
from core.utils import paginate_response
from .serializers import  IntakeSerializer, ExamCreateSerializer, ExamPaperUploadSerializer, BulkExamResultSerializer, EnrollmentStudentMinimalSerializer
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
        
        active_enrollments = Enrollment.objects.filter(
            intake=exam_obj.intake,
            status='Enrolled'
        ).select_related('student').only(
            'id', 'status', 'student__id', 'student__full_name'
        )

        exam_serializer = ExamListSerializer(exam_obj)
        enrollment_serializer = EnrollmentStudentMinimalSerializer(active_enrollments, many=True)

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
    def post(self, request, *args, **kwargs):
        serializer = BulkExamResultSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return success_response(message=f"Successfully processed {len(serializer.validated_data['results'])} records.")
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



