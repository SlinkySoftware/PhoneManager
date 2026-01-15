"""Base device type renderer contract."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class DeviceType:
    """Base contract for device type renderers."""

    TypeID: str
    Manufacturer: str
    Model: str
    NumberOfLines: int
    CommonOptions: Dict[str, Any]
    DeviceSpecificOptions: Dict[str, Any]

    def render(self, device: Any) -> str:
        """Render configuration text for a fully-populated Device instance."""
        raise NotImplementedError
