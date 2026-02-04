# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Polycom SoundPoint IP650 device type renderer."""
from typing import Any, Dict
import calendar
from datetime import datetime, timedelta
from xml.sax.saxutils import escape
import re
import pytz
from pytz import AmbiguousTimeError, NonExistentTimeError

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
    ("Mon, 1 Jan", "D,dM"),
    ("Mon, Jan 1", "D,Md"),
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
                {
                    "optionId": "use_long_format",
                    "friendlyName": "Use Long Format (January/Jan, Tuesday/Tue)",
                    "default": True,
                    "mandatory": False,
                    "type": "checkbox",
                    "uiOrder": 3,
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
                    "friendlyName": "Logging Level",
                    "default": "Minor Error",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 4,
                    "options": [
                        "Debug",
                        "Event 1",
                        "Event 2",
                        "Event 3",
                        "Minor Error",
                        "Major Error",
                        "Fatal Error",
                    ],
                },
            ],
        },
        {
            "friendlyName": "SIP Parameters",
            "uiOrder": 3,
            "options": [
                {
                    "optionId": "sip_register_expires",
                    "friendlyName": "SIP Registration Expiry (seconds)",
                    "default": 3600,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 1,
                },
                {
                    "optionId": "sip_retry_timeout",
                    "friendlyName": "SIP Retry Timeout (seconds)",
                    "default": 30,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
                {
                    "optionId": "sip_local_port",
                    "friendlyName": "Local SIP Port",
                    "default": 5060,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 5,
                },
                {
                    "optionId": "sip_use_rfc2543_hold",
                    "friendlyName": "Use RFC2543 Hold",
                    "default": True,
                    "mandatory": False,
                    "type": "checkbox",
                    "uiOrder": 4,
                },
                {
                    "optionId": "sip_max_retries",
                    "friendlyName": "Maximum number of retries",
                    "default": 3,
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
        {
            "friendlyName": "Dial Plan",
            "uiOrder": 5,
            "options": [
                {
                    "optionId": "inter_digit_timeout",
                    "friendlyName": "Inter-Digit timeout",
                    "default": 3,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 1,
                },
            ],
        },
        {
            "friendlyName": "Device Appearance",
            "uiOrder": 6,
            "options": [
                {
                    "optionId": "calls_per_line_key",
                    "friendlyName": "# of Calls per Line",
                    "default": 4,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 1,
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
                    "optionId": "line_1_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 1,
                    "options": RING_TONES,
                },
                {
                    "optionId": "line_1_keys",
                    "friendlyName": "Keys per Line",
                    "default": 1,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
            ],
        },
        {
            "friendlyName": "Line 2 Configuration",
            "uiOrder": 3,
            "options": [
                {
                    "optionId": "line_2_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 1,
                    "options": RING_TONES,
                },
                {
                    "optionId": "line_2_keys",
                    "friendlyName": "Keys per Line",
                    "default": 1,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
            ],
        },
        {
            "friendlyName": "Line 3 Configuration",
            "uiOrder": 4,
            "options": [
                {
                    "optionId": "line_3_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 1,
                    "options": RING_TONES,
                },
                {
                    "optionId": "line_3_keys",
                    "friendlyName": "Keys per Line",
                    "default": 1,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
            ],
        },
        {
            "friendlyName": "Line 4 Configuration",
            "uiOrder": 5,
            "options": [
                {
                    "optionId": "line_4_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 1,
                    "options": RING_TONES,
                },
                {
                    "optionId": "line_4_keys",
                    "friendlyName": "Keys per Line",
                    "default": 1,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
            ],
        },
        {
            "friendlyName": "Line 5 Configuration",
            "uiOrder": 6,
            "options": [
                {
                    "optionId": "line_5_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 1,
                    "options": RING_TONES,
                },
                {
                    "optionId": "line_5_keys",
                    "friendlyName": "Keys per Line",
                    "default": 1,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
            ],
        },
        {
            "friendlyName": "Line 6 Configuration",
            "uiOrder": 7,
            "options": [
                {
                    "optionId": "line_6_ring_tone",
                    "friendlyName": RING_TONE,
                    "default": "Low Trill",
                    "mandatory": False,
                    "type": "select",
                    "uiOrder": 1,
                    "options": RING_TONES,
                },
                {
                    "optionId": "line_6_keys",
                    "friendlyName": "Keys per Line",
                    "default": 1,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
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
    UserAgentPatterns = (
        r"PolycomSoundPointIP",
        r"SPIP[_-]?650",
    )

    def _get_gmt_offset(self, timezone_str: str) -> str:
        """Calculate standard GMT offset in hours for a given timezone.
        
        Args:
            timezone_str: Timezone string (e.g., 'America/New_York')
            
        Returns:
            Offset in hours from GMT (string, may be fractional)
        """
        try:
            tz = pytz.timezone(timezone_str)
            year = datetime.now().year
            offsets = []
            standard_offsets = []
            for month in range(1, 13):
                sample = datetime(year, month, 15, 12, 0, 0)
                local = tz.localize(sample, is_dst=None)
                offset = local.utcoffset() or timedelta(0)
                offsets.append(offset)
                if (local.dst() or timedelta(0)) == timedelta(0):
                    standard_offsets.append(offset)
            base_offset = standard_offsets[0] if standard_offsets else min(offsets, default=timedelta(0))
            hours = base_offset.total_seconds() / 3600
            return f"{hours:g}"
        except Exception:
            return "0"  # Default to GMT if timezone invalid

    def _calculate_dst_rules(self, timezone_str: str) -> Dict[str, str]:
        """Calculate DST start/end rules for a timezone.
        
        Returns:
            Dict of DST rule fields for Polycom.
        """
        try:
            tz = pytz.timezone(timezone_str)
            year = datetime.now().year
            start_transition = None
            stop_transition = None
            last_dst = None

            start_date = datetime(year, 1, 1, 0, 0, 0)
            for hour_offset in range(0, 366 * 24):
                naive = start_date + timedelta(hours=hour_offset)
                try:
                    local = tz.localize(naive, is_dst=None)
                except (AmbiguousTimeError, NonExistentTimeError):
                    try:
                        local = tz.localize(naive, is_dst=True)
                    except Exception:
                        continue

                dst_offset = local.dst() or timedelta(0)
                if last_dst is None:
                    last_dst = dst_offset
                    continue

                if dst_offset != last_dst:
                    if dst_offset > last_dst:
                        start_transition = local
                    else:
                        stop_transition = local
                    last_dst = dst_offset
                    if start_transition and stop_transition:
                        break

            if not start_transition or not stop_transition:
                return {
                    "enable": "0",
                    "start_day_of_week": "1",
                    "start_month": "1",
                    "start_time": "0",
                    "start_date": "1",
                    "start_last_in_month": "0",
                    "stop_day_of_week": "1",
                    "stop_month": "1",
                    "stop_time": "0",
                    "stop_date": "1",
                    "stop_last_in_month": "0",
                }

            def build_rule(dt: datetime) -> Dict[str, str]:
                day_of_week = ((dt.weekday() + 1) % 7) + 1  # Sunday=1
                day = dt.day
                week_index = (day - 1) // 7
                week_value = 1 + min(week_index, 3) * 7
                days_in_month = calendar.monthrange(dt.year, dt.month)[1]
                last_in_month = "1" if day + 7 > days_in_month else "0"
                return {
                    "day_of_week": str(day_of_week),
                    "month": str(dt.month),
                    "time": str(dt.hour),
                    "date": str(week_value),
                    "last_in_month": last_in_month,
                }

            start_rule = build_rule(start_transition)
            stop_rule = build_rule(stop_transition)

            return {
                "enable": "1",
                "start_day_of_week": start_rule["day_of_week"],
                "start_month": start_rule["month"],
                "start_time": start_rule["time"],
                "start_date": start_rule["date"],
                "start_last_in_month": start_rule["last_in_month"],
                "stop_day_of_week": stop_rule["day_of_week"],
                "stop_month": stop_rule["month"],
                "stop_time": stop_rule["time"],
                "stop_date": stop_rule["date"],
                "stop_last_in_month": stop_rule["last_in_month"],
            }
        except Exception:
            return {
                "enable": "0",
                "start_day_of_week": "1",
                "start_month": "1",
                "start_time": "0",
                "start_date": "1",
                "start_last_in_month": "0",
                "stop_day_of_week": "1",
                "stop_month": "1",
                "stop_time": "0",
                "stop_date": "1",
                "stop_last_in_month": "0",
            }

    def _convert_dial_plan_rule(self, input_regex: str, output_regex: str) -> str:
        """Convert a dial plan rule to a Polycom digitmap entry.

        Args:
            input_regex: Input regex (standard format with anchors, X, *, [], [^])
            output_regex: Output regex with $1 substitutions

        Returns:
            Polycom digitmap entry string (may include replacement prefix and T suffix).
        """
        if not input_regex:
            return ""

        raw_input = (input_regex or "").strip()
        raw_output = (output_regex or "").strip()

        # Remove anchors
        cleaned = raw_input.replace("^", "").replace("$", "")

        def build_replace(find: str, replace: str) -> str:
            return f"R{find}R{replace}R"

        def normalize_pattern(pattern: str) -> tuple[str, bool]:
            if not pattern:
                return "", False
            needs_timeout = pattern.endswith("*")
            if needs_timeout:
                pattern = pattern[:-1]
            pattern = pattern.replace("X", "x")
            return pattern, needs_timeout

        replacement_prefix = ""
        match_pattern = cleaned
        timeout_required = False

        capture_match = re.match(r"^([^(]*)\(([^()]*)\)$", cleaned)
        if capture_match:
            prefix = capture_match.group(1)
            captured = capture_match.group(2)

            match_pattern, timeout_required = normalize_pattern(captured)

            if "$1" in raw_output:
                output_prefix = raw_output.replace("$1", "")
                if prefix or output_prefix:
                    replacement_prefix = build_replace(prefix, output_prefix)
        else:
            match_pattern, timeout_required = normalize_pattern(cleaned)

            if raw_output and raw_output != cleaned:
                if raw_output.endswith(match_pattern):
                    output_prefix = raw_output[: -len(match_pattern)]
                    replacement_prefix = build_replace("", output_prefix)

        if not match_pattern:
            return ""

        digitmap = f"{replacement_prefix}{match_pattern}"
        if timeout_required:
            digitmap += "T"

        return digitmap

    def render(self, device: Any) -> str:
        """Render Polycom SoundPoint IP650 XML configuration.
        
        Args:
            device: Device model instance with site, lines, and configuration
            
        Returns:
            XML configuration string with <ALL> tag containing all attributes
        """
        # Get configuration values (decrypt password fields)
        config = device.get_decrypted_device_config()
        site = device.site
        lines = []
        seen_line_ids = set()
        if device.line_1:
            lines.append(device.line_1)
            seen_line_ids.add(device.line_1.id)
        for extra_line in device.lines.all().order_by("directory_number"):
            if extra_line.id in seen_line_ids:
                continue
            lines.append(extra_line)
            seen_line_ids.add(extra_line.id)
        
        # Get common options
        clock_24hour = config.get("clock_24hour", True)
        date_format_label = config.get("date_format", "DD/MM/YYYY")
        syslog_server = config.get("syslog_server", "").strip()
        syslog_transport = config.get("syslog_transport", "UDP")
        syslog_facility = config.get("syslog_facility", 16)
        syslog_render_level_label = config.get("syslog_renderLevel", "Minor Error")
        
        # Map logging level friendly name to numeric value
        syslog_level_map = {
            "Debug": 0,
            "Event 1": 1,
            "Event 2": 2,
            "Event 3": 3,
            "Minor Error": 4,
            "Major Error": 5,
            "Fatal Error": 6,
        }
        syslog_render_level = syslog_level_map.get(syslog_render_level_label, 4)
        
        codec_priority_order = config.get("codec_priority_order", [CODEC_G722, CODEC_G711A, CODEC_G711MU])
        sip_register_expires = config.get("sip_register_expires", 3600)
        sip_retry_timeout = config.get("sip_retry_timeout", 30)
        sip_local_port = int(config.get("sip_local_port", 5060))
        sip_use_rfc2543_hold = config.get("sip_use_rfc2543_hold", True)
        sip_max_retries = int(config.get("sip_max_retries", 3))
        inter_digit_timeout = int(config.get("inter_digit_timeout", 3))
        use_long_format = config.get("use_long_format", True)
        calls_per_line_key = int(config.get("calls_per_line_key", 4))
        
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
        dst_rules = self._calculate_dst_rules(timezone_str)
        
        # Map syslog transport
        syslog_transport_map = {"UDP": 1, "TCP": 2, "TLS": 3}
        syslog_transport_value = syslog_transport_map.get(syslog_transport, 1)
        
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
            # We are setting device parameters
            "device.set": "1",

            # Language (hard-coded)
            "lcl.ml.lang": "en-gb",
            
            # Regional settings
            "lcl.datetime.time.24HourClock": "1" if clock_24hour else "0",
            "lcl.datetime.date.format": escape(date_format),
            "lcl.ml.lang.clock.5.longFormat": "1" if use_long_format else "0",
            
            # Timezone
            "tcpIpApp.sntp.gmtOffset.overrideDHCP": "1",
            "tcpIpApp.sntp.gmtOffset": int(gmt_offset) * 3600,  # device expects in seconds
            "tcpIpApp.sntp.resyncPeriod": "14400",
            "tcpIpApp.sntp.daylightSavings.enable": dst_rules["enable"],
            "tcpIpApp.sntp.daylightSavings.start.dayOfWeek": dst_rules["start_day_of_week"],
            "tcpIpApp.sntp.daylightSavings.start.month": dst_rules["start_month"],
            "tcpIpApp.sntp.daylightSavings.start.time": dst_rules["start_time"],
            "tcpIpApp.sntp.daylightSavings.start.date": dst_rules["start_date"],
            "tcpIpApp.sntp.daylightSavings.start.dayOfWeek.lastInMonth": dst_rules["start_last_in_month"],
            "tcpIpApp.sntp.daylightSavings.stop.dayOfWeek": dst_rules["stop_day_of_week"],
            "tcpIpApp.sntp.daylightSavings.stop.month": dst_rules["stop_month"],
            "tcpIpApp.sntp.daylightSavings.stop.time": dst_rules["stop_time"],
            "tcpIpApp.sntp.daylightSavings.stop.date": dst_rules["stop_date"],
            "tcpIpApp.sntp.daylightSavings.stop.dayOfWeek.lastInMonth": dst_rules["stop_last_in_month"],
            
            # NTP server
            "tcpIpApp.sntp.address": escape(site.primary_ntp_ip or "") if site else "",
            "tcpIpApp.sntp.address.overrideDHCP": "1" if site.primary_ntp_ip else "0",
            
            # Tag serial number (hard-coded)
            "log.render.file.tagSerialNo": "1",
            
            # Codecs
            CODEC_G722_PRIORITY: str(codec_priorities[CODEC_G722_PRIORITY]),
            CODEC_G711A_PRIORITY: str(codec_priorities[CODEC_G711A_PRIORITY]),
            CODEC_G711MU_PRIORITY: str(codec_priorities[CODEC_G711MU_PRIORITY]),
            CODEC_G729AB_PRIORITY: str(codec_priorities[CODEC_G729AB_PRIORITY]),
            
            # Admin passwords
            "device.auth.localAdminPassword": escape(admin_password),
            "device.auth.localUserPassword": escape(user_password),
            
            # SIP parameters
            "voIpProt.SIP.local.port": str(sip_local_port),
            "voIpProt.SIP.useRFC2543hold": "1" if sip_use_rfc2543_hold else "0",
            "voIpProt.server.1.retryMaxCount": str(sip_max_retries),
            "voIpProt.server.2.retryMaxCount": str(sip_max_retries),
            
            # Device appearance
            "call.callsPerLineKey": str(calls_per_line_key),
            
        }
        
        # Syslog options only when serverName is defined
        if syslog_server:
            attrs["device.syslog.serverName"] = escape(syslog_server)
            attrs["device.syslog.transport"] = str(syslog_transport_value)
            attrs["device.syslog.facility"] = str(syslog_facility)
            attrs["device.syslog.renderLevel"] = str(syslog_render_level)
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
                
                # Line label from line.phone_label or fallback to line.name
                line_label = line.phone_label or line.name or ""
                attrs[f"reg.{line_num}.label"] = escape(line_label)
                
                # Line keys per line
                line_keys = config.get(f"line_{line_num}_keys", 1)
                attrs[f"reg.{line_num}.lineKeys"] = str(line_keys)
                
                # Ring tone
                ring_tone_label = config.get(f"line_{line_num}_ring_tone", "Low Trill")
                ring_tone_value = 1  # Default to Low Trill (enum value 1)
                if ring_tone_label in RING_TONES:
                    # Map ring tone to Polycom enum values: Low Trill=1, Low Double Trill=4, etc.
                    ring_tone_enum_values = [1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
                    ring_tone_index = RING_TONES.index(ring_tone_label)
                    ring_tone_value = ring_tone_enum_values[ring_tone_index]
                attrs[f"se.rt.{line_num}.name"] = str(ring_tone_value)
                
            else:
                # Disable unused line
                attrs[f"reg.{line_num}.server.1.register"] = "0"

        # Dial plan (global digitmap)
        if site and site.dial_plan:
            rules = site.dial_plan.rules.all().order_by("sequence_order")
            digitmaps: list[str] = []
            for rule in rules:
                digitmap_entry = self._convert_dial_plan_rule(rule.input_regex, rule.output_regex)
                if digitmap_entry:
                    digitmaps.append(digitmap_entry)

            if digitmaps:
                attrs["dialplan.digitmap"] = escape(f"{ '|'.join(digitmaps) }")
                attrs["dialplan.digitmap.timeOut"] = "|".join(
                    str(inter_digit_timeout) for _ in digitmaps
                )
        
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
