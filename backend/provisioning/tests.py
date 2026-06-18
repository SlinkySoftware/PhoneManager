# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Tests for provisioning endpoint behavior."""

from unittest.mock import patch

from django.db import DatabaseError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.models import Device, DeviceTypeConfig, DialPlan, DialPlanRule, Line, SIPServer, Site
from provisioning.device_types.base import DeviceType
from provisioning.device_types.grandstream_ht812 import GrandstreamHT812
from provisioning.device_types.yealink_sip_t33g import YealinkSIPT33G
from provisioning.device_types.yealink_w70b_dect import YealinkW70BDECT


class FakeProvisioningPhone(DeviceType):
    """Minimal device type used to exercise provisioning responses."""

    TypeID = "FakeProvisioningPhone"
    Manufacturer = "Slinky"
    Model = "Test Phone"
    NumberOfLines = 1
    CommonOptions = {}
    DeviceSpecificOptions = {}
    ContentType = "text/plain"
    UserAgentPatterns = ()

    def render(self, device):
        return f"config for {device.mac_address}"


class FakeProvisioningBaseUrlPhone(DeviceType):
    """Minimal device type used to exercise provisioning base URL fallback."""

    TypeID = "FakeProvisioningBaseUrlPhone"
    Manufacturer = "Slinky"
    Model = "Test URL Phone"
    NumberOfLines = 1
    CommonOptions = {}
    DeviceSpecificOptions = {}
    ContentType = "text/plain"
    UserAgentPatterns = ()

    def render(self, device):
        return self.get_provisioning_base_url()


class FakeProvisioningSecurityPhone(DeviceType):
    """Minimal device type used to exercise renderer-owned security assets."""

    TypeID = "FakeProvisioningSecurityPhone"
    Manufacturer = "Slinky"
    Model = "Test Security Phone"
    NumberOfLines = 1
    CommonOptions = {}
    DeviceSpecificOptions = {}
    ContentType = "text/plain"
    UserAgentPatterns = ()
    lockdown_filename = "fake-secure.cfg"
    lockdown_payload = "[GUI]\nbluetooth = 1"

    def render(self, device):
        return "security test"


class ProvisioningViewSetTests(TestCase):
    """Exercise config delivery and best-effort metadata tracking."""

    def setUp(self):
        self.sip_server = SIPServer.objects.create(name="Primary", host="pbx.example.test", port=5060)
        self.site = Site.objects.create(name="HQ", primary_sip_server=self.sip_server, timezone="UTC")
        self.line = Line.objects.create(
            name="Main",
            phone_label="Main",
            directory_number="1001",
            registration_account="1001",
            registration_password="secret",
            is_shared=False,
        )
        self.device = Device.objects.create(
            mac_address="AA:BB:CC:DD:EE:FF",
            description="Lobby phone",
            device_type_id=FakeProvisioningPhone.TypeID,
            site=self.site,
            line_1=self.line,
            enabled=True,
        )
        self.url = reverse("provision-device", args=[self.device.mac_address])

        self.views_type_patcher = patch("provisioning.views.get_device_type", return_value=FakeProvisioningPhone)
        self.registry_type_patcher = patch("provisioning.registry.get_device_type", return_value=FakeProvisioningPhone)
        self.views_type_patcher.start()
        self.registry_type_patcher.start()
        self.addCleanup(self.views_type_patcher.stop)
        self.addCleanup(self.registry_type_patcher.stop)

    def test_retrieve_persists_provisioning_metadata_on_success(self):
        response = self.client.get(self.url, HTTP_X_REAL_IP="198.51.100.10")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), f"config for {self.device.mac_address}")
        self.assertTrue(response["Content-Type"].startswith(FakeProvisioningPhone.ContentType))

        self.device.refresh_from_db()
        self.assertIsNotNone(self.device.last_provisioned_at)
        self.assertEqual(self.device.last_requested_ip_address, "198.51.100.10")

    def test_retrieve_supports_cfg_prefixed_mac_formats(self):
        for request_path in ("/provision/cfgaabbccddeeff", "/provision/cfgaabbccddeeff.cfg"):
            with self.subTest(request_path=request_path):
                response = self.client.get(request_path)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content.decode(), f"config for {self.device.mac_address}")

    def test_retrieve_falls_back_to_request_base_url_when_not_configured(self):
        with (
            patch("provisioning.views.get_device_type", return_value=FakeProvisioningBaseUrlPhone),
            patch("provisioning.registry.get_device_type", return_value=FakeProvisioningBaseUrlPhone),
            patch("provisioning.device_types.base.config.get", return_value=""),
        ):
            response = self.client.get("/provision/cfgaabbccddeeff.xml", HTTP_HOST="pbx.example.test:8000")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "http://pbx.example.test:8000/provision")

    def test_retrieve_returns_config_when_metadata_write_fails(self):
        with (
            patch(
                "provisioning.views._record_last_provisioning_metadata",
                side_effect=DatabaseError("read-only replica"),
            ) as mock_record,
            patch("provisioning.views.logger.exception") as mock_logger,
        ):
            response = self.client.get(self.url, HTTP_X_REAL_IP="198.51.100.20")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), f"config for {self.device.mac_address}")
        self.assertTrue(response["Content-Type"].startswith(FakeProvisioningPhone.ContentType))

        recorded_device, recorded_ip = mock_record.call_args.args
        self.assertEqual(recorded_device.pk, self.device.pk)
        self.assertEqual(recorded_ip, "198.51.100.20")
        mock_logger.assert_called_once()

        self.device.refresh_from_db()
        self.assertIsNone(self.device.last_provisioned_at)
        self.assertIsNone(self.device.last_requested_ip_address)

    def test_security_asset_returns_renderer_payload(self):
        with patch(
            "provisioning.views.get_device_type_by_lockdown_filename",
            return_value=FakeProvisioningSecurityPhone,
        ):
            response = self.client.get(
                reverse("provision-security-asset", args=[FakeProvisioningSecurityPhone.lockdown_filename])
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "[GUI]\nbluetooth = 1\n")
        self.assertTrue(response["Content-Type"].startswith("text/plain"))

    def test_security_asset_returns_t33g_renderer_payload(self):
        response = self.client.get(reverse("provision-security-asset", args=[YealinkSIPT33G.lockdown_filename]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), YealinkSIPT33G.get_lockdown_payload())

    def test_security_asset_returns_w70b_renderer_payload(self):
        response = self.client.get(reverse("provision-security-asset", args=[YealinkW70BDECT.lockdown_filename]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), YealinkW70BDECT.get_lockdown_payload())

    def test_security_asset_returns_404_for_unknown_asset(self):
        response = self.client.get(reverse("provision-security-asset", args=["unknown-secure.cfg"]))

        self.assertEqual(response.status_code, 404)


