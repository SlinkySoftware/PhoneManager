# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Core data models for Phone Provisioning Manager.

These models mirror the frontend-oriented structure described in the build prompt.
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
import pytz

from .fields import EncryptedCharField
from .encryption import decrypt_password, encrypt_password


def normalize_mac(mac: str) -> str:
    """Normalize MAC to colon-separated uppercase form."""
    if not mac:
        return mac
    cleaned = mac.replace("-", "").replace(":", "").upper()
    if len(cleaned) != 12:
        return mac
    # Insert colons every 2 characters
    return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))


mac_validator = RegexValidator(
    regex=r"^[0-9A-Fa-f]{2}([:-]?[0-9A-Fa-f]{2}){5}$",
    message="MAC address must be 12 hex characters (colon or dash optional)",
)


class UserProfile(models.Model):
    """Extended user profile for role-based access control and SSO integration."""
    
    ROLE_ADMIN = 'admin'
    ROLE_READONLY = 'readonly'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Administrator'),
        (ROLE_READONLY, 'Read Only'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_READONLY)
    is_sso = models.BooleanField(default=False, help_text="True if user authenticates via SAML SSO")
    force_password_reset = models.BooleanField(default=False, help_text="User must change password on next login")
    
    class Meta:
        ordering = ['user__username']
    
    def __str__(self) -> str:
        return f"{self.user.username} ({self.get_role_display()})"


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


class DialPlan(models.Model):
    """Dial plan for phone number transformation rules."""
    name = models.CharField(max_length=128, unique=True, help_text="Dial plan name")
    description = models.TextField(blank=True, help_text="Description of dial plan purpose")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class DialPlanRule(models.Model):
    """Individual transformation rule within a dial plan."""
    dial_plan = models.ForeignKey(DialPlan, on_delete=models.CASCADE, related_name="rules")
    input_regex = models.CharField(max_length=512, help_text="Input pattern (standard format with X, *, [], [^], ())")
    output_regex = models.CharField(max_length=512, help_text="Output pattern with $1, $2, etc. for capture groups")
    sequence_order = models.PositiveIntegerField(default=0, help_text="Rule execution order (ascending)")

    class Meta:
        ordering = ["dial_plan", "sequence_order"]
        constraints = [
            UniqueConstraint(fields=["dial_plan", "sequence_order"], name="unique_dial_plan_rule_order"),
        ]

    def __str__(self) -> str:
        return f"{self.dial_plan.name} - Rule {self.sequence_order}"


class Site(models.Model):
    name = models.CharField(max_length=128, unique=True)
    primary_sip_server = models.ForeignKey(SIPServer, on_delete=models.PROTECT, related_name="primary_sites")
    secondary_sip_server = models.ForeignKey(
        SIPServer, on_delete=models.PROTECT, related_name="secondary_sites", null=True, blank=True
    )
    timezone = models.CharField(
        max_length=64,
        choices=[(tz, tz) for tz in pytz.common_timezones],
        default="UTC",
        help_text="Timezone for the site"
    )
    primary_ntp_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Primary NTP server IP address"
    )
    secondary_ntp_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Secondary NTP server IP address"
    )
    dial_plan = models.ForeignKey(
        DialPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sites",
        help_text="Dial plan for phone number transformation at this site"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Line(models.Model):
    name = models.CharField(max_length=128)
    phone_label = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Label displayed on device screens",
    )
    directory_number = models.CharField(max_length=32)
    registration_account = models.CharField(max_length=64)
    registration_password = EncryptedCharField(max_length=512)  # Encrypted storage, decrypted on access
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
    
    def get_decrypted_saved_values(self):
        """Get saved values with passwords decrypted.
        
        Returns dict with password fields decrypted for use in rendering.
        """
        saved_values = self.common_options.get('_saved_values', {})
        if not saved_values:
            return {}
        
        # Import here to avoid circular dependency
        from provisioning.registry import get_device_type
        
        device_type_cls = get_device_type(self.type_id)
        if not device_type_cls:
            return saved_values
        
        # Identify password fields from CommonOptions schema
        password_fields = set()
        for section in device_type_cls.CommonOptions.get('sections', []):
            for option in section.get('options', []):
                if option.get('type') == 'password':
                    password_fields.add(option['optionId'])
        
        # Decrypt password fields
        decrypted = {}
        for key, value in saved_values.items():
            if key in password_fields and value:
                decrypted[key] = decrypt_password(value)
            else:
                decrypted[key] = value
        
        return decrypted
    
    def set_encrypted_saved_values(self, values: dict):
        """Set saved values with passwords encrypted.
        
        Args:
            values: Dict of plaintext values from API/frontend
        """
        # Import here to avoid circular dependency
        from provisioning.registry import get_device_type
        
        device_type_cls = get_device_type(self.type_id)
        if not device_type_cls:
            # No device type, store as-is
            if '_saved_values' not in self.common_options:
                self.common_options['_saved_values'] = {}
            self.common_options['_saved_values'].update(values)
            return
        
        # Identify password fields from CommonOptions schema
        password_fields = set()
        for section in device_type_cls.CommonOptions.get('sections', []):
            for option in section.get('options', []):
                if option.get('type') == 'password':
                    password_fields.add(option['optionId'])
        
        # Encrypt password fields
        if '_saved_values' not in self.common_options:
            self.common_options['_saved_values'] = {}
        
        for key, value in values.items():
            if key in password_fields and value:
                self.common_options['_saved_values'][key] = encrypt_password(value)
            else:
                self.common_options['_saved_values'][key] = value


