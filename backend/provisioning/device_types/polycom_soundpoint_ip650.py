# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Polycom SoundPoint IP650 device type renderer."""
from typing import Any, Dict, Tuple
from datetime import datetime
from xml.sax.saxutils import escape
import pytz

from .base import DeviceType


# Codec constants
CODEC_G722 = "G.722"
CODEC_G711A = "G.711A"
CODEC_G711MU = "G.711Mu"
CODEC_G729AB = "G.729AB"

CODEC_CHOICES = [
    CODEC_G722,
    CODEC_G711A,
    CODEC_G711MU,
    CODEC_G729AB,
]

# Codec priority attribute keys
CODEC_G722_PRIORITY = "audio.codecs.G722.priority"
CODEC_G711A_PRIORITY = "audio.codecs.G711_A.priority"
CODEC_G711MU_PRIORITY = "audio.codecs.G711_Mu.priority"
CODEC_G729AB_PRIORITY = "audio.codecs.G729_AB.priority"

# UI strings (constants to avoid duplication)
LINE_LABEL = "Line Label"
RING_TONE = "Ring Tone"
DEFAULT_DATE_FORMAT = "DD/MM/YYYY"

# Ring tone constants (1-15) - values match Polycom phone enum
RING_TONES = [
    "Low Trill",           # 1
    "Low Double Trill",    # 2 (gap intentional - values are 1,4,5,6,7,8,9,10,11,12,13,14,15)
    "Medium Trill",        # 3 (gap intentional)
    "Medium Double Trill", # 4
    "High Trill",          # 5
    "High Double Trill",   # 6
    "Highest Trill",       # 7
    "Highest Double Trill",# 8
    "Beeble",              # 9
    "Triplet",             # 10
    "Ringback-Style",      # 11
    "Low Trill Precedence",# 12
    "Ring Splash",         # 13
]

# Date format mappings (UI label -> Polycom format string)
DATE_FORMAT_CHOICES = [
    ("1 Jan, Mon", "D,Md"),
    ("Jan 1, Mon", "Md,D"),
    ("Mon, 1 Jan", "D,dm"),
    ("Mon, Jan 1", "D,md"),
    ("DD/MM/YY", "DD/MM/YY"),
    ("DD/MM/YYYY", "DD/MM/YYYY"),
    ("MM/DD/YY", "MM/DD/YY"),
    ("MM/DD/YYYY", "MM/DD/YYYY"),
    ("YY/MM/DD", "YY/MM/DD"),
    ("YYYY/MM/DD", "YYYY/MM/DD"),
]


