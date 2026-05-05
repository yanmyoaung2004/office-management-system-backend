"""API views for School Office Management System."""
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import  status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated 
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from collections import defaultdict
from core.decorators import role_required
from core.utils import  paginate_response, success_response, error_response
from core.models import (
     Major, Intake,  Enquiry, Semester, IntakeSemester,
    FollowUpSession, Enrollment
)
from .serializers import (
    MajorDetailSerializer, SchoolIdUpdateSerializer,
    IntakeSerializer, IntakeCreateSerializer,
      StudentCreateSerializer, StudentListSerializer
      ,StudentUpdateSerializer,StudentDetailSerializer,
    EnquiryListSerializer, EnquiryDetailSerializer, EnquiryCreateSerializer,
    EnquiryUpdateSerializer,
    FollowUpSessionSerializer, FollowUpCreateSerializer, FollowUpUpdateSerializer,
    MajorEnrollmentSerializer,
    DropoutSerializer, 
    EnrollmentListSerializer, EnrollmentSerializer
)



# ============ Majors ============
class MajorListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_major'))
    def get(self, request):
        qs = Major.objects.prefetch_related(
            'years__semesters' 
        ).all().order_by('id')
        return paginate_response(qs, MajorDetailSerializer, request)

    @method_decorator(role_required('add_major'))
    def post(self, request):
        if request.user.role != 'admin':
            return error_response('Admin only', 'FORBIDDEN', 403)

        serializer = MajorDetailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)

        serializer.save()
        return success_response(serializer.data, 'Major created successfully', 201)
    

class MajorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_major'))
    def get(self, request, pk):
        obj = get_object_or_404(Major, pk=pk)
        serializer = MajorDetailSerializer(obj)
        return success_response(serializer.data)

    @method_decorator(role_required('change_major'))
    def put(self, request, pk):
        major = get_object_or_404(Major, pk=pk)
        serializer = MajorDetailSerializer(major, data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)

        major = serializer.save()
        return success_response(serializer.data, 'Major updated successfully')


    @method_decorator(role_required('delete_major'))
    def delete(self, request, pk):
        if not request.user.role == 'admin':
            return error_response('Admin only', 'FORBIDDEN', 403)
        obj = get_object_or_404(Major, pk=pk)
        obj.delete()
        return success_response(message='Major deleted successfully')

# ============ Intakes ============
def generate_id(prefix, model_class):
    """
    Generate sequential ID with format: PREFIX-NNN
    
    Args:
        prefix: String prefix (e.g., 'ISEM', 'INT', 'STU')
        model_class: Django model class to check uniqueness against
    
    Returns:
        String ID like 'ISEM-001', 'ISEM-002', etc.
    """
    with transaction.atomic():
        last_obj = model_class.objects.select_for_update().filter(
            id__startswith=prefix
        ).order_by('-id').first()
        
        if last_obj:
            last_number = int(last_obj.id.split('-')[-1])
            next_number = last_number + 1
        else:
            next_number = 1
        return f"{prefix}-{next_number:03d}"
    
class IntakeListCreateView(APIView):
    permission_classes = [IsAuthenticated]


    @method_decorator(role_required('view_intake'))
    def get(self, request):
        qs = Intake.objects.select_related('major').prefetch_related('scheduled_semesters').all()
        major = request.query_params.get('major')
        if major:
            qs = qs.filter(major_id=major)
        return paginate_response(qs, IntakeSerializer, request)

    @method_decorator(role_required('add_intake'))    
    def post(self, request):
        serializer = IntakeCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)
        
        try:
            with transaction.atomic():
                semester_schedules = serializer.validated_data.pop('semester_schedules')
                intake_obj = serializer.save()
                for schedule in semester_schedules:
                    semester = Semester.objects.get(id=schedule['semester_id'])                    
                    IntakeSemester.objects.create(
                        intake=intake_obj,
                        semester=semester,
                        start_date=schedule['start_date'],
                        end_date=schedule['end_date'],
                    )
                
            return success_response({
                'id': intake_obj.id,
                'code': intake_obj.code,
                'majorId': intake_obj.major_id,
                'year': intake_obj.year,
                'createdAt': intake_obj.created_at.isoformat() + 'Z'
            }, 'Intake and semester schedules created successfully', 201)
            
        except Semester.DoesNotExist:
            return error_response('Invalid semester_id provided', 'VALIDATION_ERROR', 422)
        except Exception as e:
            return error_response(str(e), 'INTERNAL_ERROR', 500)
    
class IntakeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_intake'))
    def get(self, request, pk):
        obj = get_object_or_404(Intake.objects.select_related('major'), pk=pk)
        serializer = IntakeSerializer(obj)
        data = serializer.data
        return success_response(data)

    @method_decorator(role_required('change_intake'))    
    def put(self, request, pk):
        if not request.user.role == 'admin':
            return error_response('Admin only', 'FORBIDDEN', 403)
        obj = get_object_or_404(Intake, pk=pk)
        serializer = IntakeCreateSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)

        serializer.save()
        return success_response(message='Intake updated successfully')

    @method_decorator(role_required('delete_intake'))    
    def delete(self, request, pk):
        if not request.user.role == 'admin':
            return error_response('Admin only', 'FORBIDDEN', 403)
        obj = get_object_or_404(Intake, pk=pk)
        obj.delete()
        return success_response(message='Intake deleted successfully')

# ============ Students ============

class UpdateSchoolIdView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('change_student'))
    def patch(self, request, pk):
        # I am assuming 'pk' is the Enrollment ID based on your previous code
        enrollment = get_object_or_404(Enrollment.objects.select_related('student'), pk=pk)
        
        serializer = SchoolIdUpdateSerializer(enrollment, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return success_response({
                'schoolId': enrollment.student.school_id
            }, 'School ID updated successfully')
            
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)

class StudentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_student'))
    def get(self, request, pk):
        # We query Enrollment because that's where status/intake/fees live now
        obj = get_object_or_404(
            Enrollment.objects.select_related(
                'student', 
                'intake__major', 
                'intake__current_semester__year'
            ), 
            pk=pk
        )
        serializer = StudentDetailSerializer(obj)
        return success_response(serializer.data)

    @method_decorator(role_required('change_student'))
    def put(self, request, pk):
        obj = get_object_or_404(Enrollment.objects.select_related('student'), pk=pk)
        serializer = StudentUpdateSerializer(obj, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)
            
        enrollment = serializer.save()
        
        return success_response({
            'id': enrollment.id,
            'fullName': enrollment.student.full_name,
            'updatedAt': enrollment.updated_at.isoformat() + 'Z'
        }, 'Student and Enrollment updated successfully')

    @method_decorator(role_required('delete_student'))
    def delete(self, request, pk):
        # Deleting the enrollment record
        obj = get_object_or_404(Enrollment, pk=pk)
        obj.delete()
        return success_response(message='Enrollment deleted successfully')

class StudentListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    @method_decorator(role_required('view_student', 'view_enrollment'))
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
                data['dropout'] = None
                if hasattr(enrollment, 'dropout_record'):
                    data['dropout'] = {
                        "intakeCode": enrollment.intake.code,
                        "reason": enrollment.dropout_record.reason,
                        "remark": enrollment.dropout_record.remark,
                        "status" : enrollment.status,
                        "enrolledDate" : enrollment.enrolled_date,
                        "dropoutDate": enrollment.dropout_record.dropout_date,
                    }
                
                data['previousEnrollments'] = []
                grouped_data[student_id] = data
            else:
                history_item = {
                    "dropout": None
                }
                if hasattr(enrollment, 'dropout_record'):
                    history_item['dropout'] = {
                        "intakeCode": enrollment.intake.code,
                        "reason": enrollment.dropout_record.reason,
                        "remark": enrollment.dropout_record.remark,
                        "status": enrollment.status,
                        "enrolledDate" : enrollment.enrolled_date,
                        "dropoutDate": enrollment.dropout_record.dropout_date,
                    }
                
                grouped_data[student_id]['previousEnrollments'].append(history_item)
        final_list = list(grouped_data.values())
        return paginate_response(final_list, None, request)
    
    @method_decorator(role_required('add_student'))
    def post(self, request):
        serializer = StudentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)
            
        obj = serializer.save() 
        return success_response({
            'id': obj.id,
            'fullName': obj.full_name,
            'createdAt': obj.created_at.isoformat() + 'Z'
        }, 'Student created successfully', 201)

