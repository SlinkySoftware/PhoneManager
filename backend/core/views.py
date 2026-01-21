# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""REST API viewsets for core resources."""
import logging
import secrets
import string
from datetime import datetime
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
import pytz

from .config import config
from .models import Device, DeviceTypeConfig, Line, SIPServer, Site, UserProfile
from .permissions import IsAdmin, IsAdminOrReadOnly
from .saml import SAMLAuthHandler, prepare_django_request
from .serializers import (
    DeviceSerializer, 
    DeviceTypeConfigSerializer, 
    LineSerializer, 
    SIPServerSerializer, 
    SiteSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


class AdminOrReadOnly(permissions.BasePermission):
    """Allow read for all authenticated users; write for staff."""

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return bool(request.user and request.user.is_staff)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """Authenticate user and return token with role information."""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'detail': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {'detail': 'Invalid username or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.check_password(password):
        return Response(
            {'detail': 'Invalid username or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.is_active:
        return Response(
            {'detail': 'Account is disabled'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get or create token
    token, _ = Token.objects.get_or_create(user=user)
    
    # Get or create user profile
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': UserProfile.ROLE_READONLY, 'is_sso': False}
    )

    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'role': profile.role,
            'is_sso': profile.is_sso,
            'force_password_reset': profile.force_password_reset,
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def auth_config(request):
    """Return authentication configuration (SSO enabled status)."""
    sso_enabled = config.get('SSO_ENABLED', default=False, env_var='SSO_ENABLED')
    return Response({
        'sso_enabled': sso_enabled
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """Change password for local (non-SSO) users."""
    user = request.user
    
    # Get or create profile
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': UserProfile.ROLE_READONLY, 'is_sso': False}
    )
    
    # Check if user is SSO user
    if profile.is_sso:
        return Response(
            {'detail': 'SSO users cannot change passwords in this system. Please use your identity provider.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    
    if not all([old_password, new_password, confirm_password]):
        return Response(
            {'detail': 'All fields required: old_password, new_password, confirm_password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify old password
    if not user.check_password(old_password):
        return Response(
            {'detail': 'Current password is incorrect'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify new passwords match
    if new_password != confirm_password:
        return Response(
            {'detail': 'New passwords do not match'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate password (uses Django validators)
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError as DjangoValidationError
    
    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as e:
        return Response(
            {'detail': ' '.join(e.messages)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Set new password and clear force reset flag
    user.set_password(new_password)
    user.save()
    
    profile.force_password_reset = False
    profile.save()
    
    logger.info(f"Password changed for user: {user.username}")
    
    return Response(
        {'detail': 'Password changed successfully'},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def saml_login(request):
    """Initiate SAML SSO login flow."""
    if not config.get('SSO_ENABLED', default=False, env_var='SSO_ENABLED'):
        return Response(
            {'detail': 'SSO is not enabled'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        request_data = prepare_django_request(request)
        saml_handler = SAMLAuthHandler(request_data)
        sso_url = saml_handler.get_sso_url()
        
        # Redirect to IdP
        from django.shortcuts import redirect
        return redirect(sso_url)
    except Exception as e:
        logger.exception(f"Error initiating SAML login: {e}")
        return Response(
            {'detail': f'SAML login error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def saml_acs(request):
    """SAML Assertion Consumer Service - process SAML response from IdP."""
    if not config.get('SSO_ENABLED', default=False, env_var='SSO_ENABLED'):
        return Response(
            {'detail': 'SSO is not enabled'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        request_data = prepare_django_request(request)
        saml_handler = SAMLAuthHandler(request_data)
        user, error = saml_handler.process_response()
        
        if error:
            logger.error(f"SAML authentication failed: {error}")
            return Response(
                {'detail': error},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not user:
            return Response(
                {'detail': 'Authentication failed'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get or create token
        token, _ = Token.objects.get_or_create(user=user)
        profile = user.profile
        
        # Return token and user info
        response_data = {
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'role': profile.role,
                'is_sso': profile.is_sso,
                'force_password_reset': profile.force_password_reset,
            }
        }
        
        # Redirect to frontend with token
        from django.shortcuts import redirect
        frontend_url = config.get('FRONTEND_URL', default='http://localhost:5173', env_var='FRONTEND_URL')
        redirect_url = f"{frontend_url}/?token={token.key}"
        return redirect(redirect_url)
        
    except Exception as e:
        logger.exception(f"Error processing SAML response: {e}")
        return Response(
            {'detail': f'SAML processing error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def saml_metadata(request):
    """Return SAML SP metadata XML for IdP configuration."""
    if not config.get('SSO_ENABLED', default=False, env_var='SSO_ENABLED'):
        return Response(
            {'detail': 'SSO is not enabled'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        request_data = prepare_django_request(request)
        saml_handler = SAMLAuthHandler(request_data)
        metadata_xml = saml_handler.get_metadata()
        
        return HttpResponse(metadata_xml, content_type='application/xml')
    except Exception as e:
        logger.exception(f"Error generating SAML metadata: {e}")
        return Response(
            {'detail': f'Metadata generation error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class SIPServerViewSet(viewsets.ModelViewSet):
    queryset = SIPServer.objects.all()
    serializer_class = SIPServerSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        """Handle delete with foreign key constraint checking."""
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError as e:
            # Count related objects
            protected_objects = e.protected_objects
            count = len(protected_objects)
            return Response(
                {
                    'detail': f'Cannot delete this SIP Server as it is currently used by {count} site(s). '
                              'Please reassign or delete those sites first.',
                    'error_code': 'foreign_key_constraint'
                },
                status=status.HTTP_409_CONFLICT
            )
        except IntegrityError as e:
            return Response(
                {
                    'detail': 'Cannot delete this item due to database constraints. '
                              'It may be referenced by other records.',
                    'error_code': 'integrity_error'
                },
                status=status.HTTP_409_CONFLICT
            )


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.select_related("primary_sip_server", "secondary_sip_server")
    serializer_class = SiteSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        """Handle delete with foreign key constraint checking."""
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError as e:
            protected_objects = e.protected_objects
            count = len(protected_objects)
            return Response(
                {
                    'detail': f'Cannot delete this Site as it has {count} device(s) assigned to it. '
                              'Please reassign or delete those devices first.',
                    'error_code': 'foreign_key_constraint'
                },
                status=status.HTTP_409_CONFLICT
            )
        except IntegrityError as e:
            return Response(
                {
                    'detail': 'Cannot delete this item due to database constraints. '
                              'It may be referenced by other records.',
                    'error_code': 'integrity_error'
                },
                status=status.HTTP_409_CONFLICT
            )


class LineViewSet(viewsets.ModelViewSet):
    queryset = Line.objects.all()
    serializer_class = LineSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        """Handle delete with foreign key constraint checking."""
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError as e:
            protected_objects = e.protected_objects
            count = len(protected_objects)
            return Response(
                {
                    'detail': f'Cannot delete this Line as it is currently assigned to {count} device(s). '
                              'Please reassign or delete those devices first.',
                    'error_code': 'foreign_key_constraint'
                },
                status=status.HTTP_409_CONFLICT
            )
        except IntegrityError as e:
            return Response(
                {
                    'detail': 'Cannot delete this item due to database constraints. '
                              'It may be referenced by other records.',
                    'error_code': 'integrity_error'
                },
                status=status.HTTP_409_CONFLICT
            )


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.select_related("site", "line_1").prefetch_related("lines")
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        """Handle delete with foreign key constraint checking."""
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError as e:
            protected_objects = e.protected_objects
            count = len(protected_objects)
            return Response(
                {
                    'detail': f'Cannot delete this Device as it has {count} related record(s). '
                              'Please remove those dependencies first.',
                    'error_code': 'foreign_key_constraint'
                },
                status=status.HTTP_409_CONFLICT
            )
        except IntegrityError as e:
            return Response(
                {
                    'detail': 'Cannot delete this item due to database constraints. '
                              'It may be referenced by other records.',
                    'error_code': 'integrity_error'
                },
                status=status.HTTP_409_CONFLICT
            )


class DeviceTypeConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for managing device type configurations.
    
    Supports custom endpoints for getting/saving config by type_id:
    - GET /device-type-config/{type_id}/ - Get config for a type
    - PUT /device-type-config/{type_id}/ - Create/update config for a type
    """
    queryset = DeviceTypeConfig.objects.all()
    serializer_class = DeviceTypeConfigSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    lookup_field = 'type_id'

    def get_object(self):
        """Allow lookup by type_id in URL."""
        type_id = self.kwargs.get('type_id') or self.kwargs.get('pk')
        if not type_id:
            from rest_framework.exceptions import NotFound
            raise NotFound("type_id is required in the URL path")
        try:
            return DeviceTypeConfig.objects.get(type_id=type_id)
        except DeviceTypeConfig.DoesNotExist:
            # Return 404 if not found
            from rest_framework.exceptions import NotFound
            raise NotFound(f"No configuration found for device type: {type_id}")

    def retrieve(self, request, *args, **kwargs):
        """Handle GET request for a specific type_id."""
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Handle PUT/PATCH requests.
        
        Extracts saved_values from request and updates the configuration.
        """
        type_id = kwargs.get('type_id') or kwargs.get('pk')
        if not type_id:
            return Response(
                {'detail': 'type_id is required in the URL path'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            instance = DeviceTypeConfig.objects.get(type_id=type_id)
            saved_values = request.data.get('saved_values', {})
            
            # Update common_options with new schema if provided
            if 'common_options' in request.data:
                instance.common_options = request.data.get('common_options', {})
            
            # Store saved values
            if saved_values:
                instance.common_options['_saved_values'] = saved_values
            
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeviceTypeConfig.DoesNotExist:
            # Create new record
            common_options = request.data.get('common_options', {})
            saved_values = request.data.get('saved_values', {})
            
            instance = DeviceTypeConfig.objects.create(
                type_id=type_id,
                common_options=common_options
            )
            
            # Store saved values
            if saved_values:
                instance.common_options['_saved_values'] = saved_values
                instance.save()
            
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def create(self, request, *args, **kwargs):
        """Handle POST requests to create new configuration."""
        return super().create(request, *args, **kwargs)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_timezones(request):
    """Return all timezones with current UTC offsets.
    
    Returns a list of timezone objects with:
    - value: timezone name (e.g., 'America/New_York')
    - label: display string with offset (e.g., 'America/New_York (UTC-05:00)')
    - offset: UTC offset hours (e.g., -5)
    
    Sorted alphabetically by timezone name.
    """
    now = datetime.now(pytz.UTC)
    timezones = []
    
    for tz_name in sorted(pytz.common_timezones):
        try:
            tz = pytz.timezone(tz_name)
            # Get current offset for this timezone
            tz_now = now.astimezone(tz)
            offset = tz_now.strftime('%z')
            # Format offset as ±HH:MM
            offset_hours = offset[:3]
            offset_minutes = offset[3:5]
            offset_str = f"{offset_hours}:{offset_minutes}"
            
            timezones.append({
                'value': tz_name,
                'label': f"{tz_name} (UTC{offset_str})",
                'offset': offset_str
            })
        except Exception:
            # Skip invalid timezones
            continue
    
    return Response(timezones, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing local users (admin-only)."""
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        """Return all users for list view."""
        return User.objects.select_related('profile').all()
    
    def create(self, request, *args, **kwargs):
        """Create a new local user with temporary password."""
        username = request.data.get('username')
        role = request.data.get('role', UserProfile.ROLE_READONLY)
        email = request.data.get('email', '')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        if not username:
            return Response(
                {'detail': 'Username is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists
        if User.objects.filter(username=username).exists():
            return Response(
                {'detail': 'Username already exists'},
                status=status.HTTP_409_CONFLICT
            )
        
        # Validate role
        valid_roles = [UserProfile.ROLE_ADMIN, UserProfile.ROLE_READONLY]
        if role not in valid_roles:
            return Response(
                {'detail': f'Invalid role. Must be one of: {", ".join(valid_roles)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate temporary password (16 characters, alphanumeric + special)
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        temporary_password = ''.join(secrets.choice(alphabet) for _ in range(16))
        
        # Create user
        user = User.objects.create_user(
            username=username,
            password=temporary_password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        
        # Create profile
        UserProfile.objects.create(
            user=user,
            role=role,
            is_sso=False,
            force_password_reset=True
        )
        
        logger.info(f"Created local user: {username} with role: {role}")
        
        # Return user info with temporary password
        serializer = self.get_serializer(user)
        response_data = serializer.data
        response_data['temporary_password'] = temporary_password
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update user details (email, first_name, last_name, role, force_password_reset)."""
        user = self.get_object()
        
        # SSO users cannot have their role changed locally
        if user.profile.is_sso and 'role' in request.data:
            role_changed = request.data['role'] != user.profile.role
            if role_changed:
                return Response(
                    {'detail': 'Cannot change role for SSO users. Role is managed by identity provider.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Update user fields
        if 'email' in request.data:
            user.email = request.data['email']
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        user.save()
        
        # Update profile fields
        if 'role' in request.data and not user.profile.is_sso:
            valid_roles = [UserProfile.ROLE_ADMIN, UserProfile.ROLE_READONLY]
            role = request.data['role']
            if role not in valid_roles:
                return Response(
                    {'detail': f'Invalid role. Must be one of: {", ".join(valid_roles)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.profile.role = role
        
        if 'force_password_reset' in request.data and not user.profile.is_sso:
            user.profile.force_password_reset = request.data['force_password_reset']
        
        user.profile.save()
        
        logger.info(f"Updated user: {user.username}")
        
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete user or deactivate SSO user."""
        user = self.get_object()
        
        # Prevent deleting yourself
        if user.id == request.user.id:
            return Response(
                {'detail': 'You cannot delete your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if SSO user
        profile = getattr(user, 'profile', None)
        if profile and profile.is_sso:
            # Deactivate instead of delete (prevents auto-recreate on next SSO login)
            user.is_active = False
            user.save()
            logger.info(f"Deactivated SSO user: {user.username}")
            return Response(
                {'detail': 'SSO user deactivated successfully'},
                status=status.HTTP_200_OK
            )
        else:
            # Delete local user
            username = user.username
            user.delete()
            logger.info(f"Deleted local user: {username}")
            return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset password for a local user (admin action)."""
        user = self.get_object()
        
        # Check if user has profile
        profile = getattr(user, 'profile', None)
        if not profile:
            profile = UserProfile.objects.create(
                user=user,
                role=UserProfile.ROLE_READONLY,
                is_sso=False
            )
        
        # Check if SSO user
        if profile.is_sso:
            return Response(
                {'detail': 'Cannot reset password for SSO users'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate new temporary password
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        temporary_password = ''.join(secrets.choice(alphabet) for _ in range(16))
        
        # Set password and force reset
        user.set_password(temporary_password)
        user.save()
        
        profile.force_password_reset = True
        profile.save()
        
        logger.info(f"Reset password for user: {user.username}")
        
        return Response({
            'detail': 'Password reset successfully',
            'temporary_password': temporary_password
        }, status=status.HTTP_200_OK)