class GrandstreamHT812RendererTests(TestCase):
    """Exercise core SIP fields rendered for the HT812."""

    def setUp(self):
        self.factory = RequestFactory()
        self.sip_server = SIPServer.objects.create(name="Primary", host="172.19.80.80", port=5060)
        self.site = Site.objects.create(name="Branch", primary_sip_server=self.sip_server, timezone="UTC")
        self.line = Line.objects.create(
            name="Extn 36503",
            phone_label="Reception 36503",
            directory_number="36503",
            registration_account="36503",
            registration_password="secret",
            is_shared=False,
        )
        self.device = Device.objects.create(
            mac_address="C0:74:AD:DE:96:9A",
            description="HT812",
            device_type_id=GrandstreamHT812.TypeID,
            site=self.site,
            line_1=self.line,
            enabled=True,
        )

    def _renderer(self) -> GrandstreamHT812:
        return GrandstreamHT812(
            TypeID=GrandstreamHT812.TypeID,
            Manufacturer=GrandstreamHT812.Manufacturer,
            Model=GrandstreamHT812.Model,
            NumberOfLines=GrandstreamHT812.NumberOfLines,
            CommonOptions=GrandstreamHT812.CommonOptions,
            DeviceSpecificOptions=GrandstreamHT812.DeviceSpecificOptions,
            SupportsSIPServersPerLine=GrandstreamHT812.SupportsSIPServersPerLine,
            ContentType=GrandstreamHT812.ContentType,
            UserAgentPatterns=GrandstreamHT812.UserAgentPatterns,
        )

    def test_render_includes_core_sip_profile_fields(self):
        renderer = self._renderer()
        renderer.request = self.factory.get("/provision/cfgc074adde969a.xml", HTTP_HOST="pbx.example.test:8000")

        with patch("provisioning.device_types.base.config.get", return_value=""):
            xml = renderer.render(self.device)

        self.assertIn("<P47>172.19.80.80</P47>", xml)
        self.assertIn("<P193>5060</P193>", xml)
        self.assertIn("<P8617>172.19.80.80</P8617>", xml)
        self.assertIn("<P4060>36503</P4060>", xml)
        self.assertIn("<P4090>36503</P4090>", xml)
        self.assertIn("<P4180>Reception 36503</P4180>", xml)
        self.assertIn("<P4120>secret</P4120>", xml)

    def test_convert_to_grandstream_dialplan_escapes_plus_and_skips_empty_substitutions(self):
        renderer = self._renderer()

        self.assertEqual(
            renderer._convert_to_grandstream_dialplan("0([234]XXXX)", "+61$1"),
            r"<0=\+61>[234]xxxx",
        )
        self.assertEqual(
            renderer._convert_to_grandstream_dialplan("(365XX)", "$1"),
            "365xx",
        )
        self.assertEqual(
            renderer._convert_to_grandstream_dialplan("(1[38]XXXX*)", "+61$1"),
            r"<=\+61>1[38]xxxx+T",
        )
        self.assertEqual(
            renderer._convert_to_grandstream_dialplan("0011(XXXXXXX*)", "+$1"),
            r"<0011=\+>xxxxxxx+T",
        )

    def test_render_dialplan_uses_device_compatible_syntax(self):
        dial_plan = DialPlan.objects.create(name="Grandstream", description="Grandstream test plan")
        DialPlanRule.objects.create(dial_plan=dial_plan, input_regex="^000$", output_regex="+61000", sequence_order=0)
        DialPlanRule.objects.create(
            dial_plan=dial_plan,
            input_regex="^0([23478]XXXXXXXX)$",
            output_regex="+61$1",
            sequence_order=1,
        )
        DialPlanRule.objects.create(
            dial_plan=dial_plan,
            input_regex="^(1[38]XXXX*)$",
            output_regex="+61$1",
            sequence_order=2,
        )
        DialPlanRule.objects.create(
            dial_plan=dial_plan,
            input_regex="^0011(XXXXXXX*)$",
            output_regex="+$1",
            sequence_order=3,
        )
        DialPlanRule.objects.create(
            dial_plan=dial_plan,
            input_regex="^([98746]XXXXXXX)$",
            output_regex="+612$1",
            sequence_order=4,
        )
        DialPlanRule.objects.create(
            dial_plan=dial_plan,
            input_regex="^(365XX)$",
            output_regex="$1",
            sequence_order=5,
        )
        self.site.dial_plan = dial_plan
        self.site.save(update_fields=["dial_plan"])

        renderer = self._renderer()
        renderer.request = self.factory.get("/provision/cfgc074adde969a.xml", HTTP_HOST="pbx.example.test:8000")

        with patch("provisioning.device_types.base.config.get", return_value=""):
            xml = renderer.render(self.device)

        self.assertIn(
            r"<P4200>{<=\+61>000|<0=\+61>[23478]xxxxxxxx|<=\+61>1[38]xxxx+T|<0011=\+>xxxxxxx+T|<=\+612>[98746]xxxxxxx|365xx|x+}</P4200>",
            xml,
        )


