from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(permission_codename):
    """
    Check if the user's role has a specific permission.
    Usage: @role_required('view_student')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Check if user is even logged in
            if not request.user.is_authenticated:
                raise PermissionDenied
            
            # 2. Superusers bypass all checks (The 'Directorate' fallback)
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # 3. Check the role-based permissions
            if request.user.role and request.user.role.permissions.filter(codename=permission_codename).exists():
                return view_func(request, *args, **kwargs)
            
            # 4. If they have no role or no permission, kick them out
            raise PermissionDenied
            
        return _wrapped_view
    return decorator