class CreateEnrollmentView(APIView):

    @method_decorator(role_required('add_enrollment'))
    def post(self, request):
        serializer = EnrollmentSerializer(data=request.data)
        
        if serializer.is_valid():
            student = serializer.validated_data['student']
            Enrollment.objects.filter(
                student=student, 
                status='Enrolled'
            ).update(status='Interrupted')

            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ============ Enquiries ============
class EnquiryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_enquiry'))
    def get(self, request):
        qs = Enquiry.objects.prefetch_related('followups').order_by('-date', '-created_at')
        for p, f in [
            ('enquiryType', 'enquiry_type'),
            ('source', 'source_of_information'),
        ]:
            val = request.query_params.get(p)
            if val:
                qs = qs.filter(**{f: val})
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(student_name__icontains=search) |
                Q(desired_program__icontains=search) |
                Q(student_contact_no__icontains=search)
            )
        return paginate_response(qs, EnquiryListSerializer, request)

    @method_decorator(role_required('add_enquiry'))
    def post(self, request):
        serializer = EnquiryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)
        obj = serializer.save()
        return success_response({
            'id': obj.id,
            'studentName': obj.student_name,
            'desiredProgram': obj.desired_program,
            'enquiryType': obj.enquiry_type,
            'createdAt': obj.created_at.isoformat() + 'Z'
        }, 'Enquiry created successfully', 201)

class EnquiryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_enquiry'))
    def get(self, request, pk):
        obj = get_object_or_404(Enquiry.objects.prefetch_related('followups'), pk=pk)
        serializer = EnquiryDetailSerializer(obj)
        return success_response(serializer.data)
    
    @method_decorator(role_required('change_enquiry'))
    def put(self, request, pk):
        obj = get_object_or_404(Enquiry, pk=pk)
        serializer = EnquiryUpdateSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)
        serializer.save()
        return success_response(message='Enquiry updated successfully')

    @method_decorator(role_required('delete_enquiry'))
    def delete(self, request, pk):
        obj = get_object_or_404(Enquiry, pk=pk)
        obj.delete()
        return success_response(message='Enquiry deleted successfully')

# ============ Follow-ups ============
class EnquiryFollowUpListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_followupsession'))
    def get(self, request, enquiry_id):
        get_object_or_404(Enquiry, pk=enquiry_id)
        qs = FollowUpSession.objects.filter(enquiry_id=enquiry_id).order_by('-date')
        return paginate_response(qs, FollowUpSessionSerializer, request)

    @method_decorator(role_required('add_followupsession'))
    def post(self, request, enquiry_id):
        enquiry = get_object_or_404(Enquiry, pk=enquiry_id)
        serializer = FollowUpCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)
        obj = serializer.save(enquiry=enquiry)
        return success_response({
            'id': obj.id,
            'enquiryId': obj.enquiry_id,
            'date': str(obj.date),
            'handledBy': obj.handled_by,
            'createdAt': obj.created_at.isoformat() + 'Z'
        }, 'Follow-up session created successfully', 201)
    

class FollowUpDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_followupsession'))
    def get(self, request, pk):
        obj = get_object_or_404(FollowUpSession, pk=pk)
        serializer = FollowUpSessionSerializer(obj)
        return success_response(serializer.data)

    @method_decorator(role_required('change_followupsession'))
    def put(self, request, pk):
        obj = get_object_or_404(FollowUpSession, pk=pk)
        serializer = FollowUpUpdateSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)
        serializer.save()
        return success_response(message='Follow-up updated successfully')

    @method_decorator(role_required('delete_followupsession'))
    def delete(self, request, pk):
        obj = get_object_or_404(FollowUpSession, pk=pk)
        obj.delete()
        return success_response(message='Follow-up deleted successfully')


# ============ Dropouts ============
class DropoutListCreateView(APIView):
    @method_decorator(role_required('add_dropout'))
    def post(self, request):
        serializer = DropoutSerializer(data=request.data)
        if serializer.is_valid():
            # The serializer .save() calls the .create() we defined above
            obj = serializer.save()
            
            return Response({
                'success': True,
                'message': f'Student status updated to {obj.enrollment.status}',
                'data': {
                    'id': obj.id,
                    'enrollmentId': obj.enrollment.id,
                    'status': obj.enrollment.status
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

# ============ Enrollments ============
class IntakeEnrollmentListView(generics.ListAPIView):
    serializer_class = EnrollmentListSerializer
    pagination_class = None  

    def get_queryset(self):
        intake_id = self.kwargs.get('intake_id')
        return (
            Enrollment.objects
            .filter(intake_id=intake_id)
            .select_related('student')
            .order_by('enrolled_date', 'student__full_name')  # stable, deterministic order
        )

class DashboardSummaryView(APIView):
    def get(self, request):
        # 1. Capture and prepare filters
        year = request.query_params.get('selectedYear')
        major_name = request.query_params.get('selectedYearMajor')
        intake_code = request.query_params.get('selectedIntake')

        filters = {}
        if year:
            filters['intake__year'] = year
        if major_name:
            filters['intake__major__name'] = major_name
        if intake_code:
            filters['intake__code'] = intake_code

        # 2. Query Major Statistics
        major_queryset = (
            Enrollment.objects
            .filter(**filters)
            .values('intake__major__name')
            .annotate(total=Count('id'))
            .order_by('intake__major__name')
        )
        major_stats = MajorEnrollmentSerializer(major_queryset, many=True).data

        # 3. Query Location Statistics
        # Note: Using .filter(**filters) ensures consistency across both datasets
        location_queryset = (
            Enrollment.objects
            .filter(**filters)
            .values('student__city')
            .annotate(value=Count('id'))
            .order_by('-value')
        )
        
        location_stats = [
            {
                "location": item['student__city'] or "Unknown",
                "value": item['value']
            }
            for item in location_queryset
        ]

        # 4. Return combined object
        return Response({
            "majorData": major_stats,
            "locationData": location_stats
        })

class FilterDataView(APIView):
    def get(self, request):
        # 1. Basic flat lists
        years = Intake.objects.values_list('year', flat=True).distinct().order_by('-year')
        majors = Major.objects.values('id', 'name').order_by('name')
        intakes = Intake.objects.values('id', 'code').order_by('code')

        # 2. Year -> Major Mapping
        # We fetch all Intake combinations of year and major info
        year_major_queryset = (
            Intake.objects
            .values('year', 'major__id', 'major__name')
            .distinct()
            .order_by('-year', 'major__name')
        )

        # Organize into a dictionary: { 2022: [{"id": "...", "name": "CS"}, ...], 2023: [...] }
        year_major_map = {}
        for item in year_major_queryset:
            year = item['year']
            if year not in year_major_map:
                year_major_map[year] = []
            
            year_major_map[year].append({
                "id": item['major__id'],
                "name": item['major__name']
            })
        queryset = Intake.objects.select_related('major').values('major__name', 'code')
        mapping = defaultdict(list)
        for item in queryset:
            major_name = item['major__name']
            intake_code = item['code']
            mapping[major_name].append(intake_code)
        return Response({
            "years": years,
            "majors": majors,
            "intakes": intakes,
            "yearMajor": year_major_map,
            'majorIntakeMap': dict(mapping)
        })
    