class Device(models.Model):
    mac_address = models.CharField(max_length=17, unique=True, validators=[mac_validator])
    description = models.CharField(max_length=255, blank=True)
    device_type_id = models.CharField(max_length=128)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="devices")
    line_1 = models.ForeignKey(Line, on_delete=models.PROTECT, related_name="primary_devices")
    lines = models.ManyToManyField(Line, related_name="devices", blank=True)
    device_specific_configuration = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    last_provisioned_at = models.DateTimeField(null=True, blank=True, help_text="Last time device configuration was requested")

    class Meta:
        ordering = ["mac_address"]
        constraints = [
            UniqueConstraint(Lower("mac_address"), name="unique_mac_address_ci"),
        ]

    def clean(self) -> None:
        if not self.mac_address:
            raise ValidationError("MAC address required")
        # Normalize and validate format
        self.mac_address = normalize_mac(self.mac_address)
        mac_validator(self.mac_address)

    def __str__(self) -> str:
        return self.mac_address

    def save(self, *args, **kwargs):
        self.mac_address = normalize_mac(self.mac_address)
        super().save(*args, **kwargs)
    
    def get_decrypted_device_config(self):
        """Get device-specific configuration with passwords decrypted.

        Returns dict with password fields decrypted for use in rendering.
        Merges DeviceTypeConfig common options (type-level defaults) with device-specific overrides.
        """
        # Import here to avoid circular dependency
        from provisioning.registry import get_device_type

        device_type_cls = get_device_type(self.device_type_id)

        # Start with common options from DeviceTypeConfig (type-level configuration)
        merged_config = {}
        try:
            device_type_config = DeviceTypeConfig.objects.get(type_id=self.device_type_id)
            merged_config = device_type_config.get_decrypted_saved_values()
        except DeviceTypeConfig.DoesNotExist:
            pass

        # If no device type class found, return merged config as-is
        if not device_type_cls:
            if self.device_specific_configuration:
                merged_config.update(self.device_specific_configuration)
            return merged_config

        # Identify password fields from DeviceSpecificOptions schema
        password_fields = set()
        device_specific_options = device_type_cls.DeviceSpecificOptions or {}
        for section in device_specific_options.get('sections', []):
            for option in section.get('options', []):
                if option.get('type') == 'password':
                    password_fields.add(option['optionId'])

        # Decrypt password fields from device-specific configuration and merge
        if self.device_specific_configuration:
            for key, value in self.device_specific_configuration.items():
                if key in password_fields and value:
                    merged_config[key] = decrypt_password(value)
                else:
                    merged_config[key] = value

        return merged_config
    
    def set_encrypted_device_config(self, values: dict):
        """Set device-specific configuration with passwords encrypted.
        
        Args:
            values: Dict of plaintext values from API/frontend
        """
        # Import here to avoid circular dependency
        from provisioning.registry import get_device_type
        
        device_type_cls = get_device_type(self.device_type_id)
        if not device_type_cls:
            # No device type, store as-is
            self.device_specific_configuration = values
            return
        
        # Identify password fields from DeviceSpecificOptions schema
        password_fields = set()
        device_specific_options = device_type_cls.DeviceSpecificOptions or {}
        for section in device_specific_options.get('sections', []):
            for option in section.get('options', []):
                if option.get('type') == 'password':
                    password_fields.add(option['optionId'])
        
        # Encrypt password fields
        encrypted_config = {}
        for key, value in values.items():
            if key in password_fields and value:
                encrypted_config[key] = encrypt_password(value)
            else:
                encrypted_config[key] = value
        
        self.device_specific_configuration = encrypted_config
