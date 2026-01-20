"""Provisioning-facing views and device type API endpoints."""
from typing import Any, Dict

from django.http import Http404, HttpResponse
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Device, DeviceTypeConfig, normalize_mac
from core.serializers import DeviceTypeConfigSerializer
from .registry import get_device_type, list_device_types


class DeviceTypeSerializer(serializers.Serializer):
    typeId = serializers.CharField(source="TypeID")
    manufacturer = serializers.CharField(source="Manufacturer")
    model = serializers.CharField(source="Model")
    numberOfLines = serializers.IntegerField(source="NumberOfLines")
    commonOptions = serializers.JSONField(source="CommonOptions")
    deviceSpecificOptions = serializers.JSONField(source="DeviceSpecificOptions")


class DeviceTypeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        serializer = DeviceTypeSerializer(list_device_types(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "patch"], url_path="common-options")
    def common_options(self, request, pk=None):
        device_type_cls = get_device_type(pk)
        if not device_type_cls:
            raise Http404

        config, _ = DeviceTypeConfig.objects.get_or_create(type_id=pk)
        if request.method.lower() == "patch":
            serializer = DeviceTypeConfigSerializer(config, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(type_id=pk)
            return Response(serializer.data)

        serializer = DeviceTypeConfigSerializer(config)
        return Response(serializer.data)


class ProvisioningViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, pk=None):
        mac = normalize_mac(pk)
        try:
            device = Device.objects.select_related("line_1", "site__primary_sip_server", "site__secondary_sip_server").get(
                mac_address__iexact=mac
            )
        except Device.DoesNotExist:
            raise Http404("Unknown device")

        if not device.enabled:
            return HttpResponse("Device disabled", status=status.HTTP_403_FORBIDDEN)

        device_type_cls = get_device_type(device.device_type_id)
        if not device_type_cls:
            return HttpResponse("Unsupported device type", status=status.HTTP_404_NOT_FOUND)

        renderer = device_type_cls(
            TypeID=device_type_cls.TypeID,
            Manufacturer=device_type_cls.Manufacturer,
            Model=device_type_cls.Model,
            NumberOfLines=device_type_cls.NumberOfLines,
            CommonOptions=device_type_cls.CommonOptions,
            DeviceSpecificOptions=device_type_cls.DeviceSpecificOptions,
        )
        config_text = renderer.render(device)
        return HttpResponse(config_text, content_type="text/plain")
