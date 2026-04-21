# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Yealink SIP-T33G device type renderer.

"""
from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime
import re

import pytz

from core.models import SIPServer
from .base import DeviceType


COMMON_OPTIONS: Dict[str, Any] = {
    "sections": [
        {
            "friendlyName": "SIP Parameters",
            "uiOrder": 1,
            "options": [
                {
                    "optionId": "hold_inactive",
                    "friendlyName": "RFC 2543 Hold (0.0.0.0)",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                },
                {
                    "optionId": "enable_user_equal_phone",
                    "friendlyName": "Send user=phone",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 2,
                },			
                {
                    "optionId": "enable_rport",
                    "friendlyName": "RPort",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 3,
                },
                {
                    "optionId": "server_expires",
                    "friendlyName": "Registration Expiry (s)",
                    "default": 600,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 4,
                },
                {
                    "optionId": "registration_random_seconds",
                    "friendlyName": "Registration Randomisation (s)",
                    "default": 6,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 5,
                },
                {
                    "optionId": "reg_fail_retry_interval",
                    "friendlyName": "Register Retry Interval (s)",
                    "default": 30,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 6,
                },				
                {
                    "optionId": "retry_counts",
                    "friendlyName": "Registery Retry Count",
                    "default": 3,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 7,
                },
                {
                    "optionId": "session_timer_enable",
                    "friendlyName": "Session Timer",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 8,
                },
                {
                    "optionId": "session_expires",
                    "friendlyName": "Session Expires (s)",
                    "default": 1800,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 9,
                },
                {
                    "optionId": "session_refresher",
                    "friendlyName": "Session Refresher",
                    "default": "UAC",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["UAS", "UAC"],
                    "uiOrder": 10,
                },
                {
                    "optionId": "nat_udp_update_type",
                    "friendlyName": "Keep Alive Type",
                    "default": "Options",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["Disabled", "Default","Options","Notify"],
                    "uiOrder": 11,
                },			
                {
                    "optionId": "nat_udp_update_time",
                    "friendlyName": "Keep Alive Timer (s)",
                    "default": 60,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 12,
                },	
			]
		},
        {
            "friendlyName": "High Availability",
            "uiOrder": 2,
            "options": [
                {
                    "optionId": "failover_type",
                    "friendlyName": "Failover Type",
                    "default": "Successive",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["Successive", "Concurrent"],
                    "uiOrder": 1,
                },
                {
                    "optionId": "failover_timeout",
                    "friendlyName": "Failover Timeout (s)",
                    "default": 30,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
                {
                    "optionId": "register_on_active",
                    "friendlyName": "Register on Active Server Only",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 3,
                },
                {  
                    "optionId": "signal_with_registered_only",
                    "friendlyName": "Signal with Registered Server Only",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 4,
                },
                {
                    "optionId": "invite_retry_count",
                    "friendlyName": "Invite Retry Count",
                    "default": 3,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 5,
                },
                {
                    "optionId": "failback_mode",
                    "friendlyName": "Failback Mode",
                    "default": "Duration",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["New Requests", "DNS TTL", "Registration", "Duration"],
                    "uiOrder": 6,
                },
                { 
                    "optionId": "failback_duration",
                    "friendlyName": "Failback Duration (min)",
                    "default": 10,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 7,
                },
                
            ]
        },
        {
            "friendlyName": "RTP Parameters",
            "uiOrder": 3,
            "options": [
                {
                    "optionId": "dtmf_type",
                    "friendlyName": "DTMF Type",
                    "default": "RFC2833",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["RFC2833", "SIP_INFO", "Inband", "RFC2833+SIP_INFO"],
                    "uiOrder": 1,
                },
                {
                    "optionId": "dtmf_payload",
                    "friendlyName": "DTMF Payload",
                    "default": 101,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },	
                {
                    "optionId": "srtp_mode",
                    "friendlyName": "RTP Encryption",
                    "default": "Disabled",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["Disabled", "Optional", "SRTP"],
                    "uiOrder": 3,
                },
                {
                    "optionId": "early_media",
                    "friendlyName": "Early Media",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 4,
                },
                {
                    "optionId": "preferred_codecs",
                    "friendlyName": "Preferred Codec Order",
                    "default": ["PCMA", "PCMU", "G722"],
                    "mandatory": True,
                    "type": "orderedmultiselect",
                    "choices": [
                        "PCMA",
                        "PCMU",
                        "G729",
                        "G722",
                        "iLBC",
                        "G723_53",
                        "G723_63",
                        "Opus",
                    ],
                    "uiOrder": 5,
                },
			]
		},		
        {
            "friendlyName": "Network",
            "uiOrder": 4,
            "options": [
                {
                    "optionId": "network_port_http",
                    "friendlyName": "HTTP Server Port",
                    "default": 8080,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 1,
                },
                {
                    "optionId": "network_port_https",
                    "friendlyName": "HTTPS Server Port",
                    "default": 8443,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
				},
                {
                    "optionId": "rtp_port_min",
                    "friendlyName": "Local RTP Port Min",
                    "default": 16384,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 3,
                },
                {
                    "optionId": "rtp_port_max",
                    "friendlyName": "Local RTP Port Max",
                    "default": 32767,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 4,
                },                
                {
                    "optionId": "sip_qos_dscp",
                    "friendlyName": "SIP QoS DSCP",
                    "default": 26,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 5,
                },
                {
                    "optionId": "voice_qos_dscp",
                    "friendlyName": "RTP QoS DSCP",
                    "default": 46,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 6,
                },
				
			]
		},
        {
            "friendlyName": "RTCP-XR (Voice Quality Report)",
            "uiOrder": 5,
            "options": [
                {
                    "optionId": "vq_rtcp_xr_enable",
                    "friendlyName": "Enable Voice Quality Reports",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                },
                {
                    "optionId": "vq_rtcpxr_interval_report_enable",
                    "friendlyName": "Enable Interval Reports",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 2,
                },
                {
                    "optionId": "vq_rtcpxr_states_show_on_gui_enable",
                    "friendlyName": "Show Status on Phone",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 3,
                },
                {
                    "optionId": "vq_rtcpxr_states_show_on_web_enable",
                    "friendlyName": "Show Status on WebUI",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 4,
                },
                {
                    "optionId": "vq_rtcpxr_interval_period",
                    "friendlyName": "Interval Period (s)",
                    "default": 15,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 5,
                }
			]
		}
	]
}


DEVICE_OPTIONS: Dict[str, Any] = {
    "sections": [
        {
            "friendlyName": "Date and Time",
            "uiOrder": 1,
            "options": [
                {
                    "optionId": "local_time_format",
                    "friendlyName": "Time Format",
                    "default": "24 Hour",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["24 Hour", "12 Hour"],
                    "uiOrder": 1,
                },		                
                {
                    "optionId": "local_date_format",
                    "friendlyName": "Date Format",
                    "default": "DD MMM YYYY",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["WWW MMM DD", "DD-MMM-YY", "YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YY", "DD MMM YYYY", "WWW DD MMM"],
                    "uiOrder": 1,
                },		                
			]
		},
        {
            "friendlyName": "Features",
            "uiOrder": 2,
            "options": [
               {
                    "optionId": "call_waiting",
                    "friendlyName": "Call Waiting",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                },
                {
                    "optionId": "missed_calllog_enable",
                    "friendlyName": "Enable Missed Call Log",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 2,
                },
                {
                    "optionId": "save_call_log",
                    "friendlyName": "Save Call Log",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 3,
                },                
			]
		},
		{
            "friendlyName": "Administrative",
            "uiOrder": 3,
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
                    "optionId": "voice_country",
                    "friendlyName": "Voice Tones Country",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 2,
                }
            ]
        },
		{
            "friendlyName": "Network",
            "uiOrder": 4,
            "options": [
                {
                    "optionId": "lldp_active",
                    "friendlyName": "LLDP Active",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                },
                {
                    "optionId": "cdp_active",
                    "friendlyName": "CDP Active",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 2,
                },
                {
                    "optionId": "web_http_enable",
                    "friendlyName": "Enable HTTP Server",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 3,
                },
                {
                    "optionId": "web_https_enable",
                    "friendlyName": "Enable HTTPS Server",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 4,
                },
				{
                    "optionId": "dhcp_hostname",
                    "friendlyName": "DHCP Hostname",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 5,
                },                
			]
		},
		{
            "friendlyName": "Syslog",
            "uiOrder": 5,
            "options": [
                {
                    "optionId": "syslog_enable",
                    "friendlyName": "Enable Syslog",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                },
                {
                    "optionId": "syslog_server",
                    "friendlyName": "Syslog Server",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 2,
                },
                {
                    "optionId": "syslog_server_port",
                    "friendlyName": "Syslog Server Port",
                    "default": 514,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 3,
                },
                {
                    "optionId": "syslog_transport_type",
                    "friendlyName": "Syslog Transport Type",
                    "default": "UDP",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["UDP", "TCP", "TLS"],
                    "uiOrder": 4,
                }
            ]
        },
	]
}


class YealinkSIPT33G(DeviceType):
    TypeID = "YealinkSIPT33G"
    Manufacturer = "Yealink"
    Model = "SIP-T33G"
    NumberOfLines = 4
    SupportsSIPServersPerLine = True
    CommonOptions = COMMON_OPTIONS
    DeviceSpecificOptions = DEVICE_OPTIONS
    ContentType = "text/plain"
    UserAgentPatterns = (
        r"Yealink[/ ]SIP[- ]?T33G",
    )

    def render(self, device: Any) -> str:
        # Pull decrypted device-specific configuration (includes admin password)
        cfg = device.get_decrypted_device_config() if hasattr(device, "get_decrypted_device_config") else (
            device.device_specific_configuration or {}
        )

        def opt(key: str, default: Any) -> Any:
            return cfg.get(key, default)

        def bool_flag(value: Any) -> str:
            return "1" if bool(value) else "0"

        def convert_yealink_input_regex(pattern: str) -> str:
            if not pattern:
                return ""

            converted = pattern.replace("^", "").replace("$", "")
            converted = converted.replace("*", ".").replace("X", "x")

            def normalize_bracket(match: re.Match[str]) -> str:
                content = match.group(1)
                if not content:
                    return "[]"

                negation = ""
                body = content
                if body.startswith("^"):
                    negation = "^"
                    body = body[1:]

                if "-" in body or "," in body or len(body) <= 1:
                    return f"[{negation}{body}]"

                return f"[{negation}{','.join(list(body))}]"

            return re.sub(r"\[([^\]]*)\]", normalize_bracket, converted)

        def convert_yealink_output_regex(pattern: str) -> str:
            if not pattern:
                return ""
            return pattern.replace("X", "x")

        def get_timezone_config(tz_name: str) -> dict[str, Any]:
            """
            Calculate Yealink timezone and DST configuration.
            Returns dict with all required timezone parameters for Yealink phones.
            
            Yealink format:
            - time_zone: Standard UTC offset as integer (e.g., +10, -5)
            - summer_time: 0=no DST, 1=uses DST, 2=auto-detect
            - dst_time_type: 1=DST by day-of-week (only supported mode)
            - start_time: DST start as "month/week/dow/hour" (e.g., "10/1/7/2" = Oct 1st Sunday 2am)
            - end_time: DST end as "month/week/dow/hour"
            - offset_time: DST offset in minutes (typically 60)
            - manual_ntp_srv_prior: 1 = use manual NTP servers
            """
            try:
                tz = pytz.timezone(tz_name)
                
                # Sample two dates to detect DST pattern
                jan_naive = datetime(2026, 1, 15, 12, 0, 0)
                jul_naive = datetime(2026, 7, 15, 12, 0, 0)
                
                jan_date = tz.localize(jan_naive)
                jul_date = tz.localize(jul_naive)
                
                jan_offset_hours = jan_date.utcoffset().total_seconds() / 3600
                jul_offset_hours = jul_date.utcoffset().total_seconds() / 3600
                
                # Standard time is the smaller offset (closer to UTC)
                standard_offset_hours = min(jan_offset_hours, jul_offset_hours)
                
                # Check if timezone observes DST
                observes_dst = (jan_offset_hours != jul_offset_hours)
                
                config = {
                    "time_zone": f"{int(standard_offset_hours):+d}",  # Format as +10, -5, etc.
                    "summer_time": 1 if observes_dst else 0,  # 1=uses DST, 0=no DST
                    "dst_time_type": 1 if observes_dst else 0,  # 1=DST by day-of-week
                    "offset_time": 60 if observes_dst else 0,  # DST offset in minutes
                    "manual_ntp_srv_prior": 1,  # Use manual NTP servers
                }
                
                if observes_dst:
                    # For timezones with DST, determine transition dates
                    # Try to find the actual DST transitions using pytz transition info
                    # Fallback: Use reasonable defaults for Northern/Southern hemisphere patterns
                    
                    # Get the transition info from pytz
                    import inspect
                    try:
                        # pytz stores transitions in _utc_transition_times
                        transitions = tz._utc_transition_times
                        trans_info = tz._transition_info
                        
                        # Find 2026 transitions (current and next)
                        spring_trans = None  # Earlier transition (spring for NH, autumn for SH)
                        autumn_trans = None  # Later transition (autumn for NH, spring for SH)
                        
                        for i, trans_time in enumerate(transitions):
                            if trans_time.year == 2026:
                                # This transition is in 2026
                                trans_utc = trans_time
                                next_offset = trans_info[i][0].total_seconds() / 3600
                                
                                # Determine if this is spring-forward or fall-back
                                if i > 0:
                                    prev_offset = trans_info[i - 1][0].total_seconds() / 3600
                                    
                                    if next_offset > prev_offset:  # Spring forward (DST starts)
                                        spring_trans = trans_time
                                    else:  # Fall back (DST ends)
                                        autumn_trans = trans_time
                        
                        # If we found both transitions, use them
                        if spring_trans and autumn_trans:
                            # Ensure spring comes before autumn in the calendar year
                            if spring_trans.month > autumn_trans.month:
                                spring_trans, autumn_trans = autumn_trans, spring_trans
                            
                            config["start_time"] = format_dst_transition(spring_trans)
                            config["end_time"] = format_dst_transition(autumn_trans)
                        else:
                            # Fallback: Use common patterns
                            if standard_offset_hours > 0:  # Likely Northern Hemisphere
                                config["start_time"] = "3/2/7/2"  # 2nd Sunday in March at 2am
                                config["end_time"] = "11/1/7/2"   # 1st Sunday in November at 2am
                            else:  # Likely Southern Hemisphere
                                config["start_time"] = "10/1/7/2"  # 1st Sunday in October at 2am
                                config["end_time"] = "4/1/7/3"     # 1st Sunday in April at 3am
                    except (AttributeError, Exception):
                        # Fallback if transition info unavailable
                        if standard_offset_hours > 0:
                            config["start_time"] = "3/2/7/2"
                            config["end_time"] = "11/1/7/2"
                        else:
                            config["start_time"] = "10/1/7/2"
                            config["end_time"] = "4/1/7/3"
                
                return config
            except Exception:
                # Fallback to UTC if timezone parsing fails
                return {
                    "time_zone": "+0",
                    "summer_time": 0,
                    "dst_time_type": 0,
                    "offset_time": 0,
                    "manual_ntp_srv_prior": 1,
                    "start_time": "",
                    "end_time": "",
                }
        
        def format_dst_transition(dt: datetime) -> str:
            """
            Format a datetime as Yealink DST transition string: month/week/dow/hour
            
            month: 1-12
            week: 1-5 (1=first, 2=second, etc.)
            dow: 7=Sunday, 1=Monday, ..., 6=Saturday
            hour: 0-23
            
            This function approximates the week number based on the date.
            """
            month = dt.month
            day = dt.day
            hour = dt.hour
            dow = dt.weekday() + 1 if dt.weekday() < 6 else 7  # Convert Python weekday to Yealink (7=Sun)
            
            # Calculate week number (1-5) for this day of month
            week = (day - 1) // 7 + 1
            
            return f"{month}/{week}/{dow}/{hour}"

        transport_map = {"UDP": 0, "TCP": 1, "TLS": 2}
        dtmf_map = {"RFC2833": 1, "SIP_INFO": 2, "Inband": 0, "RFC2833+SIP_INFO": 3}
        srtp_map = {"Disabled": 0, "Optional": 1, "SRTP": 2}
        refresher_map = {"UAS": 1, "UAC": 0}
        keepalive_map = {"Disabled": 0, "Default": 1,"Options": 2,"Notify": 3}
        timeformat_map = {"24 Hour": 1, "12 Hour": 0}
        dateformat_map = {
            "WWW MMM DD": 0,
            "DD-MMM-YY": 1,
            "YYYY-MM-DD": 2,
            "DD/MM/YYYY": 3,
            "MM/DD/YY": 4,
            "DD MMM YYYY": 5,
            "WWW DD MMM": 6,
        }
        redudancy_type_map = {"Successive": 1, "Concurrent": 0}
        failback_mode_map = {"New Requests": 0, "DNS TTL": 1, "Registration": 2, "Duration": 3}
        

        def normalize_codec_name(codec: Any) -> str:
            if not isinstance(codec, str):
                return ""
            return (
                codec.strip()
                .upper()
                .replace(" ", "")
                .replace("-", "")
                .replace(".", "_")
            )

        codec_map: Dict[str, tuple[str, int | None]] = {
            "PCMU": ("pcmu", 0),
            "PCMA": ("pcma", 8),
            "G722": ("g722", 9),
            "G729": ("g729ilbc", 18),
            "G729ILBC": ("g729ilbc", 18),
            "ILBC": ("g729ilbc", 97),
            "G723_53": ("g723_53", 4),
            "G723_63": ("g723_63", 4),
            "OPUS": ("opus", 116),
        }

        preferred_codecs_raw = opt("preferred_codecs", ["PCMA", "PCMU", "G722"])
        preferred_codecs: List[str] = []
        seen_codecs: set[str] = set()
        for raw_codec in preferred_codecs_raw:
            normalized = normalize_codec_name(raw_codec)
            if not normalized or normalized in seen_codecs:
                continue
            seen_codecs.add(normalized)
            preferred_codecs.append(normalized)

        all_codec_types = sorted({mapping[0] for mapping in codec_map.values()})


        site = device.site
        primary = site.primary_sip_server
        secondary = getattr(site, "secondary_sip_server", None)

        line_configuration = getattr(device, "line_configuration", {}) or {}
        override_server_ids = set()
        for line_key, line_cfg in line_configuration.items():
            if not isinstance(line_cfg, dict) or not line_cfg.get("use_different_sip_server"):
                continue
            primary_id = line_cfg.get("primary_sip_server")
            secondary_id = line_cfg.get("secondary_sip_server")
            if primary_id:
                override_server_ids.add(primary_id)
            if secondary_id:
                override_server_ids.add(secondary_id)
        sip_server_map = {
            srv.id: srv for srv in SIPServer.objects.filter(id__in=override_server_ids)
        }

        def get_line_sip_servers(line_number: int):
            if line_number <= 1:
                return primary, secondary

            line_cfg = line_configuration.get(str(line_number))
            if not isinstance(line_cfg, dict) or not line_cfg.get("use_different_sip_server"):
                return primary, secondary

            selected_primary = sip_server_map.get(line_cfg.get("primary_sip_server"))
            if not selected_primary:
                return primary, secondary
            selected_secondary = sip_server_map.get(line_cfg.get("secondary_sip_server"))
            return selected_primary, selected_secondary



        # Network & QoS
        network_port_http = bool(opt("network_port_http", True))
        network_port_https = bool(opt("network_port_https", False))
        web_http_enable = bool(opt("web_http_enable", True))
        web_https_enable = bool(opt("web_https_enable", False))
        voice_qos_dscp = int(opt("voice_qos_dscp", 46))
        sip_qos_dscp = int(opt("sip_qos_dscp", 26))
        rtp_port_min = int(opt("rtp_port_min", 16384))
        rtp_port_max = int(opt("rtp_port_max", 32767))
        lldp_active = bool(opt("lldp_active", True))
        cdp_active = bool(opt("cdp_active", False))
        dhcp_hostname = opt("dhcp_hostname", "yealink-" + device.mac_address.replace(":", "")[-6:])

        # Failover
        failover_type = opt("failover_type", "Successive")
        failover_timeout = int(opt("failover_timeout", 30))
        register_on_active = bool(opt("register_on_active", True))
        signal_with_registered_only = bool(opt("signal_with_registered_only", True))
        invite_retry_count = int(opt("invite_retry_count", 3))
        failback_mode = opt("failback_mode", "Duration")
        failback_duration = int(opt("failback_duration", 10)) * 60  # Convert minutes to seconds
        
        # Syslog
        syslog_enable = bool(opt("syslog_enable", False))
        syslog_server = opt("syslog_server", "")
        syslog_server_port = int(opt("syslog_server_port", 514))
        syslog_transport_type = opt("syslog_transport_type", "UDP")
        
        

        # VQ RTCP-XR
        vq_enable = bool(opt("vq_rtcp_xr_enable", False))
        vq_rtcpxr_interval_period = int(opt("vq_rtcpxr_interval_period", 15))
        vq_rtcpxr_interval_report_enable = bool(opt("vq_rtcpxr_interval_report_enable", False))
        vq_rtcpxr_states_show_on_gui_enable = bool(opt("vq_rtcpxr_states_show_on_gui_enable", False))
        vq_rtcpxr_states_show_on_web_enable = bool(opt("vq_rtcpxr_states_show_on_web_enable", False))

        # Media
        dtmf_type = opt("dtmf_type", "RFC2833")
        srtp_mode = opt("srtp_mode", "Disabled")
        dtmf_payload = int(opt("dtmf_payload", 101))
        early_media = bool(opt("early_media", True))
        
        
        # SIP
        hold_inactive = bool(opt("hold_inactive", False))
        enable_rport = bool(opt("enable_rport", True))
        session_timer_enable = bool(opt("session_timer_enable", True))
        nat_udp_update_time = int(opt("nat_udp_update_time", 60))
        nat_udp_update_type = opt("nat_udp_update_type", "Options")
        reg_fail_retry_interval = int(opt("reg_fail_retry_interval", 30))
        retry_counts = int(opt("retry_counts", 3))
        registration_random_seconds = int(opt("registration_random_seconds", 6))
        enable_user_equal_phone = bool(opt("enable_user_equal_phone", True))
        session_expires = int(opt("session_expires", 1800))
        session_refresher = opt("session_refresher", "UAC")
        server_expires = int(opt("server_expires", 600))





        # Features
        call_waiting = bool(opt("call_waiting", True))
        save_call_log = bool(opt("save_call_log", True))
        missed_calllog_enable = bool(opt("missed_calllog_enable", True))
        call_list_show_number = bool(opt("call_list_show_number", True))
        voice_country = opt("voice_country", "Australia")

        # Date & Time
        local_date_format = opt("local_date_format", "DD MMM YYYY")
        local_time_format = opt("local_time_format", "24 Hour")

        # Device-only options
        admin_password = opt("admin_password", "")

        # Hard Coded Defaults
        ntp_interval = 1440  # Yealink NTP interval default
        send_mac = True     # Always send MAC address
        send_line = True    # Always send line info
        sip_trust_only = True       # Trust only SIP servers in config
        auto_line_keys = True       # Auto provision all lines on keys
        direct_ip_call_enable = False   # Disable answering direct IP calls   
        management_server_enable   = False   # Is TR-069 management server enabled?
        power_saving_enable = False     # Is power saving enabled?
        lldp_packet_interval = 60       # Number of seconds between LLDP packets
        cdp_packet_interval = 60        # Number of seconds between CDP packets
        unregister_on_reboot = True     # Do we force unregistration when device reboots


        # To be determined
        #dialplan_enable = bool(opt("dialplan_enable", False))
        #dialplan_rules = opt("dialplan_rules", "")



        # Collect lines (line_1 + additional lines)
        lines: List[Any] = []
        if device.line_1:
            lines.append(device.line_1)
        extra_lines = list(getattr(device, "lines").all()) if hasattr(device, "lines") else []
        for ln in extra_lines:
            if device.line_1 and ln.id == device.line_1.id:
                continue
            lines.append(ln)
        lines = lines[: self.NumberOfLines]




        config_lines: List[str] = ["#!version:1.0.0.1"]

        # Hard-coded auto-provision cadence (daily) to keep phones synced with PhoneManager
        config_lines.extend(
            [
                "static.auto_provision.inactivity_time_expire = 2",
                "static.auto_provision.repeat.minutes = 1440",
                "static.auto_provision.weekly.enable = 1",
                "static.auto_provision.weekly.begin_time = 22:00",
                "static.auto_provision.weekly.end_time = 06:00",
                "static.auto_provision.weekly.dayofweek = 0123456",
            ]
        )

        # "Static" Configuration
        config_lines.extend(
            [
                f"static.network.port.min_rtpport = {rtp_port_min}",
                f"static.network.port.max_rtpport = {rtp_port_max}",
                f"static.network.port.http = {network_port_http}",
                f"static.network.port.https = {network_port_https}",
                f"static.network.lldp.enable = {bool_flag(lldp_active)}",
                f"static.network.cdp.enable = {bool_flag(cdp_active)}",
                f"static.network.lldp.interval = {lldp_packet_interval}",
                f"static.network.cdp.interval = {cdp_packet_interval}",
                f"static.network.qos.audiotos = {voice_qos_dscp}",
                f"static.network.qos.signaltos = {sip_qos_dscp}",
                f"static.wui.http_enable = {bool_flag(web_http_enable)}",
                f"static.wui.https_enable = {bool_flag(web_https_enable)}",
                f"static.network.port.http = {network_port_http}",
                f"static.network.port.https = {network_port_https}",
                f"static.managementserver.enable = {bool_flag(management_server_enable)}",

            ]
        )

        # Syslog Configuration
        if syslog_enable:
            config_lines.extend(
                [
                    f"static.syslog.enable = {bool_flag(syslog_enable)}",
                    f"static.syslog.server = {syslog_server}",
                    f"static.syslog.server_port = {syslog_server_port}",
                    f"static.syslog.transport_type = {transport_map.get(syslog_transport_type, 0)}",
                ]
            )

        # Time / NTP
        tz_config = get_timezone_config(site.timezone)
        config_lines.extend(
            [
                f"local_time.time_zone = {tz_config['time_zone']}",
                f"local_time.summer_time = {tz_config['summer_time']}",
                f"local_time.dst_time_type = {tz_config['dst_time_type']}",
                f"local_time.ntp_server1 = {site.primary_ntp_ip or ''}",
                f"local_time.ntp_server2 = {site.secondary_ntp_ip or ''}",
                f"local_time.interval = {ntp_interval}",
                f"local_time.date_format = {dateformat_map.get(local_date_format, 5)}",
                f"local_time.time_format = {timeformat_map.get(local_time_format, 1)}",
                f"local_time.offset_time = {tz_config['offset_time']}",
                f"local_time.manual_ntp_srv_prior = {tz_config['manual_ntp_srv_prior']}",
            ]
        )
        
        # Add DST transition times if applicable
        if tz_config.get('start_time') and tz_config.get('end_time'):
            config_lines.extend(
                [
                    f"local_time.start_time = {tz_config['start_time']}",
                    f"local_time.end_time = {tz_config['end_time']}",
                ]
            )

        # DHCP Hostname
        if dhcp_hostname:
            config_lines.append(f"network.dhcp_host_name = {dhcp_hostname}")

        # Global features
        config_lines.extend(
            [
                f"call_waiting.enable = {bool_flag(call_waiting)}",
                f"features.save_call_history.enable = {bool_flag(save_call_log)}",
                f"phone_setting.calllist_show_number.enable = {bool_flag(call_list_show_number)}",
                f"sip.trust_ctrl = {bool_flag(sip_trust_only)}",
                f"sip.reg_surge_prevention = {registration_random_seconds}",
                f"voice.tone.country = {voice_country}",
                f"features.power_saving.enable = {bool_flag(power_saving_enable)}",
                f"features.auto_line_keys.enable = {bool_flag(auto_line_keys)}",
                f"features.direct_ip_call.enable = {bool_flag(direct_ip_call_enable)}",
                f"voice.rtcp_xr.enable = {bool_flag(vq_enable)}",
            ]
        )

        if admin_password:
            config_lines.append(f"security.user_password = admin:{admin_password}")
            config_lines.append(f"security.user_password = user:{admin_password}")

        # Dial plan rules (site-level)
        dial_plan = getattr(site, "dial_plan", None)
        if dial_plan:
            rules = dial_plan.rules.all().order_by("sequence_order")
            for index, rule in enumerate(rules, start=1):
                if index > 100:
                    break
                prefix = convert_yealink_input_regex(rule.input_regex)
                replace = convert_yealink_output_regex(rule.output_regex)
                config_lines.extend(
                    [
                        f"dialplan.replace.prefix.{index} = {prefix}",
                        f"dialplan.replace.replace.{index} = {replace}",
                    ]
                )


        # Voice Quality RTCP-XR settings (only if enabled)
        if vq_enable:
            config_lines.extend(
                [
                    f"phone_setting.vq_rtcpxr.interval_report.enable = {bool_flag(vq_rtcpxr_interval_report_enable)}",
                    f"phone_setting.vq_rtcpxr.states_show_on_gui.enable = {bool_flag(vq_rtcpxr_states_show_on_gui_enable)}",
                    f"phone_setting.vq_rtcpxr.states_show_on_web.enable = {bool_flag(vq_rtcpxr_states_show_on_web_enable)}",
                    f"phone_setting.vq_rtcpxr_interval_period = {vq_rtcpxr_interval_period}",
                    f"phone_setting.vq_rtcpxr.session_report.enable = {bool_flag(vq_enable)}",
                ]
            )


        # Per-account rendering
        for idx, line in enumerate(lines, start=1):
            line_primary, line_secondary = get_line_sip_servers(idx)

            line_label = getattr(line, "phone_label", "") or line.name

            config_lines.extend(
                [
                    f"account.{idx}.enable = 1",
                    f"account.{idx}.unregister_on_reboot = {bool_flag(unregister_on_reboot)}",
                    f"account.{idx}.label = {line_label}",
                    f"account.{idx}.display_name = {line.name}",
                    f"account.{idx}.auth_name = {line.registration_account}",
                    f"account.{idx}.user_name = {line.directory_number}",
                    f"account.{idx}.password = {line.registration_password}",
                    f"account.{idx}.shared_line = {bool_flag(getattr(line, 'is_shared', False))}",
                    f"account.{idx}.sip_server.1.address = {line_primary.host}",
                    f"account.{idx}.sip_server.1.port = {line_primary.port}",
                    f"account.{idx}.sip_server.1.transport_type = {transport_map.get(line_primary.transport.upper(), 0)}",
                    f"account.{idx}.sip_server.1.expires = {server_expires}",
                    f"account.{idx}.sip_server.1.retry_counts = {retry_counts}",
                    f"account.{idx}.sip_server.2.address = {line_secondary.host if line_secondary else ''}",
                    f"account.{idx}.sip_server.2.port = {line_secondary.port if line_secondary else ''}",
                    f"account.{idx}.sip_server.2.transport_type = {transport_map.get(line_secondary.transport.upper(), 0) if line_secondary else ''}",
                    f"account.{idx}.sip_server.2.expires = {server_expires if line_secondary else ''}",
                    f"account.{idx}.sip_server.2.retry_counts = {retry_counts if line_secondary else ''}",
                    f"account.{idx}.nat.rport = {bool_flag(enable_rport)}",
                    f"account.{idx}.nat.udp_update_enable = {keepalive_map.get(nat_udp_update_type, 2)}",
                    f"account.{idx}.nat.udp_update_time = {nat_udp_update_time}",
                    f"account.{idx}.enable_user_equal_phone = {bool_flag(enable_user_equal_phone)}",
                    f"account.{idx}.missed_calllog = {bool_flag(missed_calllog_enable)}",
                    f"account.{idx}.dtmf.type = {dtmf_map.get(dtmf_type, 1)}",
                    f"account.{idx}.dtmf.dtmf_payload = {dtmf_payload}",
                    f"account.{idx}.session_timer.enable = {bool_flag(session_timer_enable)}",
                    f"account.{idx}.reg_fail_retry_interval = {reg_fail_retry_interval}",
                    f"account.{idx}.session_timer.expires = {session_expires}",
                    f"account.{idx}.session_timer.refresher = {refresher_map.get(session_refresher, 0)}",
                    f"account.{idx}.srtp_encryption = {srtp_map.get(srtp_mode, 0)}",
                    f"account.{idx}.100rel_enable = {bool_flag(early_media)}",
                    f"account.{idx}.register_mac = {bool_flag(send_mac)}",
                    f"account.{idx}.register_line = {bool_flag(send_line)}",
                    f"account.{idx}.hold_use_inactive = {bool_flag(hold_inactive)}",
                    f"account.{idx}.fallback.redundancy_type = {redudancy_type_map.get(failover_type, 1)}",
                    f"account.{idx}.fallback.timeout = {failover_timeout}",
                    f"account.{idx}.sip_server.1.register_on_enable = {bool_flag(register_on_active)}",
                    f"account.{idx}.sip_server.1.only_signal_with_registered = {bool_flag(signal_with_registered_only)}",
                    f"account.{idx}.sip_server.1.invite_retry_counts = {invite_retry_count}",
                    f"account.{idx}.sip_server.1.failback_mode = {failback_mode_map.get(failback_mode, 3)}",
                    f"account.{idx}.sip_server.1.failback_timeout = {failback_duration}", 
                    f"account.{idx}.sip_server.2.register_on_enable = {bool_flag(register_on_active) if line_secondary else ''}",
                    f"account.{idx}.sip_server.2.only_signal_with_registered = {bool_flag(signal_with_registered_only) if line_secondary else ''}",
                    f"account.{idx}.sip_server.2.invite_retry_counts = {invite_retry_count if line_secondary else ''}",
                    f"account.{idx}.sip_server.2.failback_mode = {failback_mode_map.get(failback_mode, 3) if line_secondary else ''}",
                    f"account.{idx}.sip_server.2.failback_timeout = {failback_duration if line_secondary else ''}",
                ]
            )

            enabled_codecs: Dict[str, Dict[str, int]] = {}
            for priority, codec_norm in enumerate(preferred_codecs):
                mapped_codec = codec_map.get(codec_norm)
                if not mapped_codec:
                    continue
                codectype, rtpmap = mapped_codec
                if codectype in enabled_codecs:
                    continue
                enabled_codecs[codectype] = {"priority": priority, "rtpmap": rtpmap}

            # Disable any codec not selected
            for codectype in all_codec_types:
                if codectype not in enabled_codecs:
                    config_lines.append(f"account.{idx}.codec.{codectype}.enable = 0")

            # Enable and set priority/rtpmap for selected codecs
            for codectype, settings in enabled_codecs.items():
                config_lines.extend(
                    [
                        f"account.{idx}.codec.{codectype}.enable = 1",
                        f"account.{idx}.codec.{codectype}.priority = {settings['priority']}",
                    ]
                )
                if settings["rtpmap"] is not None:
                    config_lines.append(f"account.{idx}.codec.{codectype}.rtpmap = {settings['rtpmap']}")

            if vq_enable:
                config_lines.extend(
                    [
                        f"account.{idx}.vq_rtcpxr.collector_name = {line_primary.host}",
                        f"account.{idx}.vq_rtcpxr.collector_server_host = {line_primary.host}",
                        f"account.{idx}.vq_rtcpxr.collector_server_port = {line_primary.port}",

                    ]
                )

           

        # Disable all remaining account slots
        for idx in range(len(lines) + 1, self.NumberOfLines + 1):
            config_lines.append(f"account.{idx}.enable = 0")

        return "\n".join(config_lines)
