"""API views for School Office Management System."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny #IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from .decorators import role_required
from .utils import  paginate_response, success_response, error_response
from .models import (
    User,  Notification
)
from .serializers import (
    LoginSerializer, UserSerializer, UserDetailSerializer, UserCreateSerializer,
     NotificationSerializer,
    
)


# ============ Auth ============
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data, context={'request': request})
            if not serializer.is_valid():
                error_msg = next(iter(serializer.errors.values()))[0] 
                return error_response(error_msg, 'UNAUTHORIZED', status.HTTP_401_UNAUTHORIZED)
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'success': True,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
            }, status=status.HTTP_200_OK)

        except Exception:
            return error_response("An unexpected error occurred.", "SERVER_ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    def post(self, request):
        try:
            serializer = UserSerializer(request.user)            
            return Response({
                "success": True,
                "isValid": True,
                "user": serializer.data,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "success": False,
                "isValid": False,
                "message": "Could not retrieve user data.",
                "error": str(e) # Remove str(e) in production for security
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============ Users ============
# @token_required
class UserListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(role_required('view_user'))
    def get(self, request):
        qs = User.objects.all().order_by('id')
        role = request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return paginate_response(qs, UserSerializer, request)

    @method_decorator(role_required('add_user'))
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
    permission_classes = [IsAuthenticated]

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
  