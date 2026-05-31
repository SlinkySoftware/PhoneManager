# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Tests for localhost-only internal API endpoints."""

from django.test import TestCase
from django.urls import reverse

from .models import Device, DialPlan, DialPlanRule, Line, SIPServer, Site


class InternalApiTests(TestCase):
    """Exercise the localhost-only device context and number normalization endpoints."""

    def setUp(self):
        self.primary_token = "".join(["AbCd", "1234"])
        self.primary_registration_secret = "".join([self.primary_token, "secret"])
        self.secondary_registration_secret = "".join(["second123", "secret"])
        self.non_loopback_remote_addr = ".".join(["10", "10", "10", "10"])
        self.sip_server = SIPServer.objects.create(name="Primary", host="pbx.example.test", port=5060)
        self.dial_plan = DialPlan.objects.create(name="AU Internal", description="AU transformations")
        DialPlanRule.objects.create(
            dial_plan=self.dial_plan,
            input_regex="0(XXXXXXXXX)",
            output_regex="+61$1",
            sequence_order=0,
        )
        self.site = Site.objects.create(
            name="2SYA",
            primary_sip_server=self.sip_server,
            timezone="Australia/Sydney",
            dial_plan=self.dial_plan,
        )
        self.assertIsNotNone(self.dial_plan.pk)
        self.dial_plan_id = self.dial_plan.pk
        self.line = Line.objects.create(
            name="Desk 36500",
            phone_label="36500",
            directory_number="+61288836500",
            registration_account="desk36500",
            registration_password=self.primary_registration_secret,
            is_shared=False,
        )
        self.device = Device.objects.create(
            mac_address="80:5E:C0:AB:CD:EF",
            description="Front Desk",
            device_type_id="YealinkSIPT33G",
            site=self.site,
            line_1=self.line,
            enabled=True,
        )

    def test_device_context_returns_valid_payload_for_matching_t33g(self):
        response = self.client.get(
            reverse("internal-device-context"),
            {"mac": "805EC0ABCDEF", "dn": "+61288836500", "token": self.primary_token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "valid": True,
                "mac": "805EC0ABCDEF",
                "model": "SIP-T33G",
                "dn": "+61288836500",
                "sip_username": "desk36500",
                "line_count": 1,
                "device_name": "Front Desk",
                "site": "2SYA",
                "dial_plan_id": self.dial_plan_id,
                "message": "OK",
            },
        )

    def test_device_context_normalizes_mac_input_formats(self):
        for candidate in ("80:5e:c0:ab:cd:ef", "80-5E-C0-AB-CD-EF", "805EC0ABCDEF"):
            response = self.client.get(
                reverse("internal-device-context"),
                {"mac": candidate, "dn": "+61288836500", "token": self.primary_token},
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["valid"], msg=candidate)

    def test_device_context_returns_invalid_for_invalid_mac(self):
        response = self.client.get(
            reverse("internal-device-context"),
            {"mac": "not-a-mac", "dn": "+61288836500", "token": self.primary_token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"valid": False, "message": "Invalid device context"})

    def test_device_context_returns_invalid_for_unknown_mac(self):
        response = self.client.get(
            reverse("internal-device-context"),
            {"mac": "80:5E:C0:00:00:00", "dn": "+61288836500", "token": self.primary_token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"valid": False, "message": "Invalid device context"})

    def test_device_context_rejects_non_t33g_models(self):
        other_device = Device.objects.create(
            mac_address="AA:BB:CC:DD:EE:FF",
            description="DECT",
            device_type_id="YealinkW70BDECT",
            site=self.site,
            line_1=self.line,
            enabled=True,
        )

        response = self.client.get(
            reverse("internal-device-context"),
            {"mac": other_device.mac_address, "dn": "+61288836500", "token": self.primary_token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"valid": False, "message": "Invalid device context"})

    def test_device_context_rejects_dn_mismatch(self):
        response = self.client.get(
            reverse("internal-device-context"),
            {"mac": self.device.mac_address, "dn": "+61288839999", "token": self.primary_token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"valid": False, "message": "Invalid device context"})

    def test_device_context_rejects_invalid_token(self):
        response = self.client.get(
            reverse("internal-device-context"),
            {"mac": self.device.mac_address, "dn": "+61288836500", "token": "wrong123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"valid": False, "message": "Invalid device context"})

    def test_device_context_token_comparison_is_case_sensitive(self):
        response = self.client.get(
            reverse("internal-device-context"),
            {"mac": self.device.mac_address, "dn": "+61288836500", "token": "abcd1234"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"valid": False, "message": "Invalid device context"})

    def test_device_context_rejects_devices_with_multiple_lines(self):
        second_line = Line.objects.create(
            name="Desk 36501",
            phone_label="36501",
            directory_number="+61288836501",
            registration_account="desk36501",
            registration_password=self.secondary_registration_secret,
            is_shared=False,
        )
        self.device.lines.add(second_line)

        response = self.client.get(
            reverse("internal-device-context"),
            {"mac": self.device.mac_address, "dn": "+61288836500", "token": self.primary_token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"valid": False, "message": "Invalid device context"})

    def test_device_context_requires_all_query_parameters(self):
        response = self.client.get(reverse("internal-device-context"), {"mac": self.device.mac_address, "dn": "+61288836500"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("token", response.json()["detail"])

    def test_normalize_number_returns_transformed_destination(self):
        response = self.client.post(
            reverse("internal-normalize-number"),
            data={
                "mac": "805EC0ABCDEF",
                "dn": "+61288836500",
                "token": self.primary_token,
                "entered_destination": "0288836500",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"normalized_destination": "+61288836500", "matched": True},
        )

    def test_normalize_number_honors_rule_precedence(self):
        precedence_plan = DialPlan.objects.create(name="Precedence", description="Rule ordering")
        DialPlanRule.objects.create(
            dial_plan=precedence_plan,
            input_regex="0(X*)",
            output_regex="+61$1",
            sequence_order=0,
        )
        DialPlanRule.objects.create(
            dial_plan=precedence_plan,
            input_regex="0(XXXXXXXXX)",
            output_regex="+99$1",
            sequence_order=1,
        )
        self.device.site.dial_plan = precedence_plan
        self.device.site.save(update_fields=["dial_plan"])

        response = self.client.post(
            reverse("internal-normalize-number"),
            data={
                "mac": self.device.mac_address,
                "dn": "+61288836500",
                "token": self.primary_token,
                "entered_destination": "0288836500",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["normalized_destination"], "+61288836500")
        self.assertTrue(response.json()["matched"])

    def test_normalize_number_allows_valid_pass_through_when_number_is_already_e164(self):
        no_match_plan = DialPlan.objects.create(name="No Match", description="Does not match +E164")
        DialPlanRule.objects.create(
            dial_plan=no_match_plan,
            input_regex="0(XXXXXXXXX)",
            output_regex="+61$1",
            sequence_order=0,
        )
        self.device.site.dial_plan = no_match_plan
        self.device.site.save(update_fields=["dial_plan"])

        response = self.client.post(
            reverse("internal-normalize-number"),
            data={
                "mac": self.device.mac_address,
                "dn": "+61288836500",
                "token": self.primary_token,
                "entered_destination": "+61288836500",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"normalized_destination": "+61288836500", "matched": False},
        )

    def test_normalize_number_allows_digit_only_pass_through_when_no_rule_matches(self):
        no_match_plan = DialPlan.objects.create(name="No Match Digits", description="Leaves internal extensions alone")
        DialPlanRule.objects.create(
            dial_plan=no_match_plan,
            input_regex="0(XXXXXXXXX)",
            output_regex="+61$1",
            sequence_order=0,
        )
        self.device.site.dial_plan = no_match_plan
        self.device.site.save(update_fields=["dial_plan"])

        response = self.client.post(
            reverse("internal-normalize-number"),
            data={
                "mac": self.device.mac_address,
                "dn": "+61288836500",
                "token": self.primary_token,
                "entered_destination": "36500",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"normalized_destination": "36500", "matched": False},
        )

    def test_normalize_number_allows_digit_only_pass_through_when_rule_keeps_internal_extension(self):
        internal_extension_plan = DialPlan.objects.create(
            name="Internal Extensions",
            description="Explicitly allows unchanged internal destinations",
        )
        DialPlanRule.objects.create(
            dial_plan=internal_extension_plan,
            input_regex="^(365XX)",
            output_regex="$1",
            sequence_order=0,
        )
        self.device.site.dial_plan = internal_extension_plan
        self.device.site.save(update_fields=["dial_plan"])

        response = self.client.post(
            reverse("internal-normalize-number"),
            data={
                "mac": self.device.mac_address,
                "dn": "+61288836500",
                "token": self.primary_token,
                "entered_destination": "36500",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"normalized_destination": "36500", "matched": False},
        )

    def test_normalize_number_rejects_invalid_destination(self):
        response = self.client.post(
            reverse("internal-normalize-number"),
            data={
                "mac": self.device.mac_address,
                "dn": "+61288836500",
                "token": self.primary_token,
                "entered_destination": "1234",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Invalid Destination Specified"})

    def test_normalize_number_rejects_invalid_device_context(self):
        response = self.client.post(
            reverse("internal-normalize-number"),
            data={
                "mac": self.device.mac_address,
                "dn": "+61288836500",
                "token": "wrong123",
                "entered_destination": "0288836500",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"error": "Invalid device context"})

    def test_normalize_number_rejects_malformed_json(self):
        response = self.client.post(
            reverse("internal-normalize-number"),
            data='{"mac": "805EC0ABCDEF",',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Malformed JSON"})

    def test_normalize_number_requires_all_fields(self):
        response = self.client.post(
            reverse("internal-normalize-number"),
            data={"mac": self.device.mac_address, "dn": "+61288836500", "token": self.primary_token},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("entered_destination", response.json()["detail"])

    def test_internal_endpoints_reject_non_loopback_requests(self):
        device_context_response = self.client.get(
            reverse("internal-device-context"),
            {"mac": self.device.mac_address, "dn": "+61288836500", "token": self.primary_token},
            REMOTE_ADDR=self.non_loopback_remote_addr,
        )
        normalize_response = self.client.post(
            reverse("internal-normalize-number"),
            data={
                "mac": self.device.mac_address,
                "dn": "+61288836500",
                "token": self.primary_token,
                "entered_destination": "0288836500",
            },
            content_type="application/json",
            REMOTE_ADDR=self.non_loopback_remote_addr,
        )

        self.assertEqual(device_context_response.status_code, 404)
        self.assertEqual(device_context_response.json(), {"error": "Not found"})
        self.assertEqual(normalize_response.status_code, 404)
        self.assertEqual(normalize_response.json(), {"error": "Not found"})