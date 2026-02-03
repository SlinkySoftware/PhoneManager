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


COMMON_OPTIONS: Dict[str, Any] = {
    "sections": [
        {
            "friendlyName": "SIP Profile 1",
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
                    "optionId": "rtp_start_port",
                    "friendlyName": "RTP Start Port",
                    "default": 6004,
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
                {
                    "optionId": "session_expiration",
                    "friendlyName": "Session Expiration (s)",
                    "default": 1800,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 4,
                },
                {
                    "optionId": "min_se",
                    "friendlyName": "Min-SE (s)",
                    "default": 90,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 5,
                },
                {
                    "optionId": "enable_session_timer",
                    "friendlyName": "Enable Session Timer",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 6,
                },
                {
                    "optionId": "preferred_codecs",
                    "friendlyName": "Preferred Codec Order",
                    "default": ["PCMU", "PCMA", "G729", "G722", "OPUS"],
                    "mandatory": True,
                    "type": "orderedmultiselect",
                    "choices": ["PCMU", "PCMA", "G729", "G722", "OPUS", "G726-32", "G723", "iLBC"],
                    "uiOrder": 7,
                },
                {
                    "optionId": "sip_dscp",
                    "friendlyName": "SIP DSCP (P5046)",
                    "default": 26,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 8,
                },
                {
                    "optionId": "rtp_dscp",
                    "friendlyName": "RTP DSCP (P5050)",
                    "default": 46,
                    "mandatory": False,
                    "type": "number",
                    "uiOrder": 9,
                },
            ],
        },
        {
            "friendlyName": "Regional",
            "uiOrder": 2,
            "options": [
                {
                    "optionId": "region_tones",
                    "friendlyName": "Apply AU Tone Plan",
                    "default": True,
                    "mandatory": False,
                    "type": "boolean",
                    "uiOrder": 1,
                }
            ],
        },
        {
            "friendlyName": "SNMP",
            "uiOrder": 3,
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
            "friendlyName": "FXS Ports",
            "uiOrder": 1,
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
            "uiOrder": 2,
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
    CommonOptions = COMMON_OPTIONS
    DeviceSpecificOptions = DEVICE_OPTIONS
    ContentType = "text/xml"

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
        rtp_start = int(cfg.get("rtp_start_port", 6004))
        enable_100rel = bool(cfg.get("enable_100rel", True))
        session_exp = int(cfg.get("session_expiration", 1800))
        min_se = int(cfg.get("min_se", 90))
        enable_timer = bool(cfg.get("enable_session_timer", True))
        codec_order = cfg.get("preferred_codecs") or ["PCMU", "PCMA", "G729", "G722", "OPUS"]
        codec_pvalues = self._codec_pvalues(codec_order)

        sip_dscp = int(cfg.get("sip_dscp", 26))
        rtp_dscp = int(cfg.get("rtp_dscp", 46))

        snmp_enable = bool(cfg.get("enable_snmp", False))
        snmp_trap_ip = cfg.get("snmp_trap_ip") or ""
        snmp_trap_port = int(cfg.get("snmp_trap_port", 162))
        snmp_poll_comm = cfg.get("snmp_poll_community") or ""
        snmp_trap_comm = cfg.get("snmp_trap_community") or ""

        offhook1 = cfg.get("offhook_autodial_1", "")
        offhook2 = cfg.get("offhook_autodial_2", "")
        admin_password = cfg.get("admin_password") or ""

        mac_clean = self._mac_nocolon(device.mac_address)

        # Build XML. Only include parameters we intentionally manage.
        # Tones (AU) copied from reference config (docs example)
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

        # SIP transport P2912 expects lowercase string (e.g., 'udp') in example
        transport_xml_value = transport.lower()

        # Enable 100rel (P26061 observed as 2 in example for enabled)
        p26061 = "2" if enable_100rel else "0"

        # Session timers: model-specific; include if enabled (use common defaults)
        # P4510 seen as 60 in example (Session Expiration). P4518 appears elsewhere.
        # We'll set P4510 (Session Expiration) and P4518 (Min-SE) when timers enabled.
        timer_block = ""
        if enable_timer:
            timer_block = dedent(
                f"""
                <P4510>{session_exp}</P4510>
                <P4518>{min_se}</P4518>
                """
            ).strip()

        # RTP start port appears as P739 in example (6004). We'll set it.
        # Preferred codecs appear as multiple P504..P505.. etc in example; keep it simple
        # and emit the list using the lowest two slots P504 (1st), P505 (2nd), ... when present.
        codec_tags: List[str] = []
        for idx, pv in enumerate(codec_pvalues[:8]):
            # P504..P511 sequence commonly maps to codec preference order on HT models
            tag_num = 504 + idx
            codec_tags.append(f"<P{tag_num}>{pv}</P{tag_num}>")

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
            # P860 likely relates to speed dial; use placeholders P860/P861 from example vicinity
            offhook_block += f"\n<P860>{offhook1}</P860>"
        if offhook2:
            offhook_block += f"\n<P861>{offhook2}</P861>"

        # Primary SIP transport and RTP start
        profile_block = dedent(
            f"""
            <P2912>{transport_xml_value}</P2912>
            <P739>{rtp_start}</P739>
            <P26061>{p26061}</P26061>
            <P271>1</P271>
            <P47>{primary.host}</P47>
            <P967>{getattr(secondary, 'host', '')}</P967>
            <P5046>{sip_dscp}</P5046>
            <P5050>{rtp_dscp}</P5050>
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
                <!-- Regional tones (AU) -->
                {tones_xml}

                <!-- SIP profile basics -->
                {profile_block}
                {timer_block}
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
