# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Base device type renderer contract."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Tuple

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

    def render(self, device: Any) -> str:
        """Render configuration text for a fully-populated Device instance."""
        raise NotImplementedError

    def get_provisioning_base_url(self) -> str:
        """Return normalized provisioning base URL from config.

        Raises:
            ValueError: If PROVISIONING_BASE_URL is missing or empty.
        """
        raw_url = config.get("PROVISIONING_BASE_URL", env_var="PROVISIONING_BASE_URL")
        normalized = (raw_url or "").strip().rstrip("/")
        if not normalized:
            raise ValueError(
                'Please set "PROVISIONING_BASE_URL" in configuration to the absolute URL '
                "for the provisioning endpoint."
            )
        return normalized
