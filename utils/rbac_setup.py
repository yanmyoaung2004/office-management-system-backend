#!/usr/bin/env python
"""
RBAC Setup and Management Script for School Office Management System
This script sets up initial roles and permissions for the RBAC system.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.getcwd())
django.setup()

from core.models import Role, RolePermission, User, Department

def setup_roles():
    """Create initial roles and their corresponding permissions."""
    print("Setting up RBAC roles and permissions...")
    
    # Role configurations
    roles_config = {
        'admin': {
            'name': 'Admin',
            'slug': 'admin',
            'description': 'System Administrator with full access',
            'permissions': [
                # Student management
                {'module': 'student', 'action': 'view'},
                {'module': 'student', 'action': 'create'},
                {'module': 'student', 'action': 'update'},
                {'module': 'student', 'action': 'delete'},
                
                # Enquiry management
                {'module': 'enquiry', 'action': 'view'},
                {'module': 'enquiry', 'action': 'create'},
                {'module': 'enquiry', 'action': 'update'},
                {'module': 'enquiry', 'action': 'delete'},
                {'module': 'enquiry', 'action': 'approve'},
                
                # Finance management
                {'module': 'finance', 'action': 'view'},
                {'module': 'finance', 'action': 'create'},
                {'module': 'finance', 'action': 'update'},
                {'module': 'finance', 'action': 'approve'},
                
                # Exam management
                {'module': 'exam', 'action': 'view'},
                {'module': 'exam', 'action': 'create'},
                {'module': 'exam', 'action': 'update'},
                {'module': 'exam', 'action': 'approve'},
                
                # User management
                {'module': 'user', 'action': 'view'},
                {'module': 'user', 'action': 'create'},
                {'module': 'user', 'action': 'update'},
                {'module': 'user', 'action': 'delete'},
                
                # Report management
                {'module': 'report', 'action': 'view'},
                {'module': 'report', 'action': 'create'},
                {'module': 'report', 'action': 'update'},
                {'module': 'report', 'action': 'delete'},
            ]
        },
        'hr': {
            'name': 'HR Staff',
            'slug': 'hr-staff',
            'description': 'Human Resources staff',
            'permissions': [
                {'module': 'student', 'action': 'view'},
                {'module': 'student', 'action': 'create'},
                {'module': 'student', 'action': 'update'},
                {'module': 'enquiry', 'action': 'view'},
                {'module': 'enquiry', 'action': 'create'},
                {'module': 'enquiry', 'action': 'update'},
                {'module': 'user', 'action': 'view'},
                {'module': 'report', 'action': 'view'},
                {'module': 'report', 'action': 'create'},
            ]
        },
        'finance': {
            'name': 'Finance Staff',
            'slug': 'finance-staff',
            'description': 'Finance department staff',
            'permissions': [
                {'module': 'student', 'action': 'view'},
                {'module': 'finance', 'action': 'view'},
                {'module': 'finance', 'action': 'create'},
                {'module': 'finance', 'action': 'update'},
                {'module': 'report', 'action': 'view'},
                {'module': 'report', 'action': 'create'},
            ]
        },
        'exam': {
            'name': 'Exam Staff',
            'slug': 'exam-staff',
            'description': 'Examination department staff',
            'permissions': [
                {'module': 'student', 'action': 'view'},
                {'module': 'exam', 'action': 'view'},
                {'module': 'exam', 'action': 'create'},
                {'module': 'exam', 'action': 'update'},
                {'module': 'report', 'action': 'view'},
                {'module': 'report', 'action': 'create'},
            ]
        },
        'staff': {
            'name': 'General Staff',
            'slug': 'general-staff',
            'description': 'General office staff with limited permissions',
            'permissions': [
                {'module': 'student', 'action': 'view'},
                {'module': 'enquiry', 'action': 'view'},
                {'module': 'enquiry', 'action': 'create'},
                {'module': 'report', 'action': 'view'},
                {'module': 'report', 'action': 'create'},
            ]
        }
    }

    # Clean existing roles and permissions
    print("Cleaning existing roles...")
    RolePermission.objects.all().delete()
    # Don't delete roles if users are assigned to them
    # Role.objects.all().delete()  # Skip role deletion to prevent foreign key issues
    
    # Create roles and their permissions
    for role_key, config in roles_config.items():
        print(f"Creating role: {config['name']}")
        role, created = Role.objects.get_or_create(
            name=config['name'],
            slug=config['slug']
        )
        
        # Create permissions for this role
        for perm in config['permissions']:
            RolePermission.objects.get_or_create(
                role=role,
                module=perm['module'],
                action=perm['action']
            )
    
    print("RBAC setup completed successfully!")

def create_superuser():
    """Create a superuser with admin role."""
    print("\nCreating superuser...")
    
    if User.objects.filter(is_superuser=True).exists():
        print("Superuser already exists!")
        return
    
    try:
        admin_role = Role.objects.get(name='Admin')
    except Role.DoesNotExist:
        print("Admin role not found. Please run setup_roles() first.")
        return
    
    # Create a superuser
    superuser = User.objects.create_superuser(
        username='admin',
        email='admin@school.edu',
        password='admin123',
        full_name='System Administrator'
    )
    superuser.role = admin_role
    superuser.department = Department.objects.filter(name='ADMIN').first() or Department.objects.first()
    superuser.save()
    
    print("Superuser created successfully!")
    print("Credentials: admin / admin123")

def check_permissions(user, module, action):
    """
    Check if a user has permission for a specific module and action.
    
    Args:
        user: User instance
        module: string - e.g., 'student', 'enquiry', 'finance', etc.
        action: string - e.g., 'view', 'create', 'update', 'delete', 'approve'
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    if user.is_superuser:
        return True
    
    if not user.role:
        return False
    
    return RolePermission.objects.filter(
        role=user.role,
        module=module,
        action=action
    ).exists()

def test_rbac():
    """Test the RBAC system."""
    print("Testing RBAC system...")
    
    try:
        admin_user = User.objects.get(username='admin')
        
        test_cases = [
            ('student', 'view'),
            ('student', 'create'),
            ('student', 'delete'),
            ('finance', 'view'),
            ('finance', 'create'),
            ('nonexistent', 'view')
        ]
        
        for module, action in test_cases:
            has_perm = check_permissions(admin_user, module, action)
            print(f"Admin permission for {module}:{action} = {has_perm}")
        
    except User.DoesNotExist:
        print("Admin user not found. Run create_superuser() first.")
    
    print("✅ RBAC test completed!")

def main():
    """Main setup function."""
    setup_roles()
    create_superuser()
    test_rbac()

if __name__ == '__main__':
    main()