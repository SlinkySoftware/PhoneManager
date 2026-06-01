# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Base device type renderer contract."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Tuple
from urllib.parse import quote

from core.config import config


@dataclass
class DeviceType:
    """Base contract for device type renderers."""

    TypeID: str
    Manufacturer: str
    Model: str
    NumberOfLines: int
    CommonOptions: Dict[str, Any]
    DeviceSpecificOptions: Dict[str, Any]
    SupportsSIPServersPerLine: bool = False
    ContentType: str = "text/plain"  # HTTP Content-Type for rendered configuration
    UserAgentPatterns: Tuple[str, ...] = ()
    lockdown_filename: ClassVar[str] = ""
    lockdown_payload: ClassVar[str] = ""

    def render(self, device: Any) -> str:
        """Render configuration text for a fully-populated Device instance."""
        raise NotImplementedError

    @classmethod
    def get_lockdown_filename(cls) -> str:
        """Return the public lockdown asset filename for this renderer."""
        return str(getattr(cls, "lockdown_filename", "") or "").strip()

    @classmethod
    def get_lockdown_payload(cls) -> str:
        """Return the renderer-owned lockdown payload as plain text."""
        payload = str(getattr(cls, "lockdown_payload", "") or "").strip()
        if not payload:
            return ""
        return f"{payload}\n"

    @classmethod
    def has_lockdown_payload(cls) -> bool:
        """Return whether this renderer exposes a lockdown asset."""
        return bool(cls.get_lockdown_filename() and cls.get_lockdown_payload())

    def get_lockdown_url(self) -> str:
        """Return the absolute lockdown asset URL for this renderer."""
        filename = type(self).get_lockdown_filename()
        if not filename:
            raise ValueError("This renderer does not define a lockdown asset filename.")

        return f"{self.get_provisioning_base_url()}/security/{quote(filename, safe='')}"

    def get_provisioning_base_url(self) -> str:
        """Return normalized provisioning base URL from config.

        Raises:
            ValueError: If PROVISIONING_BASE_URL is missing or empty and no request fallback is available.
        """
        raw_url = config.get("PROVISIONING_BASE_URL", env_var="PROVISIONING_BASE_URL")
        normalized = (raw_url or "").strip().rstrip("/")
        if not normalized:
            request = getattr(self, "request", None)
            if request is not None:
                request_url = request.build_absolute_uri(request.path).rstrip("/")
                normalized = request_url.rsplit("/", 1)[0]

        if not normalized:
            raise ValueError(
                'Please set "PROVISIONING_BASE_URL" in configuration to the absolute URL '
                "for the provisioning endpoint."
            )
        return normalized
