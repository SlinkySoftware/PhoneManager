# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Tests for provisioning endpoint behavior."""

from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

from core.models import Device, Line, SIPServer, Site
from provisioning.device_types.base import DeviceType


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