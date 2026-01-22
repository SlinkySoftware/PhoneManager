# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Yealink SIP-T33G device type renderer.

"""
from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime

import pytz

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
		},        {
            "friendlyName": "RTP Parameters",
            "uiOrder": 2,
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
            "uiOrder": 3,
            "options": [
                {
                    "optionId": "network_port_http",
                    "friendlyName": "HTTP Server Port",
                    "default": 10080,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 1,
                },
                {
                    "optionId": "network_port_https",
                    "friendlyName": "HTTPS Server Port",
                    "default": 10443,
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
            "uiOrder": 4,
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
	]
}


class YealinkSIPT33G(DeviceType):
    TypeID = "YealinkSIPT33G"
    Manufacturer = "Yealink"
    Model = "SIP-T33G"
    NumberOfLines = 4
    CommonOptions = COMMON_OPTIONS
    DeviceSpecificOptions = DEVICE_OPTIONS
    ContentType = "text/plain"

    def render(self, device: Any) -> str:
        # Pull decrypted device-specific configuration (includes admin password)
        cfg = device.get_decrypted_device_config() if hasattr(device, "get_decrypted_device_config") else (
            device.device_specific_configuration or {}
        )

        def opt(key: str, default: Any) -> Any:
            return cfg.get(key, default)

        def bool_flag(value: Any) -> str:
            return "1" if bool(value) else "0"

        def get_timezone_offset_and_dst(tz_name: str) -> tuple[float, int]:
            """
            Calculate UTC offset and DST flag for a timezone.
            Automatically determines if timezone observes DST by comparing summer/winter offsets.
            
            Returns: (offset_hours: float, dst_flag: int)
            - offset_hours: UTC offset without DST (-12 to +14)
            - dst_flag: 0=no DST support, 1=DST currently active, 2=DST supported but not active
            """
            try:
                tz = pytz.timezone(tz_name)
                
                # Get offset for winter date (Jan 15) - standard time
                winter_date = datetime(2026, 1, 15, tzinfo=tz)
                winter_offset_seconds = winter_date.utcoffset().total_seconds()
                winter_offset_hours = winter_offset_seconds / 3600
                
                # Get offset for summer date (Jul 15) - potential DST time
                summer_date = datetime(2026, 7, 15, tzinfo=tz)
                summer_offset_seconds = summer_date.utcoffset().total_seconds()
                summer_offset_hours = summer_offset_seconds / 3600
                
                # Check if timezone observes DST (offsets differ between summer and winter)
                observes_dst = winter_offset_hours != summer_offset_hours
                
                if not observes_dst:
                    # Timezone doesn't observe DST
                    return winter_offset_hours, 0
                else:
                    # Timezone observes DST - check if we're currently in DST period
                    now = datetime.now(tz=tz)
                    current_offset_hours = now.utcoffset().total_seconds() / 3600
                    
                    if current_offset_hours == summer_offset_hours:
                        # Currently in DST (summer time)
                        return winter_offset_hours, 1
                    else:
                        # Currently in standard time (winter time)
                        return winter_offset_hours, 2
            except Exception:
                # Fallback to UTC if timezone parsing fails
                return 0.0, 0

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
        session_refresher = opt("session_refresher", "uas")
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
        management_server_enable   = True   # Is management server enabled?
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

        # Time / NTP
        tz_offset, dst_flag = get_timezone_offset_and_dst(site.timezone)
        config_lines.extend(
            [
                f"local_time.time_zone = {tz_offset}",
                f"local_time.summer_time = {dst_flag}",
                f"local_time.time_zone_name = {site.timezone}",
                f"local_time.ntp_server1 = {site.primary_ntp_ip or ''}",
                f"local_time.ntp_server2 = {site.secondary_ntp_ip or ''}",
                f"local_time.interval = {ntp_interval}",
                f"local_time.date_format = {dateformat_map.get(local_date_format, 5)}",
                f"local_time.time_format = {timeformat_map.get(local_time_format, 1)}",
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
            config_lines.append(f"security.user_password = {admin_password}")


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

            config_lines.extend(
                [
                    f"account.{idx}.enable = 1",
                    f"account.{idx}.unregister_on_reboot = {bool_flag(unregister_on_reboot)}",
                    f"account.{idx}.label = {line.name}",
                    f"account.{idx}.display_name = {line.name}",
                    f"account.{idx}.auth_name = {line.registration_account}",
                    f"account.{idx}.user_name = {line.registration_account}",
                    f"account.{idx}.password = {line.registration_password}",
                    f"account.{idx}.shared_line = {bool_flag(getattr(line, 'is_shared', False))}",
                    f"account.{idx}.sip_server.1.address = {primary.host}",
                    f"account.{idx}.sip_server.1.port = {primary.port}",
                    f"account.{idx}.sip_server.1.transport_type = {transport_map.get(primary.transport.upper(), 0)}",
                    f"account.{idx}.sip_server.1.expires = {server_expires}",
                    f"account.{idx}.sip_server.1.retry_counts = {retry_counts}",
                    f"account.{idx}.sip_server.2.address = {secondary.host if secondary else ''}",
                    f"account.{idx}.sip_server.2.port = {secondary.port if secondary else ''}",
                    f"account.{idx}.sip_server.2.transport_type = {transport_map.get(secondary.transport.upper(), 0) if secondary else ''}",
                    f"account.{idx}.sip_server.2.expires = {server_expires if secondary else ''}",
                    f"account.{idx}.sip_server.2.retry_counts = {retry_counts if secondary else ''}",
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
                        f"account.{idx}.vq_rtcpxr.collector_name = {primary.host}",
                        f"account.{idx}.vq_rtcpxr.collector_server_host = {primary.host}",
                        f"account.{idx}.vq_rtcpxr.collector_server_port = {primary.port}",

                    ]
                )

           

        # Disable all remaining account slots
        for idx in range(len(lines) + 1, self.NumberOfLines + 1):
            config_lines.append(f"account.{idx}.enable = 0")

        return "\n".join(config_lines)
