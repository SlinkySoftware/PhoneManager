"""Example device type renderer showing schema-driven options."""
from __future__ import annotations
from textwrap import dedent
from typing import Any, Dict

from .base import DeviceType


EXAMPLE_COMMON_OPTIONS: Dict[str, Any] = {
    "sections": [
        {
            "friendlyName": "SIP Registration",
            "uiOrder": 1,
            "options": [
                {
                    "optionId": "outbound_proxy",
                    "friendlyName": "Outbound Proxy",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                }
            ],
        }
    ]
}

EXAMPLE_DEVICE_OPTIONS: Dict[str, Any] = {
    "sections": [
        {
            "friendlyName": "Audio",
            "uiOrder": 1,
            "options": [
                {
                    "optionId": "ringtone",
                    "friendlyName": "Ringtone",
                    "default": "chime",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                },
                {
                    "optionId": "speaker_volume",
                    "friendlyName": "Speaker Volume",
                    "default": 5,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
            ],
        }
    ]
}


class ExampleSIPPhone(DeviceType):
    TypeID = "ExampleSIPPhone"
    Manufacturer = "Slinky"
    Model = "Example 100"
    NumberOfLines = 2
    CommonOptions = EXAMPLE_COMMON_OPTIONS
    DeviceSpecificOptions = EXAMPLE_DEVICE_OPTIONS

    def render(self, device: Any) -> str:
        """Simple renderer emitting deterministic key=value config."""
        line1 = device.line_1
        site = device.site
        proxy = device.device_specific_configuration.get("outbound_proxy") or ""
        ringtone = device.device_specific_configuration.get("ringtone", "chime")
        speaker_volume = device.device_specific_configuration.get("speaker_volume", 5)

        return dedent(
            f"""
            # Example configuration
            mac={device.mac_address}
            manufacturer={self.Manufacturer}
            model={self.Model}
            line1_dn={line1.directory_number}
            line1_user={line1.registration_account}
            line1_password={line1.registration_password}
            site_primary={site.primary_sip_server.host}:{site.primary_sip_server.port}
            site_secondary={getattr(site.secondary_sip_server, 'host', '')}
            transport={site.primary_sip_server.transport}
            outbound_proxy={proxy}
            ringtone={ringtone}
            speaker_volume={speaker_volume}
            """
        ).strip()
