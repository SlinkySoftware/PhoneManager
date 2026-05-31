# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Service-layer helpers for internal localhost-only APIs."""

from __future__ import annotations

from dataclasses import dataclass
import hmac
import logging
import re

from core.dialplan_utils import apply_dial_plan
from core.models import Device, Line, normalize_mac
from provisioning.registry import get_device_type


logger = logging.getLogger(__name__)

INVALID_CONTEXT_MESSAGE = "Invalid device context"
INVALID_DESTINATION_MESSAGE = "Invalid Destination Specified"
SUPPORTED_DEVICE_TYPE_ID = "YealinkSIPT33G"
SUPPORTED_DEVICE_MODEL = "SIP-T33G"
DESTINATION_MIN_DIGITS = 5
DESTINATION_MAX_DIGITS = 20

SEPARATOR_PATTERN = re.compile(r"[\s().-]+")
PLUS_DIGITS_PATTERN = re.compile(r"^\+?\d+$")
CANONICAL_DESTINATION_PATTERN = re.compile(
    rf"^\+\d{{{DESTINATION_MIN_DIGITS},{DESTINATION_MAX_DIGITS}}}$"
)


@dataclass(frozen=True)
class DeviceContext:
    """Validated device, line, and site context for internal integrations."""

    device: Device
    line: Line
    normalized_mac: str
    model: str
    site_name: str
    dial_plan_id: int | None

    @property
    def compact_mac(self) -> str:
        return self.normalized_mac.replace(":", "")


@dataclass(frozen=True)
class DeviceContextResult:
    """Structured result for device context validation."""

    valid: bool
    message: str
    reason: str | None = None
    context: DeviceContext | None = None


@dataclass(frozen=True)
class NormalizeNumberResult:
    """Structured result for destination normalization."""

    success: bool
    message: str | None = None
    reason: str | None = None
    normalized_destination: str | None = None
    matched: bool = False
    matched_rule_id: int | None = None
    matched_rule_sequence: int | None = None


def get_device_context(mac: str, dn: str, token: str) -> DeviceContextResult:
    """Validate an incoming device/line/token tuple against Phone Manager state."""
    normalized_mac = normalize_mac((mac or "").strip())
    compact_mac = normalized_mac.replace(":", "") if normalized_mac else ""

    try:
        device = (
            Device.objects.select_related("line_1", "site", "site__dial_plan")
            .prefetch_related("lines")
            .get(mac_address__iexact=normalized_mac)
        )
    except Device.DoesNotExist:
        _log_device_context_result(compact_mac, dn, "invalid", "unknown_mac")
        return DeviceContextResult(valid=False, message=INVALID_CONTEXT_MESSAGE, reason="unknown_mac")

    if not device.enabled:
        _log_device_context_result(compact_mac, dn, "invalid", "disabled_device")
        return DeviceContextResult(valid=False, message=INVALID_CONTEXT_MESSAGE, reason="disabled_device")

    device_type_cls = get_device_type(device.device_type_id)
    if not device_type_cls:
        _log_device_context_result(compact_mac, dn, "invalid", "unknown_device_type")
        return DeviceContextResult(valid=False, message=INVALID_CONTEXT_MESSAGE, reason="unknown_device_type")

    if (
        getattr(device_type_cls, "TypeID", None) != SUPPORTED_DEVICE_TYPE_ID
        or getattr(device_type_cls, "Model", None) != SUPPORTED_DEVICE_MODEL
    ):
        _log_device_context_result(compact_mac, dn, "invalid", "unsupported_model")
        return DeviceContextResult(valid=False, message=INVALID_CONTEXT_MESSAGE, reason="unsupported_model")

    ordered_lines = list(device.get_ordered_lines())
    if len(ordered_lines) != 1:
        _log_device_context_result(compact_mac, dn, "invalid", "line_count_mismatch")
        return DeviceContextResult(valid=False, message=INVALID_CONTEXT_MESSAGE, reason="line_count_mismatch")

    line = ordered_lines[0]
    if not _directory_numbers_match(dn, line.directory_number):
        _log_device_context_result(compact_mac, dn, "invalid", "dn_mismatch")
        return DeviceContextResult(valid=False, message=INVALID_CONTEXT_MESSAGE, reason="dn_mismatch")

    expected_token = (line.registration_password or "")[:8]
    if not expected_token or not hmac.compare_digest(token or "", expected_token):
        _log_device_context_result(compact_mac, dn, "invalid", "invalid_token")
        return DeviceContextResult(valid=False, message=INVALID_CONTEXT_MESSAGE, reason="invalid_token")

    context = DeviceContext(
        device=device,
        line=line,
        normalized_mac=normalized_mac,
        model=getattr(device_type_cls, "Model", SUPPORTED_DEVICE_MODEL),
        site_name=device.site.name,
        dial_plan_id=device.site.dial_plan_id,
    )
    _log_device_context_result(context.compact_mac, dn, "valid", "ok")
    return DeviceContextResult(valid=True, message="OK", reason="ok", context=context)


