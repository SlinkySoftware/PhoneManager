"""REST API viewsets for core resources."""
from rest_framework import permissions, viewsets

from .models import Device, DeviceTypeConfig, Line, SIPServer, Site
from .serializers import DeviceSerializer, DeviceTypeConfigSerializer, LineSerializer, SIPServerSerializer, SiteSerializer


class AdminOrReadOnly(permissions.BasePermission):
    """Allow read for all authenticated users; write for staff."""

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return bool(request.user and request.user.is_staff)


class SIPServerViewSet(viewsets.ModelViewSet):
    queryset = SIPServer.objects.all()
    serializer_class = SIPServerSerializer
    permission_classes = [AdminOrReadOnly]


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.select_related("primary_sip_server", "secondary_sip_server")
    serializer_class = SiteSerializer
    permission_classes = [AdminOrReadOnly]


class LineViewSet(viewsets.ModelViewSet):
    queryset = Line.objects.all()
    serializer_class = LineSerializer
    permission_classes = [AdminOrReadOnly]


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.select_related("site", "line_1")
    serializer_class = DeviceSerializer
    permission_classes = [AdminOrReadOnly]


class DeviceTypeConfigViewSet(viewsets.ModelViewSet):
    queryset = DeviceTypeConfig.objects.all()
    serializer_class = DeviceTypeConfigSerializer
    permission_classes = [AdminOrReadOnly]