COMMON_OPTIONS = {
    "sections": [
        {
            "friendlyName": "Regional Settings",
            "uiOrder": 1,
            "options": [
                {
                    "optionId": "clock_24hour",
                    "friendlyName": "24 Hour Clock",
                    "default": True,
                    "mandatory": False,
                    "type": "checkbox",
                    "uiOrder": 1,
                },
                {
                    "optionId": "date_format",
                    "friendlyName": "Date Format",
                    "default": "DD/MM/YYYY",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 2,
                    "options": [label for label, _ in DATE_FORMAT_CHOICES],
                },
            ],
        },
        {
            "friendlyName": "Syslog",
            "uiOrder": 2,
            "options": [
                {
                    "optionId": "syslog_server",
                    "friendlyName": "Syslog Server",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                },
                {
                    "optionId": "syslog_transport",
                    "friendlyName": "Syslog Transport",
                    "default": "UDP",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 2,
                    "options": ["UDP", "TCP", "TLS"],
                },
                {
                    "optionId": "syslog_facility",
                    "friendlyName": "Syslog Facility",
                    "default": 16,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 3,
                },
                {
                    "optionId": "syslog_renderLevel",
                    "friendlyName": "Syslog Render Level",
                    "default": 2,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 4,
                },
            ],
        },
        {
            "friendlyName": "SIP Parameters",
            "uiOrder": 3,
            "options": [
                {
                    "optionId": "sip_transport",
                    "friendlyName": "SIP Transport Protocol",
                    "default": "UDP",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 1,
                    "options": ["UDP", "TCP"],
                },
                {
                    "optionId": "sip_register_expires",
                    "friendlyName": "SIP Registration Expiry (seconds)",
                    "default": 3600,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
                {
                    "optionId": "sip_retry_timeout",
                    "friendlyName": "SIP Retry Timeout (seconds)",
                    "default": 30,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 3,
                },
            ],
        },
        {
            "friendlyName": "Codecs",
            "uiOrder": 4,
            "options": [
                {
                    "optionId": "codec_priority_order",
                    "friendlyName": "Codec Priority Order",
                    "default": [CODEC_G722, CODEC_G711A, CODEC_G711MU],
                    "mandatory": False,
                    "type": "orderedmultiselect",
                    "uiOrder": 1,
                    "options": CODEC_CHOICES,
                },
            ],
        },
    ]
}


DEVICE_OPTIONS = {
    "sections": [
        {
            "friendlyName": "Administrative",
            "uiOrder": 1,
            "options": [
                {
                    "optionId": "admin_password",
                    "friendlyName": "Admin Password",
                    "default": "",
                    "mandatory": False,
                    "type": "password",
                    "uiOrder": 1,
                },
                {
                    "optionId": "user_password",
                    "friendlyName": "User Password",
                    "default": "",
                    "mandatory": False,
                    "type": "password",
                    "uiOrder": 2,
                },
            ],
        },
        {
            "friendlyName": "Line 1 Configuration",
            "uiOrder": 2,
            "options": [
                {
                    "optionId": "line_1_label",
                    "friendlyName": LINE_LABEL,
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                },
                {
                    "optionId": "line_1_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 2,
                    "options": RING_TONES,
                },
            ],
        },
        {
            "friendlyName": "Line 2 Configuration",
            "uiOrder": 3,
            "options": [
                {
                    "optionId": "line_2_label",
                    "friendlyName": LINE_LABEL,
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                },
                {
                    "optionId": "line_2_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 2,
                    "options": RING_TONES,
                },
            ],
        },
        {
            "friendlyName": "Line 3 Configuration",
            "uiOrder": 4,
            "options": [
                {
                    "optionId": "line_3_label",
                    "friendlyName": LINE_LABEL,
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                },
                {
                    "optionId": "line_3_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 2,
                    "options": RING_TONES,
                },
            ],
        },
        {
            "friendlyName": "Line 4 Configuration",
            "uiOrder": 5,
            "options": [
                {
                    "optionId": "line_4_label",
                    "friendlyName": LINE_LABEL,
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                },
                {
                    "optionId": "line_4_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 2,
                    "options": RING_TONES,
                },
            ],
        },
        {
            "friendlyName": "Line 5 Configuration",
            "uiOrder": 6,
            "options": [
                {
                    "optionId": "line_5_label",
                    "friendlyName": LINE_LABEL,
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                },
                {
                    "optionId": "line_5_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 2,
                    "options": RING_TONES,
                },
            ],
        },
        {
            "friendlyName": "Line 6 Configuration",
            "uiOrder": 7,
            "options": [
                {
                    "optionId": "line_6_label",
                    "friendlyName": LINE_LABEL,
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                },
                {
                    "optionId": "line_6_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 2,
                    "options": RING_TONES,
                },
            ],
        },
    ]
}


class PolycomSoundPointIP650(DeviceType):
    """Polycom SoundPoint IP650 device type renderer.
    
    Generates XML configuration for Polycom SoundPoint IP650 phones with
    all parameters as attributes on a single <ALL> tag.
    """

    TypeID = "PolycomSoundPointIP650"
    Manufacturer = "Polycom"
    Model = "SoundPoint IP650"
    NumberOfLines = 6
    CommonOptions = COMMON_OPTIONS
    DeviceSpecificOptions = DEVICE_OPTIONS
    ContentType = "application/xml"

    def _get_gmt_offset(self, timezone_str: str) -> int:
        """Calculate GMT offset in seconds for a given timezone.
        
        Args:
            timezone_str: Timezone string (e.g., 'America/New_York')
            
        Returns:
            Offset in seconds from GMT
        """
        try:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            utc_offset = now.utcoffset()
            if utc_offset is not None:
                return int(utc_offset.total_seconds())
            return 0
        except Exception:
            return 0  # Default to GMT if timezone invalid

    def _calculate_dst_rules(self, timezone_str: str) -> Tuple[str, str, str, str]:
        """Calculate DST start/end rules for a timezone.
        
        Returns:
            Tuple of (dst_start_month, dst_start_day, dst_stop_month, dst_stop_day)
            where day is formatted as: week/day_of_week (e.g., "8/1" for 2nd Sunday)
            Week values: 1, 8, 15, 22 for 1st-4th occurrence
        """
        try:
            # Use a simple heuristic: check if DST is in effect in March and October
            # This works for most regions (Northern Hemisphere)
            tz = pytz.timezone(timezone_str)
            year = datetime.now().year
            
            # Check March 15 and October 15 to detect DST changes
            march_date = datetime(year, 3, 15, 12, 0, 0)
            october_date = datetime(year, 10, 15, 12, 0, 0)
            
            march_tz = tz.localize(march_date)
            october_tz = tz.localize(october_date)
            
            march_offset = march_tz.utcoffset()
            october_offset = october_tz.utcoffset()
            
            if march_offset != october_offset:
                # DST exists - return standard DST dates for Northern Hemisphere
                # 2nd Sunday in March (start) and 1st Sunday in November (end)
                return ("3", "8/1", "11", "1/1")
        except Exception:
            pass
        
        # Default: no DST
        return ("1", "1/1", "1", "1/1")

    def _convert_dial_plan(self, dial_plan_str: str) -> str:
        """Convert internal dial plan format to Polycom format.
        
        Args:
            dial_plan_str: Dial plan string (internal format)
            
        Returns:
            Polycom-formatted dial plan string
            
        Note:
            Currently passes through as-is. Can be enhanced to support
            format conversions between dial plan representations.
        """
        return dial_plan_str or ""

    def render(self, device: Any) -> str:
        """Render Polycom SoundPoint IP650 XML configuration.
        
        Args:
            device: Device model instance with site, lines, and configuration
            
        Returns:
            XML configuration string with <ALL> tag containing all attributes
        """
        # Get configuration values
        config = device.device_specific_configuration or {}
        site = device.site
        lines = list(device.lines.all())
        
        # Get common options
        clock_24hour = config.get("clock_24hour", True)
        date_format_label = config.get("date_format", "DD/MM/YYYY")
        syslog_server = config.get("syslog_server", "").strip()
        syslog_transport = config.get("syslog_transport", "UDP")
        syslog_facility = config.get("syslog_facility", 16)
        syslog_render_level = config.get("syslog_renderLevel", 2)
        codec_priority_order = config.get("codec_priority_order", [CODEC_G722, CODEC_G711A, CODEC_G711MU])
        sip_transport = config.get("sip_transport", "UDP")
        sip_register_expires = config.get("sip_register_expires", 3600)
        sip_retry_timeout = config.get("sip_retry_timeout", 30)
        
        # Get device-specific options
        admin_password = config.get("admin_password", "")
        user_password = config.get("user_password", "")
        
        # Map date format label to Polycom format
        date_format = "DD/MM/YYYY"
        for label, polycom_format in DATE_FORMAT_CHOICES:
            if label == date_format_label:
                date_format = polycom_format
                break
        
        # Calculate timezone info
        timezone_str = site.timezone if site else "UTC"
        gmt_offset = self._get_gmt_offset(timezone_str)
        dst_start_month, dst_start_day, dst_stop_month, dst_stop_day = self._calculate_dst_rules(timezone_str)
        
        # Map syslog transport
        syslog_transport_map = {"UDP": 1, "TCP": 2, "TLS": 3}
        syslog_transport_value = syslog_transport_map.get(syslog_transport, 1)
        
        # Map SIP transport
        sip_transport_map = {"UDP": 1, "TCP": 4}
        sip_transport_value = sip_transport_map.get(sip_transport, 1)
        
        # Convert retry timeout to milliseconds
        sip_retry_timeout_ms = sip_retry_timeout * 1000
        
        # Build codec priorities from orderedmultiselect array
        codec_map = {
            CODEC_G722: CODEC_G722_PRIORITY,
            CODEC_G711A: CODEC_G711A_PRIORITY,
            CODEC_G711MU: CODEC_G711MU_PRIORITY,
            CODEC_G729AB: CODEC_G729AB_PRIORITY,
        }
        
        codec_priorities = {
            CODEC_G722_PRIORITY: 0,
            CODEC_G711A_PRIORITY: 0,
            CODEC_G711MU_PRIORITY: 0,
            CODEC_G729AB_PRIORITY: 0,
        }
        
        # Iterate through ordered codec list and assign priorities
        if isinstance(codec_priority_order, list):
            for priority, codec in enumerate(codec_priority_order, start=1):
                if codec in codec_map:
                    codec_priorities[codec_map[codec]] = priority
        
        # Build attributes dictionary
        attrs = {
            # Language (hard-coded)
            "lcl.ml.lang": "en-gb",
            
            # Regional settings
            "lcl.datetime.time.24HourClock": "24" if clock_24hour else "12",
            "lcl.datetime.date.format": escape(date_format),
            
            # Timezone
            "tcpIpApp.sntp.gmtOffset": str(gmt_offset),
            "tcpIpApp.sntp.resyncPeriod": "14400",
            "tcpIpApp.sntp.daylightSavings.enable": "1",
            "tcpIpApp.sntp.daylightSavings.start.month": dst_start_month,
            "tcpIpApp.sntp.daylightSavings.start.date": dst_start_day,
            "tcpIpApp.sntp.daylightSavings.stop.month": dst_stop_month,
            "tcpIpApp.sntp.daylightSavings.stop.date": dst_stop_day,
            
            # NTP server
            "tcpIpApp.sntp.address": escape(site.primary_ntp_ip or "") if site else "",
            
            # Syslog
            "device.syslog.serverName": escape(syslog_server),
            "device.syslog.transport": str(syslog_transport_value),
            "device.syslog.facility": str(syslog_facility),
            "device.syslog.renderLevel": str(syslog_render_level),
            
            # Tag serial number (hard-coded)
            "log.render.file.tagSerialNo": "1",
            
            # SIP parameters
            "tcpIpApp.port.sip.transport": str(sip_transport_value),
            "voIpProt.SIP.serverFeatureControl.dndOnCodeEnabled": "1",
            "voIpProt.SIP.serverFeatureControl.dndOffCodeEnabled": "1",
            "voIpProt.SIP.serverFeatureControl.cfwdOnCodeEnabled": "1",
            "voIpProt.SIP.serverFeatureControl.cfwdOffCodeEnabled": "1",
            
            # Codecs
            CODEC_G722_PRIORITY: str(codec_priorities[CODEC_G722_PRIORITY]),
            CODEC_G711A_PRIORITY: str(codec_priorities[CODEC_G711A_PRIORITY]),
            CODEC_G711MU_PRIORITY: str(codec_priorities[CODEC_G711MU_PRIORITY]),
            CODEC_G729AB_PRIORITY: str(codec_priorities[CODEC_G729AB_PRIORITY]),
            
            # Admin passwords
            "device.auth.localAdminPassword": escape(admin_password),
            "device.auth.localUserPassword": escape(user_password),
            
            # Dial plan timeout
            "dialplan.digitmap.timeOut": "3",
        }
        
        # Conditionally add syslog.prependMac only if syslog_server is not empty
        if syslog_server:
            attrs["device.syslog.prependMac"] = "1"
        
        # Add SIP server from site
        if site and site.primary_sip_server:
            sip_server = site.primary_sip_server
            attrs["voIpProt.server.1.address"] = escape(sip_server.host)
            attrs["voIpProt.server.1.port"] = str(sip_server.port)
        
        # Add line configurations (up to 6 lines)
        for idx in range(1, 7):
            line_num = idx
            
            # Get line if available
            if idx <= len(lines):
                line = lines[idx - 1]
                
                # Registration parameters
                attrs[f"reg.{line_num}.server.1.register"] = "1"
                attrs[f"reg.{line_num}.server.1.expires"] = str(sip_register_expires)
                attrs[f"reg.{line_num}.server.1.retryTimeOut"] = str(sip_retry_timeout_ms)
                attrs[f"reg.{line_num}.displayName"] = escape(line.name or "")
                attrs[f"reg.{line_num}.address"] = escape(line.directory_number or "")
                attrs[f"reg.{line_num}.auth.userId"] = escape(line.registration_account or "")
                attrs[f"reg.{line_num}.auth.password"] = escape(line.registration_password or "")
                attrs[f"reg.{line_num}.type"] = "shared" if line.is_shared else "private"
                
                # Line label from device config or line phone_label
                line_label = config.get(f"line_{line_num}_label", "") or line.phone_label or ""
                attrs[f"reg.{line_num}.label"] = escape(line_label)
                
                # Ring tone
                ring_tone_label = config.get(f"line_{line_num}_ring_tone", "Low Trill")
                ring_tone_value = 1  # Default to Low Trill (enum value 1)
                if ring_tone_label in RING_TONES:
                    # Map ring tone to Polycom enum values: Low Trill=1, Low Double Trill=4, etc.
                    ring_tone_enum_values = [1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
                    ring_tone_index = RING_TONES.index(ring_tone_label)
                    ring_tone_value = ring_tone_enum_values[ring_tone_index]
                attrs[f"se.rt.{line_num}.name"] = str(ring_tone_value)
                
                # Dial plan (if available)
                if site and site.dial_plan:
                    dial_plan = self._convert_dial_plan(site.dial_plan.pattern or "")
                    attrs[f"dialplan.{line_num}.digitmap"] = escape(dial_plan)
            else:
                # Disable unused line
                attrs[f"reg.{line_num}.server.1.register"] = "0"
        
        # Build XML
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append("<PHONE_CONFIG>")
        xml_lines.append("<ALL")
        
        # Add all attributes
        for key, value in sorted(attrs.items()):
            xml_lines.append(f'    {key}="{value}"')
        
        xml_lines.append("/>")
        xml_lines.append("</PHONE_CONFIG>")
        
        return "\n".join(xml_lines)
