"""API views for School Office Management System."""
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.serializers import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny #IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from collections import defaultdict
from .models import (
    User, Major, Intake,  Enquiry, Semester, IntakeSemester,
    FollowUpSession, DailyReport, Enrollment, Notification
)
from .permissions import IsAdminUserRole
from .serializers import (
    LoginSerializer, UserSerializer, UserDetailSerializer, UserCreateSerializer,
    MajorDetailSerializer,
    IntakeSerializer, IntakeCreateSerializer,
      StudentCreateSerializer, StudentListSerializer
      ,StudentUpdateSerializer,StudentDetailSerializer,
    EnquiryListSerializer, EnquiryDetailSerializer, EnquiryCreateSerializer,
    EnquiryUpdateSerializer,
    FollowUpSessionSerializer, FollowUpCreateSerializer, FollowUpUpdateSerializer,
    ReportListSerializer, ReportDetailSerializer, ReportCreateSerializer,
    ReportUpdateSerializer, MajorEnrollmentSerializer,
    DropoutSerializer, NotificationSerializer,
    EnrollmentListSerializer, EnrollmentSerializer
)


def paginate_response(data, serializer_class, request, extra_data=None):
    """
    Helper for paginated list responses.
    Supports both Django QuerySets and pre-serialized Python Lists.
    """
    page = max(1, int(request.query_params.get('page', 1)))
    limit = min(max(1, int(request.query_params.get('limit', 10))), 100)
    offset = (page - 1) * limit
    is_list = isinstance(data, list)
    total = len(data) if is_list else data.count()
    items = data[offset:offset + limit]
    if is_list:
        serialized_data = items
    else:
        if serializer_class:
            serialized_data = serializer_class(items, many=True).data
        else:
            serialized_data = items

    return Response({
        'success': True,
        'data': serialized_data,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'totalPages': (total + limit - 1) // limit
        },
        **(extra_data or {})
    })

def success_response(data=None, message=None, status_code=200):
    """Standard success response."""
    resp = {'success': True}
    if message:
        resp['message'] = message
    if data is not None:
        resp['data'] = data
    return Response(resp, status=status_code)


def error_response(error, code='BAD_REQUEST', status_code=400):
    """Standard error response."""
    return Response({
        'success': False,
        'error': error,
        'code': code
    }, status=status_code)


# ============ Auth ============
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            error_details = serializer.errors.get('non_field_errors', ['Invalid credentials'])
            msg = str(error_details[0])
            return error_response(msg, 'UNAUTHORIZED', 401)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        data = {
            'id': user.id,
            'username': user.username,
            'fullName': user.full_name,
             'email': user.email,
            'role': user.role,
             'token': str(refresh.access_token)

        }
        return success_response(data, 'Login successful')

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return success_response(message='Logged out successfully')

# ============ Token Validation ============
class CheckTokenView(APIView):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [JWTAuthentication]
    def post(self, request):
        return Response({
            "isValid": True,
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "role": getattr(request.user, 'role', 'user')
            }
        })    


