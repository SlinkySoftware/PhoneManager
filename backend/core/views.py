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
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, action, parser_classes
from rest_framework.response import Response
import pytz

from .bulk_imports import XLSX_CONTENT_TYPE, generate_bulk_import_template, import_bulk_workbook, validate_upload_file
from .config import config
from .dialplan_utils import apply_dial_plan
from .ldap import LDAPAuthHandler, LDAPAuthenticationError, LDAPConfigurationError
from .models import Device, DeviceTypeConfig, DialPlan, Line, SIPServer, Site, UserProfile
from .permissions import IsAdmin, IsAdminOrReadOnly
from .saml import SAMLAuthHandler, prepare_django_request
from .serializers import (
    DeviceSerializer, 
    DeviceTypeConfigSerializer, 
    DialPlanSerializer,
    LineSerializer, 
    SIPServerSerializer, 
    SiteSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


def build_auth_response(user: User, profile: UserProfile) -> dict:
    """Build the standard authentication response payload."""
    return {
        'token': Token.objects.get_or_create(user=user)[0].key,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'role': profile.role,
            'auth_source': profile.auth_source,
            'auth_type_label': profile.get_auth_source_display(),
            'force_password_reset': profile.force_password_reset,
        }
    }


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
    # Get or create user profile
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'role': UserProfile.ROLE_READONLY,
            'is_sso': False,
            'auth_source': UserProfile.AUTH_SOURCE_LOCAL,
        }
    )

    if profile.auth_source != UserProfile.AUTH_SOURCE_LOCAL:
        return Response(
            {'detail': 'This account uses external authentication. Select the correct login method.'},
            status=status.HTTP_403_FORBIDDEN
        )

    return Response(build_auth_response(user, profile), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def ldap_login(request):
    """Authenticate a user against LDAP and return the local API token."""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'detail': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        result = LDAPAuthHandler().authenticate_user(username=username, password=password)
    except LDAPConfigurationError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except LDAPAuthenticationError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except Exception as exc:
        logger.exception('Unexpected LDAP authentication error: %s', exc)
        return Response({'detail': 'LDAP authentication failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not result.user.is_active:
        return Response({'detail': 'Account is disabled'}, status=status.HTTP_403_FORBIDDEN)

    return Response(build_auth_response(result.user, result.profile), status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def auth_config(request):
    """Return authentication configuration (SSO enabled status)."""
    return Response(config.get_auth_config(), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """Change password for local (non-SSO) users."""
    user = request.user
    
    # Get or create profile
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'role': UserProfile.ROLE_READONLY,
            'is_sso': False,
            'auth_source': UserProfile.AUTH_SOURCE_LOCAL,
        }
    )
    
    # Check if user is not locally authenticated
    if not profile.is_local:
        auth_label = profile.get_auth_source_display()
        return Response(
            {'detail': f'{auth_label} users cannot change passwords in this system. Please use your identity provider or directory service.'},
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
        profile = user.profile
        
        # Return token and user info
        response_data = build_auth_response(user, profile)
        
        # Redirect to frontend with token
        from django.shortcuts import redirect
        frontend_url = config.get('FRONTEND_URL', default='http://localhost:5173', env_var='FRONTEND_URL')
        redirect_url = f"{frontend_url}/?token={response_data['token']}"
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

        instance, created = DeviceTypeConfig.objects.get_or_create(type_id=type_id)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(type_id=type_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
def download_bulk_import_template(request):
    """Download the XLSX template for bulk device and line import."""
    workbook_bytes = generate_bulk_import_template()
    response = HttpResponse(workbook_bytes, content_type=XLSX_CONTENT_TYPE)
    response['Content-Disposition'] = 'attachment; filename="phone-manager-bulk-import-template.xlsx"'
    return response


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsAdmin])
@parser_classes([MultiPartParser, FormParser])
def bulk_import_workbook(request):
    """Import devices and lines from an uploaded XLSX workbook."""
    uploaded_file = request.FILES.get('file')
    validate_upload_file(uploaded_file)

    try:
        result = import_bulk_workbook(uploaded_file.read())
    except serializers.ValidationError:
        raise
    except Exception as exc:
        logger.exception('Unexpected bulk import failure: %s', exc)
        return Response(
            {'detail': 'An unexpected error occurred while processing the workbook.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    logger.info(
        'Bulk import completed by user=%s lines_imported=%s lines_skipped=%s devices_imported=%s devices_skipped=%s',
        request.user.username,
        result['lines']['imported_count'],
        result['lines']['skipped_count'],
        result['devices']['imported_count'],
        result['devices']['skipped_count'],
    )
    return Response(result, status=status.HTTP_200_OK)


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
            auth_source=UserProfile.AUTH_SOURCE_LOCAL,
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
        
        # LDAP users are view/deactivate only
        if user.profile.auth_source == UserProfile.AUTH_SOURCE_LDAP:
            return Response(
                {'detail': 'LDAP users are managed by the central directory and cannot be edited locally.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # SAML users cannot have their role changed locally
        if user.profile.auth_source == UserProfile.AUTH_SOURCE_SAML and 'role' in request.data:
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
        if 'role' in request.data and user.profile.is_local:
            valid_roles = [UserProfile.ROLE_ADMIN, UserProfile.ROLE_READONLY]
            role = request.data['role']
            if role not in valid_roles:
                return Response(
                    {'detail': f'Invalid role. Must be one of: {", ".join(valid_roles)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.profile.role = role
        
        if 'force_password_reset' in request.data and user.profile.is_local:
            user.profile.force_password_reset = request.data['force_password_reset']
        
        user.profile.save()
        
        logger.info(f"Updated user: {user.username}")
        
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a user account."""
        user = self.get_object()
        
        # Prevent deleting yourself
        if user.id == request.user.id:
            return Response(
                {'detail': 'You cannot delete your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        username = user.username
        profile = getattr(user, 'profile', None)
        auth_source = profile.auth_source if profile else UserProfile.AUTH_SOURCE_LOCAL

        user.delete()
        logger.info("Deleted %s user: %s", auth_source, username)
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
                is_sso=False,
                auth_source=UserProfile.AUTH_SOURCE_LOCAL,
            )
        
        # Check if externally managed user
        if not profile.is_local:
            return Response(
                {'detail': f'Cannot reset password for {profile.get_auth_source_display()} users'},
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


class DialPlanViewSet(viewsets.ModelViewSet):
    """ViewSet for managing dial plans with test function."""
    
    queryset = DialPlan.objects.all()
    serializer_class = DialPlanSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    
    def get_queryset(self):
        """Return all dial plans with prefetched rules."""
        return DialPlan.objects.prefetch_related('rules').all()
    
    def destroy(self, request, *args, **kwargs):
        """Handle delete with foreign key constraint checking."""
        instance = self.get_object()
        
        # Check if dial plan is used by any sites
        site_count = instance.sites.count()
        if site_count > 0:
            return Response(
                {
                    'detail': f'Cannot delete this dial plan as it is currently used by {site_count} site(s). '
                              'Please reassign or remove the dial plan from those sites first.',
                    'error_code': 'foreign_key_constraint'
                },
                status=status.HTTP_409_CONFLICT
            )
        
        try:
            self.perform_destroy(instance)
            logger.info(f"Deleted dial plan: {instance.name}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError as e:
            protected_objects = e.protected_objects
            count = len(protected_objects)
            return Response(
                {
                    'detail': f'Cannot delete this dial plan as it is currently used by {count} related record(s). '
                              'Please reassign or delete those records first.',
                    'error_code': 'foreign_key_constraint'
                },
                status=status.HTTP_409_CONFLICT
            )
        except IntegrityError:
            return Response(
                {
                    'detail': 'Cannot delete this item due to database constraints. '
                              'It may be referenced by other records.',
                    'error_code': 'integrity_error'
                },
                status=status.HTTP_409_CONFLICT
            )
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def test(self, request):
        """Test dial plan transformation on a phone number.
        
        POST /api/dial-plans/test/
        Body: {
            "dial_plan_id": 1,
            "input_number": "0289185593"
        }
        
        Returns: {
            "output": "+61289185593",
            "matched": true,
            "matched_rule_index": 0,
            "matched_rule_pattern": "0X*"
        }
        """
        dial_plan_id = request.data.get('dial_plan_id')
        input_number = request.data.get('input_number')
        
        # Validate input
        if not dial_plan_id:
            return Response(
                {'detail': 'dial_plan_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not input_number:
            return Response(
                {'detail': 'input_number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get dial plan
        try:
            dial_plan = DialPlan.objects.prefetch_related('rules').get(id=dial_plan_id)
        except DialPlan.DoesNotExist:
            return Response(
                {'detail': f'Dial plan with id {dial_plan_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get rules in sequence order
        rules = dial_plan.rules.order_by('sequence_order')
        
        # Apply dial plan
        output, matched_rule_index = apply_dial_plan(input_number, rules)
        
        # Build response
        if matched_rule_index is not None:
            matched_rule = rules.get(sequence_order=matched_rule_index)
            response_data = {
                'output': output,
                'matched': True,
                'matched_rule_index': matched_rule_index,
                'matched_rule_pattern': matched_rule.input_regex
            }
        else:
            response_data = {
                'output': output,
                'matched': False
            }
        
        logger.info(f"Tested dial plan '{dial_plan.name}' on '{input_number}' -> '{output}'")
        
        return Response(response_data, status=status.HTTP_200_OK)