class YealinkSIPT33GRendererTests(TestCase):
    """Exercise SIP-T33G specific rendering branches."""

    def setUp(self):
        self.factory = RequestFactory()
        self.sip_server = SIPServer.objects.create(name="Primary", host="172.19.80.80", port=5060)
        self.site = Site.objects.create(name="Branch", primary_sip_server=self.sip_server, timezone="UTC")
        self.line = Line.objects.create(
            name="Extn 36503",
            phone_label="Reception 36503",
            directory_number="36503",
            registration_account="36503",
            registration_password="secretpass",
            is_shared=False,
        )
        self.device = Device.objects.create(
            mac_address="C0:74:AD:DE:96:9A",
            description="Yealink T33G",
            device_type_id=YealinkSIPT33G.TypeID,
            site=self.site,
            line_1=self.line,
            enabled=True,
        )
        self.device_type_config = DeviceTypeConfig.objects.create(type_id=YealinkSIPT33G.TypeID)

    def _renderer(self) -> YealinkSIPT33G:
        return YealinkSIPT33G(
            TypeID=YealinkSIPT33G.TypeID,
            Manufacturer=YealinkSIPT33G.Manufacturer,
            Model=YealinkSIPT33G.Model,
            NumberOfLines=YealinkSIPT33G.NumberOfLines,
            CommonOptions=YealinkSIPT33G.CommonOptions,
            DeviceSpecificOptions=YealinkSIPT33G.DeviceSpecificOptions,
            SupportsSIPServersPerLine=YealinkSIPT33G.SupportsSIPServersPerLine,
            ContentType=YealinkSIPT33G.ContentType,
            UserAgentPatterns=YealinkSIPT33G.UserAgentPatterns,
        )

    def _configure_phone_service(self, *, enabled: bool, url: str, key_number: int = 3, label: str = "") -> None:
        self.device_type_config.set_encrypted_saved_values(
            {
                "phone_service_url": url,
                "phone_service_programmable_key_number": key_number,
                "phone_service_label": label,
            }
        )
        self.device_type_config.save(update_fields=["common_options"])

        self.device.set_encrypted_device_config({"use_phone_services": enabled})
        self.device.save(update_fields=["device_specific_configuration"])

    def test_render_includes_phone_service_programmable_key_when_enabled(self):
        self._configure_phone_service(
            enabled=True,
            url="http://phoneservices.example.internal/services/",
            key_number=5,
            label="Services",
        )

        config = self._renderer().render(self.device)

        self.assertIn("programablekey.5.label = Services", config)
        self.assertIn("programablekey.5.line = 0", config)
        self.assertIn("programablekey.5.type = 27", config)
        self.assertIn(
            "programablekey.5.value = "
            "http://phoneservices.example.internal/services/?mac=C0%3A74%3AAD%3ADE%3A96%3A9A&dn=36503&token=secretpa",
            config,
        )

    def test_render_omits_phone_service_programmable_key_when_disabled_or_url_blank(self):
        scenarios = [
            {"enabled": False, "url": "http://phoneservices.example.internal/services/"},
            {"enabled": True, "url": ""},
        ]

        for scenario in scenarios:
            with self.subTest(**scenario):
                self._configure_phone_service(enabled=scenario["enabled"], url=scenario["url"])

                config = self._renderer().render(self.device)

                self.assertNotIn("programablekey.3.label =", config)
                self.assertNotIn("programablekey.3.line = 0", config)
                self.assertNotIn("programablekey.3.type = 27", config)
                self.assertNotIn("programablekey.3.value =", config)

    def test_render_includes_lockdown_url_when_enabled(self):
        self.device.set_encrypted_device_config({"phone_lockdown": True})
        self.device.save(update_fields=["device_specific_configuration"])

        renderer = self._renderer()
        renderer.request = self.factory.get("/provision/cfgc074adde969a.xml", HTTP_HOST="pbx.example.test:8000")

        with patch("provisioning.device_types.base.config.get", return_value=""):
            config = renderer.render(self.device)

        self.assertIn("static.security.default_access_level = 0", config)
        self.assertIn("static.security.var_enable = 1", config)
        self.assertIn(
            "static.web_item_level.url = http://pbx.example.test:8000/provision/security/sipt33g-secure.cfg",
            config,
        )

    def test_render_omits_lockdown_url_when_disabled(self):
        config = self._renderer().render(self.device)

        self.assertNotIn("static.security.default_access_level = 0", config)
        self.assertNotIn("static.security.var_enable = 1", config)
        self.assertNotIn("static.web_item_level.url =", config)


