
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django.db.models import Q
from core.decorators import role_required
from core.models import Enrollment, Intake
from core.utils import paginate_response, success_response
from .serializers import StudentListSerializer, IntakeSerializer



class IntakeListView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_intake'))
    def get(self, request):
        qs = Intake.objects.select_related('major').prefetch_related('scheduled_semesters').all()
        major = request.query_params.get('major')
        if major:
            qs = qs.filter(major_id=major)
        return paginate_response(qs, IntakeSerializer, request)


class StudentListView(APIView):
    permission_classes = [IsAuthenticated]
    @method_decorator(role_required('view_student'))
    def get(self, request):
        qs = Enrollment.objects.select_related(
            'student', 
            'intake', 
            'intake__major'
        ).prefetch_related(
            'dropout_record'
        ).all().order_by('-created_at')
        filter_map = {
            'intake': 'intake_id',
            'status': 'status',
            'scholar': 'scholar',
            'gender': 'student__gender', 
            'educationLevel': 'student__education_level',
        }

        for param, field in filter_map.items():
            val = request.query_params.get(param)
            if val:
                if param == 'scholar':
                    qs = qs.filter(scholar=(val.lower() == 'true'))
                else:
                    qs = qs.filter(**{field: val})

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(student__full_name__icontains=search) |
                Q(student__nrc__icontains=search) |
                Q(student__email__icontains=search) |
                Q(student__student_phone_no__icontains=search)
            )

        grouped_data = {}
        for enrollment in qs:
            student_id = enrollment.student.id            
            if student_id not in grouped_data:
                serializer = StudentListSerializer(enrollment)
                data = serializer.data
                grouped_data[student_id] = data
        final_list = list(grouped_data.values())
        return paginate_response(final_list, None, request)
    
    

class SchoolFeeUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    @method_decorator(role_required('change_enrollment'))    
    def put(self, request, pk):
        return success_response(message='Enrollment updated successfully')

