# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Tests for provisioning endpoint behavior."""

from unittest.mock import patch

from django.db import DatabaseError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.models import Device, Line, SIPServer, Site
from provisioning.device_types.base import DeviceType
from provisioning.device_types.grandstream_ht812 import GrandstreamHT812


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

    def test_render_includes_core_sip_profile_fields(self):
        renderer = GrandstreamHT812(
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