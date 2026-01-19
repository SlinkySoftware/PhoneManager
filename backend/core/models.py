# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Core data models for Phone Provisioning Manager.

These models mirror the frontend-oriented structure described in the build prompt.
"""
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


mac_validator = RegexValidator(
    regex=r"^[0-9A-Fa-f]{2}(:?[0-9A-Fa-f]{2}){5}$",
    message="MAC address must be 12 hex characters (colon optional)",
)


class SIPServer(models.Model):
    TRANSPORT_TLS = "TLS"
    TRANSPORT_UDP = "UDP"
    TRANSPORT_TCP = "TCP"
    TRANSPORT_CHOICES = [
        (TRANSPORT_TLS, "TLS"),
        (TRANSPORT_UDP, "UDP"),
        (TRANSPORT_TCP, "TCP"),
    ]

    name = models.CharField(max_length=128, unique=True)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=5060)
    transport = models.CharField(max_length=4, choices=TRANSPORT_CHOICES, default=TRANSPORT_UDP)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.host}:{self.port}/{self.transport})"


class Site(models.Model):
    name = models.CharField(max_length=128, unique=True)
    primary_sip_server = models.ForeignKey(SIPServer, on_delete=models.PROTECT, related_name="primary_sites")
    secondary_sip_server = models.ForeignKey(
        SIPServer, on_delete=models.PROTECT, related_name="secondary_sites", null=True, blank=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Line(models.Model):
    name = models.CharField(max_length=128)
    directory_number = models.CharField(max_length=32)
    registration_account = models.CharField(max_length=64)
    registration_password = models.CharField(max_length=256)
    is_shared = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.directory_number})"


class DeviceTypeConfig(models.Model):
    """Stores mutable CommonOptions per registered device type (identified by TypeID)."""

    type_id = models.CharField(max_length=128, unique=True)
    common_options = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["type_id"]

    def __str__(self) -> str:
        return self.type_id


class Device(models.Model):
    mac_address = models.CharField(max_length=17, unique=True, validators=[mac_validator])
    description = models.CharField(max_length=255, blank=True)
    device_type_id = models.CharField(max_length=128)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="devices")
    line_1 = models.ForeignKey(Line, on_delete=models.PROTECT, related_name="primary_devices")
    lines = models.ManyToManyField(Line, related_name="devices", blank=True)
    device_specific_configuration = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["mac_address"]

    def clean(self) -> None:
        if not self.mac_address:
            raise ValidationError("MAC address required")

    def __str__(self) -> str:
        return self.mac_address