# ============ Users ============
# @token_required
class UserListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        if not request.user.role == 'admin':
            return error_response('Admin only', 'FORBIDDEN', 403)
        qs = User.objects.all().order_by('id')
        role = request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return paginate_response(qs, UserSerializer, request)

    def post(self, request):
        if request.user.role not in ['admin', 'super_admin']:
            return error_response('Admin only', 'FORBIDDEN', 403)
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            err = serializer.errors
            if 'username' in err:
                return error_response('Username already exists', 'CONFLICT', 400)
            return error_response(
                str(serializer.errors),
                'VALIDATION_ERROR',
                422
            )
        target_role = serializer.validated_data.get('role')
        if target_role == 'admin':
            if not request.user.is_superuser:
                return error_response(
                    'Only super_admins can create admin users', 
                    'FORBIDDEN', 
                    403
                )
        user = serializer.save()
        return success_response({
            'id': user.id,
            'username': user.username,
            'fullName': user.full_name,
            'email': user.email,
            'role': user.role,
            'createdAt': user.date_joined.isoformat() + 'Z'
        }, 'User created successfully', 201)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if request.user.role not in ['admin', 'super_admin'] and request.user != user:
            return error_response('Forbidden', 'FORBIDDEN', 403)
        serializer = UserDetailSerializer(user)
        data = serializer.data
        data['createdAt'] = data.get('createdAt', user.date_joined.isoformat() + 'Z')
        data['updatedAt'] = data.get('updatedAt', (user.last_login or user.date_joined).isoformat() + 'Z')
        return success_response(data)

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if request.user.role != 'admin' and not request.user.is_superuser and request.user != user:
            return error_response('Forbidden', 'FORBIDDEN', 403)
        serializer = UserDetailSerializer(user, data=request.data, partial=True)        
        if serializer.is_valid():
            new_role = serializer.validated_data.get('role')
            if new_role == 'admin' and not getattr(request.user, 'is_superuser', False):
                return error_response(
                    'Only Super Admins can assign the admin role', 
                    'FORBIDDEN', 
                    403
                )
            if 'password' in request.data:
                user.set_password(request.data['password'])
            serializer.save() 
            return success_response(serializer.data, 'User updated successfully')
        return error_response(serializer.errors, 'VALIDATION_ERROR', 400)

    def delete(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        requester = request.user
        if requester.role == 'staff' and not requester.is_superuser:
            return error_response('Staff cannot delete users', 'FORBIDDEN', 403)
        if target_user.is_superuser:
            return error_response('SUPER ADMIN cannot be deleted', 'FORBIDDEN', 403)
        if target_user.role == 'admin' and not requester.is_superuser:
            return error_response('Admins can only be deleted by a SUPER ADMIN', 'FORBIDDEN', 403)
        if target_user.role == 'admin':
            admin_count = User.objects.filter(role='admin').count()
            if admin_count <= 1:
                return error_response('Cannot delete the last admin user', 'FORBIDDEN', 403)
        target_user.delete()
        return success_response(message='User deleted successfully')


# ============ Majors ============
class MajorListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        qs = Major.objects.prefetch_related(
            'years__semesters' 
        ).all().order_by('id')
        return paginate_response(qs, MajorDetailSerializer, request)

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
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request, pk):
        obj = get_object_or_404(Major, pk=pk)
        serializer = MajorDetailSerializer(obj)
        return success_response(serializer.data)

    def put(self, request, pk):
        if request.user.role != 'admin':
            return error_response('Admin only', 'FORBIDDEN', 403)

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
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        qs = Intake.objects.select_related('major').prefetch_related('scheduled_semesters').all()
        major = request.query_params.get('major')
        if major:
            qs = qs.filter(major_id=major)
        return paginate_response(qs, IntakeSerializer, request)
    
    # def post(self, request):
    #     if not request.user.role == 'admin':
    #         return error_response('Admin only', 'FORBIDDEN', 403)
    #     serializer = IntakeCreateSerializer(data=request.data)
    #     if not serializer.is_valid():
    #         return Response({
    #             'success': False,
    #             'error': 'Validation failed',
    #             'details': serializer.errors
    #         }, status=422)
    #     obj = serializer.save()
    #     return success_response({
    #         'id': obj.id,
    #         'code': obj.code,
    #         'majorId': obj.major_id,
    #         'year': obj.year,
    #         'createdAt': obj.created_at.isoformat() + 'Z'
    #     }, 'Intake created successfully', 201)

    def post(self, request):
        if request.user.role != 'admin':
            return error_response('Admin only', 'FORBIDDEN', 403)
    
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
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request, pk):
        obj = get_object_or_404(Intake.objects.select_related('major'), pk=pk)
        serializer = IntakeSerializer(obj)
        data = serializer.data
        return success_response(data)

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

    def delete(self, request, pk):
        if not request.user.role == 'admin':
            return error_response('Admin only', 'FORBIDDEN', 403)
        obj = get_object_or_404(Intake, pk=pk)
        obj.delete()
        return success_response(message='Intake deleted successfully')

# ============ Students ============

class StudentDetailView(APIView):
    permission_classes = [IsAuthenticated]

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

    def delete(self, request, pk):
        # Deleting the enrollment record
        obj = get_object_or_404(Enrollment, pk=pk)
        obj.delete()
        return success_response(message='Enrollment deleted successfully')

class StudentListCreateView(APIView):
    permission_classes = [IsAuthenticated]
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

    def get(self, request, pk):
        obj = get_object_or_404(Enquiry.objects.prefetch_related('followups'), pk=pk)
        serializer = EnquiryDetailSerializer(obj)
        return success_response(serializer.data)

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

    def delete(self, request, pk):
        obj = get_object_or_404(Enquiry, pk=pk)
        obj.delete()
        return success_response(message='Enquiry deleted successfully')

# ============ Follow-ups ============
class EnquiryFollowUpListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, enquiry_id):
        get_object_or_404(Enquiry, pk=enquiry_id)
        qs = FollowUpSession.objects.filter(enquiry_id=enquiry_id).order_by('-date')
        return paginate_response(qs, FollowUpSessionSerializer, request)

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

    def get(self, request, pk):
        obj = get_object_or_404(FollowUpSession, pk=pk)
        serializer = FollowUpSessionSerializer(obj)
        return success_response(serializer.data)

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

    def delete(self, request, pk):
        obj = get_object_or_404(FollowUpSession, pk=pk)
        obj.delete()
        return success_response(message='Follow-up deleted successfully')

