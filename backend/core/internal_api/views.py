# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Localhost-only internal HTTP endpoints for trusted local services."""

from __future__ import annotations

import ipaddress
import json
import logging
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .services import (
    INVALID_CONTEXT_MESSAGE,
    get_device_context,
    normalize_destination,
)


logger = logging.getLogger(__name__)


@require_GET
def device_context_view(request: HttpRequest) -> JsonResponse:
    """Validate a device, directory number, and token against Phone Manager state."""
    loopback_response = _reject_if_not_loopback(request)
    if loopback_response:
        return loopback_response

    mac = request.GET.get("mac")
    dn = request.GET.get("dn")
    token = request.GET.get("token")

    missing_fields = [field for field, value in (("mac", mac), ("dn", dn), ("token", token)) if not value]
    if missing_fields:
        return JsonResponse(
            {"detail": f"Missing required query parameter(s): {', '.join(missing_fields)}"},
            status=400,
        )

    result = get_device_context(mac=mac or "", dn=dn or "", token=token or "")
    if not result.valid or not result.context:
        return JsonResponse({"valid": False, "message": INVALID_CONTEXT_MESSAGE}, status=200)

    payload: dict[str, Any] = {
        "valid": True,
        "mac": result.context.compact_mac,
        "model": result.context.model,
        "dn": result.context.line.directory_number,
        "sip_username": result.context.line.registration_account,
        "line_count": 1,
        "device_name": result.context.device.description or None,
        "site": result.context.site_name,
        "dial_plan_id": result.context.dial_plan_id,
        "message": result.message,
    }
    return JsonResponse(payload, status=200)


@csrf_exempt
@require_POST
def normalize_number_view(request: HttpRequest) -> JsonResponse:
    """Normalize a destination number for local phone services integrations."""
    loopback_response = _reject_if_not_loopback(request)
    if loopback_response:
        return loopback_response

    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Malformed JSON"}, status=400)

    missing_fields = [
        field
        for field in ("mac", "dn", "token", "entered_destination")
        if not data.get(field)
    ]
    if missing_fields:
        return JsonResponse(
            {"detail": f"Missing required field(s): {', '.join(missing_fields)}"},
            status=400,
        )

    result = normalize_destination(
        mac=str(data.get("mac", "")),
        dn=str(data.get("dn", "")),
        token=str(data.get("token", "")),
        entered_destination=str(data.get("entered_destination", "")),
    )

    if not result.success:
        if result.message == INVALID_CONTEXT_MESSAGE:
            return JsonResponse({"error": INVALID_CONTEXT_MESSAGE}, status=403)
        return JsonResponse({"error": result.message}, status=400)

    payload = {"normalized_destination": result.normalized_destination, "matched": result.matched}
    return JsonResponse(payload, status=200)


def _reject_if_not_loopback(request: HttpRequest) -> JsonResponse | None:
    if _is_loopback_request(request):
        return None

    logger.warning(
        "internal_api_rejected_non_loopback endpoint=%s remote_addr=%s forwarded=%s x_forwarded_for=%s x_real_ip=%s",
        request.path,
        request.META.get("REMOTE_ADDR"),
        request.META.get("HTTP_FORWARDED"),
        request.META.get("HTTP_X_FORWARDED_FOR"),
        request.META.get("HTTP_X_REAL_IP"),
    )
    return JsonResponse({"error": "Not found"}, status=404)


def _is_loopback_request(request: HttpRequest) -> bool:
    remote_addr = request.META.get("REMOTE_ADDR")
    if not _is_loopback_ip(remote_addr):
        return False

    forwarded_candidates = []
    forwarded_header = request.META.get("HTTP_FORWARDED", "")
    for segment in forwarded_header.split(","):
        for part in segment.split(";"):
            key, _, value = part.partition("=")
            if key.strip().lower() == "for":
                forwarded_candidates.append(value.strip().strip('"'))

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    forwarded_candidates.extend(candidate.strip() for candidate in x_forwarded_for.split(",") if candidate.strip())

    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        forwarded_candidates.append(x_real_ip.strip())

    return all(_is_loopback_ip(candidate) for candidate in forwarded_candidates if candidate)


def _is_loopback_ip(candidate: str | None) -> bool:
    if not candidate:
        return False

    value = candidate.strip().strip('"')
    if value.startswith("[") and "]" in value:
        value = value[1:value.index("]")]
    elif value.count(":") == 1 and "." in value:
        value = value.split(":", 1)[0]

    if value.startswith("for="):
        value = value[4:].strip().strip('"')

    if "%" in value:
        value = value.split("%", 1)[0]

    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False