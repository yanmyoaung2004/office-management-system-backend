
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, IntegrityError
from django.utils.decorators import method_decorator
from core.decorators import role_required
from core.models import Enrollment, Intake, SchoolFee
from core.utils import paginate_response, success_response, error_response
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

class IntakeEnrollmentListView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_student'))
    def get(self, request, intake_id, *args, **kwargs):
        # 1. Fetch and optimize the queryset
        queryset = (
            Enrollment.objects
            .filter(intake_id=intake_id)
            .select_related('student', 'intake', 'intake__current_semester', 'intake__current_semester__year')
            .prefetch_related('semester_fees')
            .order_by('-created_at', 'student__full_name') # Deterministic ordering is still mandatory
        )

        serializer = StudentListSerializer(queryset, many=True)
        return paginate_response(serializer.data, None, request)
    
class SchoolFeeToggleView(APIView):
    permission_classes = [IsAuthenticated]
    
    @method_decorator(role_required('add_schoolfee'))    
    def post(self, request):
        enrollment_id = request.data.get('enrollment_id')
        semester_id = request.data.get('semester_id')
        if not enrollment_id or not semester_id:
            return error_response(error="Both enrollment_id and semester_id are required.", code=400)

        try:
            with transaction.atomic():
                school_fee, created = SchoolFee.objects.get_or_create(
                    enrollment_id=enrollment_id,
                    semester_id=semester_id,
                    defaults={'is_paid': True}
                )
                if not created:
                    school_fee.is_paid = not school_fee.is_paid
                    school_fee.save()
            status_text = "Paid" if school_fee.is_paid else "Unpaid"
            return success_response(
                message=f"Payment status for this semester is now {status_text}.",
                data={
                    'id': school_fee.id,
                    'is_paid': school_fee.is_paid,
                    'enrollment_id': enrollment_id,
                    'semester_id': semester_id
                }
            )

        except IntegrityError:
            return error_response(
                error="Invalid enrollment or semester ID. Record does not exist.", 
                code=400
            )
        except Exception as e:
            # Catch-all for unexpected issues
            return error_response(error=str(e), code=500)

