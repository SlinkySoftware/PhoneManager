# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""REST API viewsets for core resources."""
from datetime import datetime
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.decorators import action
import pytz

from .models import Device, DeviceTypeConfig, Line, SIPServer, Site
from .serializers import DeviceSerializer, DeviceTypeConfigSerializer, LineSerializer, SIPServerSerializer, SiteSerializer


class AdminOrReadOnly(permissions.BasePermission):
    """Allow read for all authenticated users; write for staff."""

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return bool(request.user and request.user.is_staff)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """Authenticate user and return token."""
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

    # Get or create token
    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff
        }
    }, status=status.HTTP_200_OK)


class SIPServerViewSet(viewsets.ModelViewSet):
    queryset = SIPServer.objects.all()
    serializer_class = SIPServerSerializer
    permission_classes = [AdminOrReadOnly]

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
    permission_classes = [AdminOrReadOnly]

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
    permission_classes = [AdminOrReadOnly]

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
    permission_classes = [AdminOrReadOnly]

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
    permission_classes = [AdminOrReadOnly]
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