def normalize_destination(mac: str, dn: str, token: str, entered_destination: str) -> NormalizeNumberResult:
    """Normalize a call diversion destination to +E164-style output."""
    context_result = get_device_context(mac=mac, dn=dn, token=token)
    if not context_result.valid or not context_result.context:
        compact_mac = normalize_mac((mac or "").strip()).replace(":", "") if mac else ""
        _log_normalize_result(
            compact_mac=compact_mac,
            dn=dn,
            result="invalid_context",
            reason=context_result.reason or "invalid_context",
            matched_rule_id=None,
            matched_rule_sequence=None,
            changed=False,
        )
        return NormalizeNumberResult(
            success=False,
            message=INVALID_CONTEXT_MESSAGE,
            reason=context_result.reason or "invalid_context",
        )

    cleaned_destination = _sanitize_destination(entered_destination)
    if not cleaned_destination:
        _log_normalize_result(
            compact_mac=context_result.context.compact_mac,
            dn=dn,
            result="invalid_destination",
            reason="invalid_destination_format",
            matched_rule_id=None,
            matched_rule_sequence=None,
            changed=False,
        )
        return NormalizeNumberResult(
            success=False,
            message=INVALID_DESTINATION_MESSAGE,
            reason="invalid_destination_format",
        )

    rules = []
    if context_result.context.device.site.dial_plan_id:
        rules = list(context_result.context.device.site.dial_plan.rules.order_by("sequence_order"))

    transformed_destination, matched_rule_sequence = apply_dial_plan(cleaned_destination, rules)
    matched_rule = next((rule for rule in rules if rule.sequence_order == matched_rule_sequence), None)

    if matched_rule_sequence is not None:
        canonical_destination = _canonicalize_transformed_destination(transformed_destination)
        if not canonical_destination:
            _log_normalize_result(
                compact_mac=context_result.context.compact_mac,
                dn=dn,
                result="invalid_destination",
                reason="rule_output_not_e164",
                matched_rule_id=matched_rule.id if matched_rule else None,
                matched_rule_sequence=matched_rule_sequence,
                changed=False,
            )
            return NormalizeNumberResult(
                success=False,
                message=INVALID_DESTINATION_MESSAGE,
                reason="rule_output_not_e164",
                matched_rule_id=matched_rule.id if matched_rule else None,
                matched_rule_sequence=matched_rule_sequence,
            )

        changed = transformed_destination != cleaned_destination
        _log_normalize_result(
            compact_mac=context_result.context.compact_mac,
            dn=dn,
            result="ok",
            reason="rule_applied",
            matched_rule_id=matched_rule.id if matched_rule else None,
            matched_rule_sequence=matched_rule_sequence,
            changed=changed,
        )
        return NormalizeNumberResult(
            success=True,
            normalized_destination=canonical_destination,
            matched=changed,
            matched_rule_id=matched_rule.id if matched_rule else None,
            matched_rule_sequence=matched_rule_sequence,
        )

    passthrough_destination = _canonicalize_transformed_destination(cleaned_destination)
    if not passthrough_destination:
        _log_normalize_result(
            compact_mac=context_result.context.compact_mac,
            dn=dn,
            result="invalid_destination",
            reason="no_match_and_non_e164",
            matched_rule_id=None,
            matched_rule_sequence=None,
            changed=False,
        )
        return NormalizeNumberResult(
            success=False,
            message=INVALID_DESTINATION_MESSAGE,
            reason="no_match_and_non_e164",
        )

    _log_normalize_result(
        compact_mac=context_result.context.compact_mac,
        dn=dn,
        result="ok",
        reason="pass_through",
        matched_rule_id=None,
        matched_rule_sequence=None,
        changed=False,
    )
    return NormalizeNumberResult(
        success=True,
        normalized_destination=passthrough_destination,
        matched=False,
    )


def _directory_numbers_match(provided_dn: str, expected_dn: str) -> bool:
    """Compare directory numbers conservatively because no shared DN normalizer exists."""
    return (provided_dn or "").strip() == (expected_dn or "").strip()


def _sanitize_destination(destination: str) -> str | None:
    raw = (destination or "").strip()
    if not raw:
        return None

    cleaned = SEPARATOR_PATTERN.sub("", raw)
    if cleaned.count("+") > 1 or ("+" in cleaned and not cleaned.startswith("+")):
        return None

    if not PLUS_DIGITS_PATTERN.fullmatch(cleaned):
        return None

    digits = cleaned[1:] if cleaned.startswith("+") else cleaned
    if not DESTINATION_MIN_DIGITS <= len(digits) <= DESTINATION_MAX_DIGITS:
        return None

    return f"+{digits}" if cleaned.startswith("+") else digits


def _canonicalize_transformed_destination(destination: str) -> str | None:
    cleaned = _sanitize_destination(destination)
    if not cleaned:
        return None

    if not cleaned.startswith("+"):
        return None

    if not CANONICAL_DESTINATION_PATTERN.fullmatch(cleaned):
        return None

    return cleaned


def _log_device_context_result(compact_mac: str, dn: str, result: str, reason: str) -> None:
    logger.info(
        "internal_device_context endpoint=device-context mac=%s dn=%s result=%s reason=%s",
        compact_mac,
        dn,
        result,
        reason,
    )


def _log_normalize_result(
    *,
    compact_mac: str,
    dn: str,
    result: str,
    reason: str,
    matched_rule_id: int | None,
    matched_rule_sequence: int | None,
    changed: bool,
) -> None:
    logger.info(
        "internal_normalize_number endpoint=normalize-number mac=%s dn=%s result=%s reason=%s matched_rule_id=%s matched_rule_sequence=%s changed=%s",
        compact_mac,
        dn,
        result,
        reason,
        matched_rule_id,
        matched_rule_sequence,
        changed,
    )