# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Yealink SIP-T33G device type renderer.

"""
from __future__ import annotations
from typing import Any, Dict, List

from .base import DeviceType


COMMON_OPTIONS: Dict[str, Any] = {
    "sections": [
        {
            "friendlyName": "Network & QoS",
            "uiOrder": 1,
            "options": [
                {
                    "optionId": "rtp_port_min",
                    "friendlyName": "Local RTP Port Min",
                    "default": 16384,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 1,
                },
                {
                    "optionId": "rtp_port_max",
                    "friendlyName": "Local RTP Port Max",
                    "default": 32767,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
                {
                    "optionId": "registration_random_seconds",
                    "friendlyName": "Registration Random (seconds)",
                    "default": 6,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 3,
                },
                {
                    "optionId": "lldp_active",
                    "friendlyName": "LLDP Active",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 4,
                },
                {
                    "optionId": "cdp_active",
                    "friendlyName": "CDP Active",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 5,
                },
                {
                    "optionId": "voice_qos_dscp",
                    "friendlyName": "Voice QoS DSCP",
                    "default": 46,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 6,
                },
                {
                    "optionId": "sip_qos_dscp",
                    "friendlyName": "SIP QoS DSCP",
                    "default": 26,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 7,
                },
            ],
        },
        {
            "friendlyName": "SIP & Media",
            "uiOrder": 2,
            "options": [
                {
                    "optionId": "server_expires",
                    "friendlyName": "Server Expires (s)",
                    "default": 600,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 1,
                },
                {
                    "optionId": "retry_counts",
                    "friendlyName": "Retry Counts",
                    "default": 3,
                    "mandatory": False,
                    "type": "number",
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
                    "optionId": "dtmf_type",
                    "friendlyName": "DTMF Type",
                    "default": "RFC2833",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["RFC2833", "SIP_INFO", "Inband"],
                    "uiOrder": 4,
                },
                {
                    "optionId": "session_timer_enable",
                    "friendlyName": "Session Timer",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 5,
                },
                {
                    "optionId": "session_expires",
                    "friendlyName": "Session Expires (s)",
                    "default": 1800,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 6,
                },
                {
                    "optionId": "session_refresher",
                    "friendlyName": "Session Refresher",
                    "default": "uas",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["uas", "uac"],
                    "uiOrder": 7,
                },
                {
                    "optionId": "srtp_mode",
                    "friendlyName": "RTP Encryption",
                    "default": "disabled",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["disabled", "optional", "srtp"],
                    "uiOrder": 8,
                },
                {
                    "optionId": "early_media",
                    "friendlyName": "Early Media",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 9,
                },
                {
                    "optionId": "send_mac",
                    "friendlyName": "SIP Send MAC",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 10,
                },
                {
                    "optionId": "send_line",
                    "friendlyName": "SIP Send Line",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 11,
                },
                {
                    "optionId": "hold_inactive",
                    "friendlyName": "RFC 2543 Hold (inactive)",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 12,
                },
            ],
        },
        {
            "friendlyName": "VQ RTCP-XR",
            "uiOrder": 3,
            "options": [
                {
                    "optionId": "vq_rtcp_xr_enable",
                    "friendlyName": "Enable VQ RTCP-XR",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                },
                {
                    "optionId": "vq_collector_name",
                    "friendlyName": "Collector Name",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 2,
                },
                {
                    "optionId": "vq_collector_host",
                    "friendlyName": "Collector Address",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 3,
                },
                {
                    "optionId": "vq_collector_port",
                    "friendlyName": "Collector Port",
                    "default": 5070,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 4,
                },
            ],
        },
        {
            "friendlyName": "Features",
            "uiOrder": 4,
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
                    "optionId": "save_call_log",
                    "friendlyName": "Save Call Log",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 2,
                },
                {
                    "optionId": "sip_trust_server_only",
                    "friendlyName": "Accept SIP Trust Server Only",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 3,
                },
                {
                    "optionId": "call_list_show_number",
                    "friendlyName": "Call List Show Number",
                    "default": True,
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
            ],
        },
        {
            "friendlyName": "Time & NTP",
            "uiOrder": 5,
            "options": [
                {
                    "optionId": "ntp_update_interval",
                    "friendlyName": "NTP Update Interval (minutes)",
                    "default": 1440,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 1,
                }
            ],
        },
        {
            "friendlyName": "Dial Plan",
            "uiOrder": 6,
            "options": [
                {
                    "optionId": "dialplan_enable",
                    "friendlyName": "Enable Dial Plan",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                },
                {
                    "optionId": "dialplan_rules",
                    "friendlyName": "Digitmap / Dial Plan",
                    "default": "",
                    "mandatory": False,
                    "type": "textarea",
                    "uiOrder": 2,
                },
            ],
        },
    ]
}


DEVICE_OPTIONS: Dict[str, Any] = {
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
                }
            ],
        }
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

        # Network & QoS
        rtp_port_min = int(opt("rtp_port_min", 16384))
        rtp_port_max = int(opt("rtp_port_max", 32767))
        reg_random = int(opt("registration_random_seconds", 6))
        lldp_active = bool(opt("lldp_active", True))
        cdp_active = bool(opt("cdp_active", False))
        voice_qos_dscp = int(opt("voice_qos_dscp", 46))
        sip_qos_dscp = int(opt("sip_qos_dscp", 26))

        # SIP & media
        server_expires = int(opt("server_expires", 600))
        retry_counts = int(opt("retry_counts", 3))
        enable_rport = bool(opt("enable_rport", True))
        dtmf_type = opt("dtmf_type", "RFC2833")
        session_timer_enable = bool(opt("session_timer_enable", True))
        session_expires = int(opt("session_expires", 1800))
        session_refresher = opt("session_refresher", "uas")
        srtp_mode = opt("srtp_mode", "disabled")
        early_media = bool(opt("early_media", True))
        send_mac = bool(opt("send_mac", True))
        send_line = bool(opt("send_line", True))
        hold_inactive = bool(opt("hold_inactive", False))

        # VQ RTCP-XR
        vq_enable = bool(opt("vq_rtcp_xr_enable", False))
        vq_name = opt("vq_collector_name", "")
        vq_host = opt("vq_collector_host", "")
        vq_port = int(opt("vq_collector_port", 5070))

        # Features
        call_waiting = bool(opt("call_waiting", True))
        save_call_log = bool(opt("save_call_log", True))
        sip_trust_only = bool(opt("sip_trust_server_only", True))
        call_list_show_number = bool(opt("call_list_show_number", True))
        dhcp_hostname = opt("dhcp_hostname", "")

        # Time & dialplan
        ntp_interval = int(opt("ntp_update_interval", 1440))
        dialplan_enable = bool(opt("dialplan_enable", False))
        dialplan_rules = opt("dialplan_rules", "")

        # Device-only options
        admin_password = opt("admin_password", "")

        site = device.site
        primary = site.primary_sip_server
        secondary = getattr(site, "secondary_sip_server", None)

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

        transport_map = {"UDP": 0, "TCP": 1, "TLS": 2}
        dtmf_map = {"RFC2833": 2, "SIP_INFO": 3, "Inband": 1}
        srtp_map = {"disabled": 0, "optional": 1, "srtp": 2}
        refresher_map = {"uas": 0, "uac": 1}

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

        # Network and QoS
        config_lines.extend(
            [
                f"static.network.port.min_rtpport = {rtp_port_min}",
                f"static.network.port.max_rtpport = {rtp_port_max}",
                f"sip.reg_surge_prevention = {reg_random}",
                f"network.lldp.enable = {bool_flag(lldp_active)}",
                f"network.cdp.enable = {bool_flag(cdp_active)}",
                f"static.network.qos.audiotos = {voice_qos_dscp}",
                f"static.network.qos.signaltos = {sip_qos_dscp}",
            ]
        )

        # Time, NTP, DHCP
        config_lines.extend(
            [
                f"local_time.time_zone = {site.timezone}",
                f"local_time.ntp_server1 = {site.primary_ntp_ip or ''}",
                f"local_time.ntp_server2 = {site.secondary_ntp_ip or ''}",
                f"local_time.ntp_refresh_interval = {ntp_interval}",
            ]
        )
        if dhcp_hostname:
            config_lines.append(f"network.dhcp_host_name = {dhcp_hostname}")

        # Global features
        config_lines.extend(
            [
                f"call_waiting.enable = {bool_flag(call_waiting)}",
                f"features.save_call_history.enable = {bool_flag(save_call_log)}",
                f"sip.trust_ctrl = {bool_flag(sip_trust_only)}",
                f"phone_setting.calllist_show_number.enable = {bool_flag(call_list_show_number)}",
            ]
        )

        if admin_password:
            config_lines.append(f"security.user_password = {admin_password}")

        # Per-account rendering
        for idx, line in enumerate(lines, start=1):
            transport_code = transport_map.get(primary.transport.upper(), 0)
            secondary_transport = transport_map.get(secondary.transport.upper(), 0) if secondary else 0

            config_lines.extend(
                [
                    f"account.{idx}.enable = 1",
                    f"account.{idx}.label = {line.name}",
                    f"account.{idx}.display_name = {line.name}",
                    f"account.{idx}.auth_name = {line.registration_account}",
                    f"account.{idx}.user_name = {line.registration_account}",
                    f"account.{idx}.password = {line.registration_password}",
                    f"account.{idx}.sip_server.1.address = {primary.host}",
                    f"account.{idx}.sip_server.1.port = {primary.port}",
                    f"account.{idx}.sip_server.1.transport_type = {transport_code}",
                    f"account.{idx}.sip_server.1.expires = {server_expires}",
                    f"account.{idx}.sip_server.1.retry_counts = {retry_counts}",
                    f"account.{idx}.sip_server.2.address = {secondary.host if secondary else ''}",
                    f"account.{idx}.sip_server.2.port = {secondary.port if secondary else ''}",
                    f"account.{idx}.sip_server.2.transport_type = {secondary_transport if secondary else ''}",
                    f"account.{idx}.sip_server.2.expires = {server_expires if secondary else ''}",
                    f"account.{idx}.sip_server.2.retry_counts = {retry_counts if secondary else ''}",
                    f"account.{idx}.nat.rport = {bool_flag(enable_rport)}",
                    f"account.{idx}.dtmf.type = {dtmf_map.get(dtmf_type, 2)}",
                    f"account.{idx}.session_timer.enable = {bool_flag(session_timer_enable)}",
                    f"account.{idx}.session_timer.expires = {session_expires}",
                    f"account.{idx}.session_timer.refresher = {refresher_map.get(session_refresher, 0)}",
                    f"account.{idx}.srtp_encryption = {srtp_map.get(srtp_mode, 0)}",
                    f"account.{idx}.100rel_enable = {bool_flag(early_media)}",
                    f"account.{idx}.register_mac = {bool_flag(send_mac)}",
                    f"account.{idx}.register_line = {bool_flag(send_line)}",
                    f"account.{idx}.hold_use_inactive = {bool_flag(hold_inactive)}",
                ]
            )

            if vq_enable:
                config_lines.extend(
                    [
                        f"account.{idx}.vq_rtcpxr.collector_name = {vq_name}",
                        f"account.{idx}.vq_rtcpxr.collector_server_host = {vq_host}",
                        f"account.{idx}.vq_rtcpxr.collector_server_port = {vq_port}",
                    ]
                )

            if dialplan_enable and dialplan_rules:
                config_lines.extend(
                    [
                        f"account.{idx}.dialplan.digitmap.enable = 1",
                        f"account.{idx}.dialplan.digitmap.string = {dialplan_rules}",
                    ]
                )
            elif dialplan_enable:
                config_lines.append(f"account.{idx}.dialplan.digitmap.enable = 1")
            else:
                config_lines.append(f"account.{idx}.dialplan.digitmap.enable = 0")

        return "\n".join(config_lines)
