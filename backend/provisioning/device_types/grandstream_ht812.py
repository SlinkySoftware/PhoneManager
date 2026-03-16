# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Grandstream HT812 ATA device type renderer.

This implementation exposes a small, focused set of options and renders
an XML provisioning payload compatible with Grandstream HT81x series.

Notes:
- Many parameters are left to device defaults. The renderer sets the key
  identity, transport, regional tones, and per-port user fields. Additional
  P-values can be added incrementally as needed.
"""
from __future__ import annotations
from textwrap import dedent
from typing import Any, Dict, List
import re

from .base import DeviceType


DTMF_METHOD_IN_AUDIO = "In-audio"
DTMF_METHOD_RFC2833 = "RFC2833"
DTMF_METHOD_SIP_INFO = "SIP INFO"
DTMF_METHOD_CHOICES = [DTMF_METHOD_IN_AUDIO, DTMF_METHOD_RFC2833, DTMF_METHOD_SIP_INFO]


COMMON_OPTIONS: Dict[str, Any] = {
    "sections": [
        {
            "friendlyName": "SIP Parameters",
            "uiOrder": 1,
            "options": [
                {
                    "optionId": "sip_transport",
                    "friendlyName": "SIP Transport",
                    "default": "UDP",
                    "mandatory": True,
                    "type": "select",
                    "choices": ["UDP", "TCP", "TLS"],
                    "uiOrder": 1,
                },
                {
                    "optionId": "session_expiration",
                    "friendlyName": "Session Expiration (s)",
                    "default": 1800,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
                {
                    "optionId": "sip_keepalive_interval",
                    "friendlyName": "SIP Keep-Alive Interval (s)",
                    "default": 20,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 3,
                },
                {
                    "optionId": "enable_sip_keepalive",
                    "friendlyName": "Enable SIP Keep-Alive",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 4,
                },
                {
                    "optionId": "registration_retry_interval",
                    "friendlyName": "Registration Failure Retry Interval (s)",
                    "default": 20,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 5,
                },
                {
                    "optionId": "prefer_primary_server",
                    "friendlyName": "Prefer Primary SIP Server",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 6,
                },
                {
                    "optionId": "sip_dscp",
                    "friendlyName": "SIP DSCP",
                    "default": 26,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 7,
                },
            ],
        },
        {
            "friendlyName": "Session Timer",
            "uiOrder": 2,
            "options": [
                {
                    "optionId": "enable_session_timer",
                    "friendlyName": "Enable Session Timer",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                },
                {
                    "optionId": "min_se",
                    "friendlyName": "Min-SE (s)",
                    "default": 90,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
                {
                    "optionId": "enable_100rel",
                    "friendlyName": "Enable 100rel (PRACK)",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 3,
                },
            ],
        },
        {
            "friendlyName": "RTP & Codecs",
            "uiOrder": 3,
            "options": [
                {
                    "optionId": "local_rtp_port",
                    "friendlyName": "Local RTP Port",
                    "default": 6004,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 1,
                },
                {
                    "optionId": "rtp_dscp",
                    "friendlyName": "RTP DSCP",
                    "default": 46,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
                {
                    "optionId": "preferred_codecs",
                    "friendlyName": "Preferred Codec Order",
                    "default": ["PCMU", "PCMA", "G729", "G722", "OPUS"],
                    "mandatory": True,
                    "type": "orderedmultiselect",
                    "choices": ["PCMU", "PCMA", "G729", "G722", "OPUS", "G726-32", "G723", "iLBC"],
                    "uiOrder": 3,
                },
            ],
        },
        {
            "friendlyName": "DTMF",
            "uiOrder": 4,
            "options": [
                {
                    "optionId": "dtmf_payload_id",
                    "friendlyName": "RFC2833 DTMF Payload ID",
                    "default": 101,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 1,
                },
                {
                    "optionId": "dtmf_method_1",
                    "friendlyName": "DTMF Method 1",
                    "default": DTMF_METHOD_RFC2833,
                    "mandatory": True,
                    "type": "select",
                    "choices": DTMF_METHOD_CHOICES,
                    "uiOrder": 2,
                },
                {
                    "optionId": "dtmf_method_2",
                    "friendlyName": "DTMF Method 2",
                    "default": DTMF_METHOD_SIP_INFO,
                    "mandatory": True,
                    "type": "select",
                    "choices": DTMF_METHOD_CHOICES,
                    "uiOrder": 3,
                },
                {
                    "optionId": "dtmf_method_3",
                    "friendlyName": "DTMF Method 3",
                    "default": DTMF_METHOD_IN_AUDIO,
                    "mandatory": True,
                    "type": "select",
                    "choices": DTMF_METHOD_CHOICES,
                    "uiOrder": 4,
                },
            ],
        },
        {
            "friendlyName": "Syslog",
            "uiOrder": 5,
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
                    "optionId": "syslog_level",
                    "friendlyName": "Syslog Level",
                    "default": "None",
                    "mandatory": False,
                    "type": "select",
                    "choices": ["None", "Debug", "Info", "Warning", "Error", "Extra Debug"],
                    "uiOrder": 2,
                },
            ],
        },
        {
            "friendlyName": "Regional",
            "uiOrder": 6,
            "options": [
                {
                    "optionId": "region_tones",
                    "friendlyName": "Use AU Tones",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                }
            ],
        },
        {
            "friendlyName": "SNMP",
            "uiOrder": 7,
            "options": [
                {
                    "optionId": "enable_snmp",
                    "friendlyName": "Enable SNMP",
                    "default": False,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                },
                {
                    "optionId": "snmp_trap_ip",
                    "friendlyName": "SNMP Trap Receiver IP",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 2,
                },
                {
                    "optionId": "snmp_trap_port",
                    "friendlyName": "SNMP Trap Receiver Port",
                    "default": 162,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 3,
                },
                {
                    "optionId": "snmp_poll_community",
                    "friendlyName": "SNMP Poll Community",
                    "default": "public",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 4,
                },
                {
                    "optionId": "snmp_trap_community",
                    "friendlyName": "SNMP Trap Community",
                    "default": "public",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 5,
                },
            ],
        },
    ]
}


DEVICE_OPTIONS: Dict[str, Any] = {
    "sections": [
        {
            "friendlyName": "Network",
            "uiOrder": 1,
            "options": [
                {
                    "optionId": "dhcp_hostname",
                    "friendlyName": "DHCP Hostname",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                },
                {
                    "optionId": "http_port",
                    "friendlyName": "HTTP Port",
                    "default": 80,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 2,
                },
                {
                    "optionId": "https_port",
                    "friendlyName": "HTTPS Port",
                    "default": 443,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 3,
                },
            ],
        },
        {
            "friendlyName": "FXS Ports",
            "uiOrder": 2,
            "options": [
                {
                    "optionId": "offhook_autodial_1",
                    "friendlyName": "Port 1 Offhook Autodial Number",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 1,
                },
                {
                    "optionId": "offhook_autodial_2",
                    "friendlyName": "Port 2 Offhook Autodial Number",
                    "default": "",
                    "mandatory": False,
                    "type": "text",
                    "uiOrder": 2,
                },
            ],
        },
        {
            "friendlyName": "Administrative",
            "uiOrder": 3,
            "options": [
                {
                    "optionId": "admin_password",
                    "friendlyName": "Administrative Password",
                    "default": "",
                    "mandatory": False,
                    "type": "password",
                    "uiOrder": 1,
                }
            ],
        }
    ]
}


class GrandstreamHT812(DeviceType):
    TypeID = "GrandstreamHT812"
    Manufacturer = "Grandstream"
    Model = "HT812"
    NumberOfLines = 2
    SupportsSIPServersPerLine = False
    CommonOptions = COMMON_OPTIONS
    DeviceSpecificOptions = DEVICE_OPTIONS
    ContentType = "text/xml"
    UserAgentPatterns = (
        r"Grandstream HT812",
        r"HT812",
    )

    def _mac_nocolon(self, mac: str) -> str:
        return mac.replace(":", "").replace("-", "").upper()

    def _codec_pvalues(self, codec_order: List[str]) -> List[str]:
        """Map human codec names to Grandstream pvalues (per options JSON)."""
        mapping = {
            "PCMU": "0",
            "PCMA": "8",
            "G723": "4",
            "G729": "18",
            "G726-32": "2",
            "iLBC": "97",
            "OPUS": "123",
            "G722": "9",
        }
        return [mapping[c] for c in codec_order if c in mapping]

    def _convert_to_grandstream_dialplan(self, input_regex: str, output_regex: str) -> str:
        """Convert standard regex dial plan rule to Grandstream syntax.
        
        Args:
            input_regex: Standard format pattern (e.g., "0([23478]XXXXXXXX)")
            output_regex: Standard format replacement (e.g., "+61$1")
        
        Returns:
            Grandstream dial plan entry (e.g., "<0=+61>[23478]xxxxxxxxT")
        
        Translation rules:
            - X → x (lowercase)
            - * → + (then combine with preceding x to make x+)
            - Remove ^ and $ anchors
            - [2468] → [2468] (preserved)
            - (pattern) with $1 → prepend/replace syntax
            - Fixed prefix → use <prefix=replacement> or <=prepend>
            - T suffix for variable-length patterns
        """
        if not input_regex or not output_regex:
            return ""
        
        # Remove anchors
        inp = input_regex.replace("^", "").replace("$", "")
        out = output_regex
        
        # Check for capture group pattern: prefix(pattern) → replacement$1
        capture_match = re.match(r'^([^(]*)\(([^)]+)\)$', inp)
        
        if capture_match:
            prefix = capture_match.group(1)
            captured = capture_match.group(2)
            
            # Check if output uses $1
            if "$1" in out:
                replacement_prefix = out.replace("$1", "")
                
                # Convert captured pattern carefully:
                # First handle * → + conversion, then lowercase X
                # This ensures XXX* becomes xxx+ not xxxx+
                converted_captured = captured.replace("*", "+").replace("X", "x")
                
                if prefix:
                    # Pattern like: 0([23]xxx) → +61$1 becomes <0=+61>[23]xxx
                    result = f"<{prefix}={replacement_prefix}>{converted_captured}"
                else:
                    # Pattern like: ([467]xxx) → +612$1 becomes <=+612>[467]xxx
                    result = f"<={replacement_prefix}>{converted_captured}"
                
                # Add T suffix ONLY for variable-length patterns (contains x+)
                # T = inter-digit timeout for patterns that can match varying lengths
                if "x+" in converted_captured:
                    result += "T"
                
                return result
        
        # Simple prepend case: no capture groups, just prepend prefix
        # Example: 000 → +61000 becomes <=+61>000
        converted_inp = inp.replace("*", "+").replace("X", "x")
        
        # Check if output contains the input pattern
        if converted_inp in out.replace("x", "X"):
            # Pure prepend case
            prefix_to_add = out.replace(inp, "").replace(converted_inp.upper(), "")
            result = f"<={prefix_to_add}>{converted_inp}"
        else:
            # Direct replacement case
            result = f"<={out}>{converted_inp}"
        
        # Add T suffix for variable-length patterns
        if "x+" in result and not result.endswith("T"):
            result += "T"
        
        return result

    def render(self, device: Any) -> str:
        line1 = device.line_1
        additional_lines = list(getattr(device, "lines").all()) if hasattr(device, "lines") else []
        line2 = additional_lines[0] if additional_lines else None

        site = device.site
        primary = site.primary_sip_server
        secondary = getattr(site, "secondary_sip_server", None)

        # Pull options with sensible defaults
        cfg = device.device_specific_configuration or {}
        transport = (cfg.get("sip_transport") or primary.transport or "UDP").upper()
        session_exp = int(cfg.get("session_expiration", 1800))
        sip_keepalive_interval = int(cfg.get("sip_keepalive_interval", 20))
        enable_sip_keepalive = bool(cfg.get("enable_sip_keepalive", True))
        registration_retry_interval = int(cfg.get("registration_retry_interval", 20))
        prefer_primary_server = bool(cfg.get("prefer_primary_server", True))

        enable_timer = bool(cfg.get("enable_session_timer", True))
        min_se = int(cfg.get("min_se", 90))
        enable_100rel = bool(cfg.get("enable_100rel", True))

        local_rtp_port = int(cfg.get("local_rtp_port", 6004))
        codec_order = cfg.get("preferred_codecs") or ["PCMU", "PCMA", "G729", "G722", "OPUS"]
        codec_pvalues = self._codec_pvalues(codec_order)

        sip_dscp = int(cfg.get("sip_dscp", 26))
        rtp_dscp = int(cfg.get("rtp_dscp", 46))

        dtmf_payload_id = int(cfg.get("dtmf_payload_id", 101))
        dtmf_method_1 = cfg.get("dtmf_method_1", DTMF_METHOD_RFC2833)
        dtmf_method_2 = cfg.get("dtmf_method_2", DTMF_METHOD_SIP_INFO)
        dtmf_method_3 = cfg.get("dtmf_method_3", DTMF_METHOD_IN_AUDIO)

        syslog_server = cfg.get("syslog_server") or ""
        syslog_level = cfg.get("syslog_level", "None")

        region_tones = bool(cfg.get("region_tones", True))

        snmp_enable = bool(cfg.get("enable_snmp", False))
        snmp_trap_ip = cfg.get("snmp_trap_ip") or ""
        snmp_trap_port = int(cfg.get("snmp_trap_port", 162))
        snmp_poll_comm = cfg.get("snmp_poll_community") or ""
        snmp_trap_comm = cfg.get("snmp_trap_community") or ""

        dhcp_hostname = cfg.get("dhcp_hostname") or ""
        http_port = int(cfg.get("http_port", 80))
        https_port = int(cfg.get("https_port", 443))

        offhook1 = cfg.get("offhook_autodial_1", "")
        offhook2 = cfg.get("offhook_autodial_2", "")
        admin_password = cfg.get("admin_password") or ""

        mac_clean = self._mac_nocolon(device.mac_address)
        if not dhcp_hostname:
            dhcp_hostname = f"grandstream_{mac_clean[-6:]}"

        provisioning_base_url = self.get_provisioning_base_url()

        # Build XML. Only include parameters we intentionally manage.
        # Tones (AU) copied from reference config (docs example)
        tones_xml = ""
        if region_tones:
            tones_xml = dedent(
                """
                <P4000>f1=400@-15,f2=425@-15,c=0/0;</P4000>
                <P4001>f1=400@-15,f2=450@-15,c=400/200-400/2000;</P4001>
                <P4002>f1=425@-12,f2=425@-30,c=375/375;</P4002>
                <P4003>f1=425@-12,f2=425@-30,c=2500/500;</P4003>
                <P4004>f1=425@-15,c=200/200-200/4400;</P4004>
                <P4005>f1=440@-13,c=300/10000;</P4005>
                """
            ).strip()

        transport_values = {
            "UDP": "0",
            "TCP": "1",
            "TLS": "2",
        }
        transport_xml_value = transport_values.get(transport, "0")

        enable_100rel_value = "1" if enable_100rel else "0"
        enable_timer_value = "1" if enable_timer else "0"

        timer_block = dedent(
            f"""
            <P2395>{enable_timer_value}</P2395>
            <P32>{session_exp}</P32>
            <P261>{min_se}</P261>
            <P272>{enable_100rel_value}</P272>
            """
        ).strip()

        codec_tag_numbers = [57, 58, 59, 60, 61, 62, 46, 98]
        codec_tags: List[str] = []
        for idx, pv in enumerate(codec_pvalues[:8]):
            tag_num = codec_tag_numbers[idx]
            codec_tags.append(f"<P{tag_num}>{pv}</P{tag_num}>")

        dtmf_method_values = {
            DTMF_METHOD_IN_AUDIO: "100",
            DTMF_METHOD_RFC2833: "101",
            DTMF_METHOD_SIP_INFO: "102",
        }
        dtmf_1_value = dtmf_method_values.get(dtmf_method_1, "101")
        dtmf_2_value = dtmf_method_values.get(dtmf_method_2, "102")
        dtmf_3_value = dtmf_method_values.get(dtmf_method_3, "100")

        syslog_level_values = {
            "None": "0",
            "Debug": "1",
            "Info": "2",
            "Warning": "3",
            "Error": "4",
            "Extra Debug": "5",
        }
        syslog_level_value = syslog_level_values.get(syslog_level, "0")

        provisioning_protocol_values = {
            "tftp": "0",
            "http": "1",
            "https": "2",
            "ftp": "3",
            "ftps": "4",
        }
        scheme = provisioning_base_url.split("://", 1)[0].lower() if "://" in provisioning_base_url else ""
        provisioning_protocol = provisioning_protocol_values.get(scheme, "")

        line_blocks = []
        # Line 1 (FXS1)
        line_blocks.append(
            dedent(
                f"""
                <P4060>{line1.registration_account}</P4060>
                <P4090>{line1.registration_account}</P4090>
                <P4180>{line1.name}</P4180>
                <P4120>{line1.registration_password}</P4120>
                """
            ).strip()
        )

        # Line 2 (FXS2) if present
        if line2 is not None:
            line_blocks.append(
                dedent(
                    f"""
                    <P4061>{line2.registration_account}</P4061>
                    <P4091>{line2.registration_account}</P4091>
                    <P4181>{line2.name}</P4181>
                    <P4121>{line2.registration_password}</P4121>
                    """
                ).strip()
            )

        # Offhook autodial numbers (per-port)
        offhook_block = ""
        if offhook1:
            offhook_block += f"\n<P4210>{offhook1}</P4210>"
        if offhook2:
            offhook_block += f"\n<P4211>{offhook2}</P4211>"

        # Primary SIP transport and RTP start
        profile_block = dedent(
            f"""
            <P130>{transport_xml_value}</P130>
            <P5004>{local_rtp_port}</P5004>
            <P84>{sip_keepalive_interval}</P84>
            <P2397>{'1' if enable_sip_keepalive else '0'}</P2397>
            <P138>{registration_retry_interval}</P138>
            <P4567>{'1' if prefer_primary_server else '0'}</P4567>
            <P91>0</P91>
            <P271>1</P271>
            <P47>{primary.host}</P47>
            <P967>{getattr(secondary, 'host', '')}</P967>
            <P5046>{sip_dscp}</P5046>
            <P5050>{rtp_dscp}</P5050>
            """
        ).strip()

        provisioning_block = dedent(
            f"""
            <P192>{provisioning_base_url}</P192>
            <P237>{provisioning_base_url}</P237>
            {f'<P212>{provisioning_protocol}</P212>' if provisioning_protocol else ''}
            """
        ).strip()

        network_block = dedent(
            f"""
            <P146>{dhcp_hostname}</P146>
            <P901>{http_port}</P901>
            <P27010>{https_port}</P27010>
            """
        ).strip()

        dtmf_block = dedent(
            f"""
            <P79>{dtmf_payload_id}</P79>
            <P850>{dtmf_1_value}</P850>
            <P851>{dtmf_2_value}</P851>
            <P852>{dtmf_3_value}</P852>
            """
        ).strip()

        syslog_block = ""
        if syslog_server or syslog_level_value != "0":
            syslog_block = dedent(
                f"""
                <P207>{syslog_server}</P207>
                <P208>{syslog_level_value}</P208>
                """
            ).strip()

        # Optionally include secondary server hint via XML comment for visibility
        secondary_hint = ""
        if secondary:
            secondary_hint = f"<!-- Secondary SIP Server: {secondary.host}:{secondary.port} / {secondary.transport} -->"

        # SNMP block
        snmp_block = ""
        if snmp_enable:
            snmp_block = dedent(
                f"""
                <P21896>1</P21896>
                <P21897>{snmp_trap_ip}</P21897>
                <P21898>{snmp_trap_port}</P21898>
                <P21902>{snmp_poll_comm}</P21902>
                <P21900>{snmp_trap_comm}</P21900>
                """
            ).strip()

        # Admin password
        admin_block = f"<P2>{admin_password}</P2>" if admin_password else ""

        # Dial plan conversion (site-level)
        dialplan_block = ""
        dial_plan = getattr(site, "dial_plan", None)
        if dial_plan:
            rules = dial_plan.rules.all().order_by("sequence_order")
            dialplan_entries = []
            for rule in rules:
                entry = self._convert_to_grandstream_dialplan(rule.input_regex, rule.output_regex)
                if entry:
                    dialplan_entries.append(entry)
            
            if dialplan_entries:
                # Grandstream dial plan format: { rule1 | rule2 | rule3 }
                dialplan_string = "{ " + " | ".join(dialplan_entries) + " }"
                # P2396 is the dial plan P-code for FXS1, P2398 for FXS2
                # We'll apply the same dial plan to both ports
                dialplan_block = dedent(
                    f"""
                    <P2396>{dialplan_string}</P2396>
                    <P2398>{dialplan_string}</P2398>
                    """
                ).strip()

        xml = dedent(
            f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!-- Auto-generated by PhoneManager -->
            <gs_provision version="1">
              <mac>{mac_clean}</mac>
              <config version="1">
                                <!-- Provisioning server -->
                                {provisioning_block}

                                <!-- Network settings -->
                                {network_block}

                                <!-- Regional tones (AU) -->
                {tones_xml}

                <!-- SIP profile basics -->
                {profile_block}
                {timer_block}
                                {dtmf_block}
                                {syslog_block}
                {'\n'.join(codec_tags)}

                <!-- Line identities for FXS ports -->
                {'\n'.join(line_blocks)}
                {offhook_block}

                <!-- SNMP settings -->
                {snmp_block}

                <!-- Administrative password -->
                {admin_block}

                <!-- Dial plan transformation rules -->
                {dialplan_block}

                <!-- Site primary SIP Server: {primary.host}:{primary.port} / {primary.transport} -->
                {secondary_hint}
              </config>
            </gs_provision>
            """
        ).strip()

        return xml
