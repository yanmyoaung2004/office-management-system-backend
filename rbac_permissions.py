#!/usr/bin/env python
"""
RBAC Permission Checker Script
This script demonstrates how to check user permissions with the RBAC system.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.getcwd())
django.setup()

from core.models import Role, RolePermission, User

def has_permission(user, module, action):
    """
    Check if a user has permission for a specific module and action.
    
    Args:
        user: User instance or user_id
        module: string - e.g., 'student', 'enquiry', 'finance', 'exam', 'report', 'user'
        action: string - e.g., 'view', 'create', 'update', 'delete', 'approve'
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    if isinstance(user, (int, str)):
        user = User.objects.get(id=user)
    
    # Superuser has all permissions
    if user.is_superuser:
        return True
    
    # User must have a role
    if not user.role:
        return False
    
    # Check if permission exists
    return RolePermission.objects.filter(
        role=user.role,
        module=module,
        action=action
    ).exists()

def list_user_permissions(user):
    """List all permissions for a specific user."""
    if isinstance(user, (int, str)):
        user = User.objects.get(id=user)
    
    if not user.role:
        return []
    
    permissions = RolePermission.objects.filter(role=user.role)
    return [(perm.module, perm.action) for perm in permissions]

def get_permissions_summary():
    """Get a summary of all roles and their permissions."""
    summary = {}
    
    for role in Role.objects.all():
        permissions = RolePermission.objects.filter(role=role)
        summary[role.name] = {
            'slug': role.slug,
            'permissions': [(perm.module, perm.action) for perm in permissions]
        }
    
    return summary

def test_example_permissions():
    """Test the RBAC system with example checks."""
    try:
        admin_role = Role.objects.get(name='Admin')
        
        # Create a test user if one doesn't exist  
        try:
            test_user = User.objects.get(username='test_user')
        except User.DoesNotExist:
            test_user = User.objects.create_user(
                username='test_user',
                email='test@example.com',
                password='test123',
                full_name='Test User'
            )
            test_user.role = admin_role
            test_user.save()
        
        # Test various permissions
        test_cases = [
            (test_user, 'student', 'view'),
            (test_user, 'student', 'create'),
            (test_user, 'enquiry', 'update'),
            (test_user, 'finance', 'view'),
            (test_user, 'report', 'delete'),
            (None, 'nonexistent', 'view')  # This will be False
        ]
        
        print("Testing RBAC System:")
        print("=" * 40)
        
        for user, module, action in test_cases:
            if user is None:
                has_perm = False
            else:
                has_perm = has_permission(user, module, action)
            print(f"User {getattr(user, 'username', 'system')} can {action} {module}: {has_perm}")
        
        print("\nTest user permissions:")
        user_permissions = list_user_permissions(test_user)
        print(f"Test user has {len(user_permissions)} permissions:")
        for module, action in user_permissions[:5]:  # Show first 5
            print(f"  - {action} {module}")
            
    except Exception as e:
        print(f"Error during testing: {e}")

def main():
    """Main function to test the RBAC system."""
    test_example_permissions()
    
    print("\n" + "=" * 40)
    print("Permission Summary for Admin Role")
    print("=" * 40)
    
    try:
        admin_role = Role.objects.get(name='Admin')
        permissions = RolePermission.objects.filter(role=admin_role)
        print(f"Admin has {permissions.count()} permissions:")
        for perm in permissions:
            print(f"  - {perm.action} {perm.module}")
    except Role.DoesNotExist:
        print("Admin role not found")

if __name__ == '__main__':
    main()