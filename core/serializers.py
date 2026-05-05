"""Serializers for School Office Management API."""
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate
from .models import (
    User, Department, Role, Notification
)


# Auth
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            if not user:
                raise serializers.ValidationError(
                    _('Unable to log in with provided credentials.'),
                    code='authorization'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    _('User account is disabled.'),
                    code='authorization'
                )
        else:
            raise serializers.ValidationError(
                _('Must include "username" and "password".'),
                code='authorization'
            )
        attrs['user'] = user
        return attrs

# User

class DepartmentSerializer(serializers.ModelSerializer):
    """
    Serializer for department model.
    """
    class Meta:
        model = Department
        fields = ('id', 'name', 'created_at', 'updated_at')

class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer for role model.
    """
    class Meta:
        model = Role
        fields = ('id', 'name', 'slug', 'created_at', 'updated_at')


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user model.
    """
    department = DepartmentSerializer(read_only=True)
    role = RoleSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 
            'last_name', 'role', 'department', 
            'is_active', 'date_joined'
        )
        read_only_fields = ('id', 'date_joined')

class UserDetailSerializer(serializers.ModelSerializer):
    # Mapping camelCase (Frontend) to snake_case (Backend)
    fullName = serializers.CharField(source='full_name')
    createdAt = serializers.DateTimeField(source='date_joined', read_only=True)
    # Note: 'last_login' only changes on login. 
    # For a real update timestamp, you'd need a field with auto_now=True.
    updatedAt = serializers.DateTimeField(source='last_login', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'fullName', 
            'role', 'password', 'createdAt', 'updatedAt'
        ]
        extra_kwargs = {
            # password should be write-only so it's never sent back to the frontend
            'password': {'write_only': True, 'required': False},
            'id': {'read_only': True}
        }

    def update(self, instance, validated_data):
        # 1. Handle Password separately (must be hashed)
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        # 2. Update all other fields automatically
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class UserCreateSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source='full_name')
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'password', 'fullName', 'email', 'role']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists')
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            email=validated_data['email'],
            role=validated_data.get('role', 'staff')
        )
        return user



# Notification
class NotificationSerializer(serializers.ModelSerializer):

    studentName = serializers.SlugRelatedField(
        read_only=True,
        slug_field='full_name'
    )
    alertType = serializers.ReadOnlyField(source='alert_type')
    isRead = serializers.BooleanField(source='is_read')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'studentName', 'title', 
            'message', 'alertType', 'isRead', 'createdAt'
        ]
        read_only_fields = ['id', 'createdAt', 'user']