class YealinkW70BDECTRendererTests(TestCase):
    """Exercise W70B-specific rendering branches."""

    def setUp(self):
        self.factory = RequestFactory()
        self.test_registration_secret = "w70b-test-secret"
        self.sip_server = SIPServer.objects.create(name="Primary", host="pbx.example.test", port=5060)
        self.site = Site.objects.create(name="Branch", primary_sip_server=self.sip_server, timezone="UTC")
        self.line = Line.objects.create(
            name="Extn 36503",
            phone_label="Reception 36503",
            directory_number="36503",
            registration_account="36503",
            registration_password=self.test_registration_secret,
            is_shared=False,
        )
        self.device = Device.objects.create(
            mac_address="C0:74:AD:DE:96:9B",
            description="Yealink W70B",
            device_type_id=YealinkW70BDECT.TypeID,
            site=self.site,
            line_1=self.line,
            enabled=True,
        )

    def _renderer(self) -> YealinkW70BDECT:
        return YealinkW70BDECT(
            TypeID=YealinkW70BDECT.TypeID,
            Manufacturer=YealinkW70BDECT.Manufacturer,
            Model=YealinkW70BDECT.Model,
            NumberOfLines=YealinkW70BDECT.NumberOfLines,
            CommonOptions=YealinkW70BDECT.CommonOptions,
            DeviceSpecificOptions=YealinkW70BDECT.DeviceSpecificOptions,
            SupportsSIPServersPerLine=YealinkW70BDECT.SupportsSIPServersPerLine,
            ContentType=YealinkW70BDECT.ContentType,
            UserAgentPatterns=YealinkW70BDECT.UserAgentPatterns,
        )

    def test_render_includes_lockdown_url_when_enabled(self):
        self.device.set_encrypted_device_config({"phone_lockdown": True})
        self.device.save(update_fields=["device_specific_configuration"])

        renderer = self._renderer()
        renderer.request = self.factory.get("/provision/cfgc074adde969b.xml", HTTP_HOST="pbx.example.test:8000")

        with patch("provisioning.device_types.base.config.get", return_value=""):
            config = renderer.render(self.device)

        self.assertIn("static.security.default_access_level = 0", config)
        self.assertIn("static.security.var_enable = 1", config)
        self.assertIn(
            "static.web_item_level.url = http://pbx.example.test:8000/provision/security/w70b-secure.cfg",
            config,
        )

    def test_render_omits_lockdown_url_when_disabled(self):
        config = self._renderer().render(self.device)

        self.assertNotIn("static.security.default_access_level = 0", config)
        self.assertNotIn("static.security.var_enable = 1", config)
        self.assertNotIn("static.web_item_level.url =", config)