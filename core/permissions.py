from rest_framework import permissions

class IsAdminUserRole(permissions.BasePermission):
    """Allows access only to users with the 'Admin' role."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role.name == 'Admin')

class IsSuperAdminUserRole(permissions.BasePermission):
    """Allows access only to users with the 'Admin' role."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
