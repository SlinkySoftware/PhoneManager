# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Provisioning-facing views and device type API endpoints."""
import ipaddress
import logging
import re
from typing import Any, Dict

from django.http import Http404, HttpResponse
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Device, DeviceTypeConfig, normalize_mac
from core.serializers import DeviceTypeConfigSerializer
from .registry import get_device_type, list_device_types


logger = logging.getLogger(__name__)


def _normalize_ip_candidate(value: str | None) -> str | None:
    """Normalize a forwarded IP token into a bare IPv4 or IPv6 string."""
    if not value:
        return None

    candidate = value.strip().strip('"')
    if not candidate or candidate.lower() == "unknown":
        return None

    if candidate.startswith("for="):
        candidate = candidate[4:].strip().strip('"')

    if candidate.startswith("[") and "]" in candidate:
        candidate = candidate[1:candidate.index("]")]
    elif candidate.count(":") == 1 and "." in candidate:
        candidate = candidate.split(":", 1)[0]

    if "%" in candidate:
        candidate = candidate.split("%", 1)[0]

    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _extract_forwarded_header_ips(header_value: str | None) -> list[str]:
    """Extract RFC 7239 Forwarded header values in client-to-proxy order."""
    if not header_value:
        return []

    results = []
    for segment in header_value.split(","):
        for part in segment.split(";"):
            key, separator, value = part.partition("=")
            if separator != "=" or key.strip().lower() != "for":
                continue
            normalized = _normalize_ip_candidate(value)
            if normalized:
                results.append(normalized)
    return results


def get_client_ip_address(request) -> str | None:
    """Resolve the originating client IP from forwarded headers and socket metadata."""
    candidates = []
    seen = set()

    def add_candidate(value: str | None):
        normalized = _normalize_ip_candidate(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)

    for value in _extract_forwarded_header_ips(request.headers.get("Forwarded")):
        add_candidate(value)

    x_forwarded_for = request.headers.get("X-Forwarded-For", "")
    for value in x_forwarded_for.split(","):
        add_candidate(value)

    add_candidate(request.headers.get("X-Real-IP"))
    add_candidate(request.META.get("REMOTE_ADDR"))

    return candidates[0] if candidates else None


class DeviceTypeSerializer(serializers.Serializer):
    typeId = serializers.CharField(source="TypeID")
    manufacturer = serializers.CharField(source="Manufacturer")
    model = serializers.CharField(source="Model")
    numberOfLines = serializers.IntegerField(source="NumberOfLines")
    supportsSipServersPerLine = serializers.BooleanField(source="SupportsSIPServersPerLine")
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

        user_agent = request.headers.get("User-Agent", "")
        patterns = getattr(device_type_cls, "UserAgentPatterns", ())
        if patterns:
            matches = any(re.search(pattern, user_agent or "", re.IGNORECASE) for pattern in patterns)
            if not matches:
                logger.warning(
                    "Provisioning User-Agent mismatch mac=%s device_type=%s user_agent=%s",
                    mac,
                    device.device_type_id,
                    user_agent,
                )
                return Response(
                    {
                        "detail": "Provisioning request User-Agent does not match expected device type.",
                        "error_code": "user_agent_mismatch",
                    },
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                )

        # Create a proxy device object with decrypted configuration
        # This ensures renderers receive plaintext passwords
        class DecryptedDevice:
            """Proxy that provides decrypted device configuration to renderer."""
            def __init__(self, original_device):
                self._original = original_device
                # Pre-decrypt configuration
                self.device_specific_configuration = original_device.get_decrypted_device_config()
            
            def __getattr__(self, name):
                # Delegate all other attributes to original device
                return getattr(self._original, name)
        
        decrypted_device = DecryptedDevice(device)
        
        renderer = device_type_cls(
            TypeID=device_type_cls.TypeID,
            Manufacturer=device_type_cls.Manufacturer,
            Model=device_type_cls.Model,
            NumberOfLines=device_type_cls.NumberOfLines,
            CommonOptions=device_type_cls.CommonOptions,
            DeviceSpecificOptions=device_type_cls.DeviceSpecificOptions,
            SupportsSIPServersPerLine=device_type_cls.SupportsSIPServersPerLine,
            ContentType=device_type_cls.ContentType,
            UserAgentPatterns=device_type_cls.UserAgentPatterns,
        )
        config_text = renderer.render(decrypted_device)

        # Update last provisioned metadata for the device request.
        device.last_provisioned_at = timezone.now()
        device.last_requested_ip_address = get_client_ip_address(request)
        device.save(update_fields=['last_provisioned_at', 'last_requested_ip_address'])
        
        return HttpResponse(config_text, content_type=renderer.ContentType)