# ============ Reports ============
class ReportListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = DailyReport.objects.select_related('user').all().order_by('-date')
        if request.query_params.get('userId'):
            qs = qs.filter(user_id=request.query_params.get('userId'))
        if request.query_params.get('date'):
            qs = qs.filter(date=request.query_params.get('date'))
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(activities__icontains=search)
        return paginate_response(qs, ReportListSerializer, request)

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        if not serializer.is_valid():
            err = serializer.errors
            if 'non_field_errors' in err:
                return error_response(err['non_field_errors'][0], 'BAD_REQUEST', 400)
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': err
            }, status=422)
        try:
            obj = serializer.save()
        except ValidationError as e:
            return error_response(
                str(e.detail[0]) if isinstance(e.detail, list) else str(e.detail),
                'BAD_REQUEST', 400
            )
        return success_response({
            'id': obj.id,
            'userId': obj.user_id,
            'date': str(obj.date),
            'enquiryCount': obj.enquiry_count,
            'createdAt': obj.created_at.isoformat() + 'Z'
        }, 'Report submitted successfully', 201)


class ReportDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        obj = get_object_or_404(
            DailyReport.objects.select_related('user').prefetch_related('report_enquiries__enquiry'),
            pk=pk
        )
        serializer = ReportDetailSerializer(obj)
        return success_response(serializer.data)

    def put(self, request, pk):
        obj = get_object_or_404(DailyReport, pk=pk)
        serializer = ReportUpdateSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=422)
        serializer.save()
        return success_response(message='Report updated successfully')

    def delete(self, request, pk):
        obj = get_object_or_404(DailyReport, pk=pk)
        obj.delete()
        return success_response(message='Report deleted successfully')


class ReportStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = DailyReport.objects.select_related('user')
        start = request.query_params.get('startDate')
        end = request.query_params.get('endDate')
        uid = request.query_params.get('userId')
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        if uid:
            qs = qs.filter(user_id=uid)
        total = qs.count()
        days = 1
        if start and end:
            from datetime import datetime
            d1 = datetime.strptime(start, '%Y-%m-%d').date()
            d2 = datetime.strptime(end, '%Y-%m-%d').date()
            days = max(1, (d2 - d1).days + 1)
        user_counts = qs.values('user__full_name').annotate(c=Count('id')).order_by('-c')
        most_active = user_counts.first()
        report_enquiries = []
        for r in qs.prefetch_related('report_enquiries'):
            for re in r.report_enquiries.all():
                report_enquiries.append(re.enquiry_id)
        from collections import Counter
        most_handled = Counter(report_enquiries).most_common(1)
        return success_response({
            'totalReports': total,
            'averageReportsPerDay': round(total / days, 1) if days else 0,
            'mostActiveUser': most_active['user__full_name'] if most_active else None,
            'mostHandledEnquiries': most_handled[0][0] if most_handled else None,
            'dateRange': {
                'start': start or '',
                'end': end or ''
            }
        })

# ============ Dropouts ============
class DropoutListCreateView(APIView):
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
# ============ Notifications ============
class NotificationListCreateView(APIView):
    """
    Handles 'Get All' and 'Create' (Post)
    """
    permission_classes = [IsAuthenticated]
    def get(self, request):
        # Filter by current user
        notifications = Notification.objects.select_related('student').filter(is_read=False).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

class NotificationDetailView(APIView):
    """
    Handles 'Update' (Put/Patch) and 'Delete'
    """
    permission_classes = [IsAuthenticated]
    def put(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        serializer = NotificationSerializer(notification, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Notification updated',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        return Response({
            'success': False,
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        serializer = NotificationSerializer(notification, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Notification updated',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        return Response({
            'success': False,
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        notification.delete()
        return Response({
            'success': True,
            'message': 'Notification deleted successfully'
        }, status=status.HTTP_200_OK) # Or 204_NO_CONTENT

class NotificationViewSet(viewsets.ModelViewSet):

    serializer_class = NotificationSerializer
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related('student').order_by('-created_at')

    @action(detail=False, methods=['patch'], url_path='mark-all-read')
    def mark_all_read(self, request):
        updated_count = Notification.objects.filter(
            # user=request.user, 
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'success': True, 
            'message': f'Marked {updated_count} notifications as read'
        }, status=status.HTTP_200_OK)
       
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
    

