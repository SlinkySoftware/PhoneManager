# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""REST API viewsets for core resources."""
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

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
    queryset = Device.objects.select_related("site", "line_1")
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
    queryset = DeviceTypeConfig.objects.all()
    serializer_class = DeviceTypeConfigSerializer
    permission_classes = [AdminOrReadOnly]
