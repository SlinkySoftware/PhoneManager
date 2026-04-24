# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Serializers for core models."""
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import serializers

from provisioning.registry import get_device_type

from .models import Device, DeviceTypeConfig, DialPlan, DialPlanRule, Line, SIPServer, Site, UserProfile, mac_validator, normalize_mac
from .dialplan_utils import validate_dial_plan_rule


class DialPlanRuleSerializer(serializers.ModelSerializer):
    """Serializer for individual dial plan rules."""
    class Meta:
        model = DialPlanRule
        fields = ["id", "input_regex", "output_regex", "sequence_order"]
    
    def validate(self, attrs):
        """Validate input and output regex patterns."""
        input_pattern = attrs.get("input_regex", "")
        output_pattern = attrs.get("output_regex", "")
        
        is_valid, error_msg = validate_dial_plan_rule(input_pattern, output_pattern)
        if not is_valid:
            raise serializers.ValidationError({
                "detail": error_msg
            })
        
        return attrs


class DialPlanSerializer(serializers.ModelSerializer):
    """Serializer for dial plans with nested rules."""
    rules = DialPlanRuleSerializer(many=True, read_only=False, required=False)
    site_count = serializers.SerializerMethodField()
    rules_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DialPlan
        fields = ["id", "name", "description", "created_at", "updated_at", "rules", "site_count", "rules_count"]
        read_only_fields = ["created_at", "updated_at"]
    
    def get_site_count(self, obj):
        """Return number of sites using this dial plan."""
        return obj.sites.count()
    
    def get_rules_count(self, obj):
        """Return number of rules in this dial plan."""
        return obj.rules.count()
    
    def create(self, validated_data):
        """Create dial plan with nested rules."""
        rules_data = validated_data.pop("rules", [])
        dial_plan = DialPlan.objects.create(**validated_data)
        
        # Create rules in sequence order, filtering out blank rules
        seq_order = 1
        for rule_data in rules_data:
            # Skip blank rules (missing input or output pattern)
            if not rule_data.get("input_regex") or not rule_data.get("output_regex"):
                continue
            rule_data["sequence_order"] = seq_order
            DialPlanRule.objects.create(dial_plan=dial_plan, **rule_data)
            seq_order += 1
        
        return dial_plan
    
    def update(self, instance, validated_data):
        """Update dial plan and its rules."""
        rules_data = validated_data.pop("rules", None)
        
        # Update dial plan fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update rules if provided
        if rules_data is not None:
            # Delete existing rules and recreate
            instance.rules.all().delete()
            seq_order = 1
            for rule_data in rules_data:
                # Skip blank rules (missing input or output pattern)
                if not rule_data.get("input_regex") or not rule_data.get("output_regex"):
                    continue
                rule_data["sequence_order"] = seq_order
                DialPlanRule.objects.create(dial_plan=instance, **rule_data)
                seq_order += 1
        
        return instance


class SIPServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SIPServer
        fields = "__all__"


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ["id", "name", "primary_sip_server", "secondary_sip_server", "timezone", "primary_ntp_ip", "secondary_ntp_ip", "dial_plan"]
        extra_kwargs = {
            "primary_ntp_ip": {"allow_blank": True, "allow_null": True, "required": False},
            "secondary_ntp_ip": {"allow_blank": True, "allow_null": True, "required": False},
            "dial_plan": {"allow_null": True, "required": False},
        }

    def validate(self, attrs):
        # Normalize empty IP strings to None so optional NTP fields stay truly optional
        for field in ("primary_ntp_ip", "secondary_ntp_ip"):
            if attrs.get(field) == "":
                attrs[field] = None
        return super().validate(attrs)


class LineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Line
        fields = "__all__"
        extra_kwargs = {
            'registration_password': {'required': False, 'allow_blank': True}
        }
    
    def update(self, instance, validated_data):
        """Only update password if provided."""
        # If password is empty string or not provided, keep existing password
        if 'registration_password' in validated_data:
            password = validated_data.get('registration_password', '').strip()
            if not password:
                validated_data.pop('registration_password')
        
        return super().update(instance, validated_data)


class DeviceSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="description", required=False, allow_blank=True)
    line_directory_numbers = serializers.SerializerMethodField(read_only=True)
    clone_source_device_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "description",
            "mac_address",
            "device_type_id",
            "site",
            "line_1",
            "lines",
            "line_configuration",
            "device_specific_configuration",
            "enabled",
            "last_provisioned_at",
            "last_requested_ip_address",
            "line_directory_numbers",
            "clone_source_device_id",
        ]

    def get_line_directory_numbers(self, obj):
        return [line.directory_number for line in obj.get_ordered_lines()]

    def validate_mac_address(self, value):
        normalized = normalize_mac(value)
        mac_validator(normalized)

        qs = Device.objects.all()
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.filter(mac_address__iexact=normalized).exists():
            raise serializers.ValidationError("MAC address must be globally unique")
        return normalized

    def _get_max_lines(self, device_type_id: str) -> int:
        device_type_cls = get_device_type(device_type_id)
        if not device_type_cls:
            raise serializers.ValidationError({"device_type_id": "Unknown device type"})
        if device_type_cls.NumberOfLines < 1:
            raise serializers.ValidationError({"device_type_id": "Device type must support at least one line"})
        return device_type_cls.NumberOfLines

    def _allowed_option_ids(self, device_type_id: str) -> set:
        device_type_cls = get_device_type(device_type_id)
        if not device_type_cls:
            return set()
        sections = device_type_cls.DeviceSpecificOptions.get("sections", [])
        option_ids = set()
        for section in sections:
            for option in section.get("options", []):
                if option_id := option.get("optionId"):
                    option_ids.add(option_id)
        return option_ids

    def _password_option_ids(self, device_type_id: str) -> set:
        device_type_cls = get_device_type(device_type_id)
        if not device_type_cls:
            return set()

        password_fields = set()
        sections = device_type_cls.DeviceSpecificOptions.get("sections", [])
        for section in sections:
            for option in section.get("options", []):
                if option.get("type") == "password" and option.get("optionId"):
                    password_fields.add(option["optionId"])
        return password_fields

    def _merge_device_default_passwords(self, validated_data):
        device_type_id = validated_data.get("device_type_id")
        if not device_type_id:
            return

        password_fields = self._password_option_ids(device_type_id)
        if not password_fields:
            return

        try:
            device_type_config = DeviceTypeConfig.objects.get(type_id=device_type_id)
        except DeviceTypeConfig.DoesNotExist:
            return

        default_config = device_type_config.get_decrypted_device_defaults()
        incoming_config = validated_data.setdefault("device_specific_configuration", {})

        for field in password_fields:
            if incoming_config.get(field):
                continue
            default_value = default_config.get(field)
            if default_value:
                incoming_config[field] = default_value

    def _merge_clone_passwords(self, validated_data, clone_source_device_id):
        if not clone_source_device_id:
            return

        source_device = Device.objects.filter(pk=clone_source_device_id).first()
        if not source_device:
            raise serializers.ValidationError({"clone_source_device_id": "Source device not found"})

        device_type_id = validated_data.get("device_type_id")
        password_fields = self._password_option_ids(device_type_id)
        if not password_fields:
            return

        source_config = source_device.get_decrypted_device_config()
        incoming_config = validated_data.setdefault("device_specific_configuration", {})

        for field in password_fields:
            if incoming_config.get(field):
                continue
            source_value = source_config.get(field)
            if source_value:
                incoming_config[field] = source_value

    def _masked_device_config(self, instance):
        config = instance.get_decrypted_device_config()
        if not config:
            return {}

        masked_config = dict(config)
        for field in self._password_option_ids(instance.device_type_id):
            masked_config.pop(field, None)
        return masked_config

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        device_type_id = attrs.get("device_type_id") or (instance.device_type_id if instance else None)
        device_type_cls = get_device_type(device_type_id)
        max_lines = self._get_max_lines(device_type_id)

        # Line 1 is required
        line_1 = attrs.get("line_1", instance.line_1 if instance else None)
        if not line_1:
            raise serializers.ValidationError({"line_1": "Line 1 is required"})

        # Clean up line assignments and enforce maximum
        line_ids = []
        line_objects = {}
        line_1_id = line_1.id if isinstance(line_1, Line) else line_1
        line_ids.append(line_1_id)
        if isinstance(line_1, Line):
            line_objects[line_1_id] = line_1

        provided_lines = attrs.get("lines", None)
        if provided_lines is not None:
            cleaned_lines = []
            seen_ids = set()
            for line in provided_lines:
                line_id = line.id if isinstance(line, Line) else line
                if line_id is None:
                    continue
                if line_id == line_1_id:
                    continue
                if line_id in seen_ids:
                    continue
                cleaned_lines.append(line)
                seen_ids.add(line_id)
                line_ids.append(line_id)
                if isinstance(line, Line):
                    line_objects[line_id] = line
            if len(cleaned_lines) > max_lines - 1:
                cleaned_lines = cleaned_lines[: max_lines - 1]
            attrs["lines"] = cleaned_lines
        elif instance:
            # Trim existing lines if type changed or exceeds max.
            existing = list(instance.get_ordered_lines()[1:])
            if len(existing) > max_lines - 1:
                attrs["lines"] = existing[: max_lines - 1]

        line_ids = [line_1_id]
        final_lines = attrs.get("lines", None)
        if final_lines is None and instance:
            final_lines = list(instance.get_ordered_lines()[1:])

        for line in final_lines or []:
            line_id = line.id if isinstance(line, Line) else line
            if line_id is None:
                continue
            line_ids.append(line_id)
            if isinstance(line, Line):
                line_objects[line_id] = line

        line_order_ids = [line_id for line_id in line_ids if line_id != line_1_id]

        # Enforce non-shared line exclusivity across devices
        for db_line in Line.objects.filter(id__in=line_ids):
            line_objects.setdefault(db_line.id, db_line)
            if db_line.is_shared:
                continue
            conflict = Device.objects.filter(Q(line_1=db_line.id) | Q(lines__id=db_line.id))
            if instance:
                conflict = conflict.exclude(pk=instance.pk)
            if conflict.exists():
                raise serializers.ValidationError(
                    {
                        "lines": f"Line {db_line.name} ({db_line.directory_number}) is already assigned to another device",
                    }
                )

        # Validate dedicated line-level configuration schema
        supports_per_line_sip = bool(getattr(device_type_cls, "SupportsSIPServersPerLine", False)) if device_type_cls else False
        raw_line_config = attrs.get("line_configuration", instance.line_configuration if instance else {})

        if not supports_per_line_sip:
            attrs["line_configuration"] = {}
            if line_order_ids:
                attrs["line_configuration"][Device.LINE_ORDER_KEY] = line_order_ids
        else:
            if raw_line_config is None:
                raw_line_config = {}
            if not isinstance(raw_line_config, dict):
                raise serializers.ValidationError({"line_configuration": "Line configuration must be an object"})

            raw_line_config = {
                key: value
                for key, value in raw_line_config.items()
                if key != Device.LINE_ORDER_KEY
            }

            cleaned_line_config = {}
            sip_server_cache = {}

            def _get_sip_server(server_id):
                if server_id not in sip_server_cache:
                    sip_server_cache[server_id] = SIPServer.objects.filter(pk=server_id).first()
                return sip_server_cache[server_id]

            for line_key, line_cfg in raw_line_config.items():
                try:
                    line_number = int(line_key)
                except (TypeError, ValueError):
                    raise serializers.ValidationError({"line_configuration": f"Invalid line number key: {line_key}"})

                if line_number < 2 or line_number > max_lines:
                    raise serializers.ValidationError(
                        {"line_configuration": f"Line configuration is only valid for lines 2 through {max_lines}"}
                    )

                if not isinstance(line_cfg, dict):
                    raise serializers.ValidationError({"line_configuration": f"Line {line_number} configuration must be an object"})

                use_different = bool(line_cfg.get("use_different_sip_server", False))
                if not use_different:
                    continue

                primary_id = line_cfg.get("primary_sip_server")
                secondary_id = line_cfg.get("secondary_sip_server")

                if not primary_id:
                    raise serializers.ValidationError(
                        {"line_configuration": f"Line {line_number} requires a primary SIP server when override is enabled"}
                    )

                primary_server = _get_sip_server(primary_id)
                if not primary_server:
                    raise serializers.ValidationError({"line_configuration": f"Line {line_number} primary SIP server is invalid"})

                cleaned_entry = {
                    "use_different_sip_server": True,
                    "primary_sip_server": primary_server.id,
                }

                if secondary_id:
                    if secondary_id == primary_server.id:
                        raise serializers.ValidationError(
                            {"line_configuration": f"Line {line_number} primary and backup SIP server must be different"}
                        )

                    secondary_server = _get_sip_server(secondary_id)
                    if not secondary_server:
                        raise serializers.ValidationError(
                            {"line_configuration": f"Line {line_number} backup SIP server is invalid"}
                        )
                    cleaned_entry["secondary_sip_server"] = secondary_server.id

                cleaned_line_config[str(line_number)] = cleaned_entry

            if line_order_ids:
                cleaned_line_config[Device.LINE_ORDER_KEY] = line_order_ids

            attrs["line_configuration"] = cleaned_line_config

        # Preserve overlapping device-specific configuration keys on type change
        allowed_keys = self._allowed_option_ids(device_type_id)
        incoming_config = attrs.get("device_specific_configuration")
        existing_config = instance.device_specific_configuration if instance else {}
        merged_config = {}

        if incoming_config is not None:
            # Keep only allowed keys from incoming
            merged_config = {k: v for k, v in incoming_config.items() if k in allowed_keys}
            # Preserve existing values for matching keys not supplied
            if instance and device_type_id != instance.device_type_id:
                for key in allowed_keys:
                    if key not in merged_config and key in existing_config:
                        merged_config[key] = existing_config[key]
        else:
            merged_config = {k: v for k, v in existing_config.items() if k in allowed_keys}

        attrs["device_specific_configuration"] = merged_config

        return super().validate(attrs)

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        clone_source_device_id = validated_data.pop("clone_source_device_id", None)

        self._merge_clone_passwords(validated_data, clone_source_device_id)
        self._merge_device_default_passwords(validated_data)
        
        # Encrypt device-specific configuration passwords
        if 'device_specific_configuration' in validated_data:
            device = Device(
                mac_address=validated_data['mac_address'],
                device_type_id=validated_data['device_type_id']
            )
            device.set_encrypted_device_config(validated_data['device_specific_configuration'])
            validated_data['device_specific_configuration'] = device.device_specific_configuration
        
        device = super().create(validated_data)
        if lines:
            device.lines.set(lines)
        return device

    def update(self, instance, validated_data):
        """Update device, preserving password fields that weren't changed."""
        lines = validated_data.pop("lines", None)
        validated_data.pop("clone_source_device_id", None)
        
        # Handle password fields in device_specific_configuration
        if 'device_specific_configuration' in validated_data:
            incoming_config = validated_data['device_specific_configuration']
            
            # Get decrypted existing config for comparison
            existing_config_decrypted = instance.get_decrypted_device_config()

            # Get device type to identify password fields
            device_type_id = validated_data.get('device_type_id', instance.device_type_id)
            password_fields = self._password_option_ids(device_type_id)

            # Preserve existing password values if not provided in update
            for field in password_fields:
                if field not in incoming_config or not incoming_config.get(field):
                    if field in existing_config_decrypted:
                        incoming_config[field] = existing_config_decrypted[field]
            
            # Encrypt the passwords in the incoming config
            instance.set_encrypted_device_config(incoming_config)
            validated_data['device_specific_configuration'] = instance.device_specific_configuration
        
        device = super().update(instance, validated_data)
        if lines is not None:
            device.lines.set(lines)
        return device
    
    def to_representation(self, instance):
        """Return device config in API responses with password fields omitted."""
        data = super().to_representation(instance)
        data['lines'] = [line.id for line in instance.get_ordered_lines()[1:]]
        if instance.device_specific_configuration:
            data['device_specific_configuration'] = self._masked_device_config(instance)
        return data


class DeviceTypeConfigSerializer(serializers.ModelSerializer):
    """
    Serializer for device type configuration.
    
    Handles both the schema (common_options) and user-saved values.
    The 'saved_values' field stores the actual option values entered by users.
    Passwords are automatically encrypted/decrypted.
    """
    saved_values = serializers.JSONField(required=False, allow_null=True)
    device_defaults = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = DeviceTypeConfig
        fields = ["type_id", "common_options", "saved_values", "device_defaults"]

    def _device_default_password_option_ids(self, instance) -> set:
        device_type_cls = get_device_type(instance.type_id)
        if not device_type_cls:
            return set()

        password_fields = set()
        for section in device_type_cls.DeviceSpecificOptions.get('sections', []):
            for option in section.get('options', []):
                if option.get('type') == 'password' and option.get('optionId'):
                    password_fields.add(option['optionId'])
        return password_fields

    def _masked_device_defaults(self, instance) -> dict:
        defaults = instance.get_decrypted_device_defaults()
        if not defaults:
            return {}

        masked_defaults = dict(defaults)
        for field in self._device_default_password_option_ids(instance):
            masked_defaults.pop(field, None)
        return masked_defaults

    def _device_default_password_fields(self, instance) -> dict:
        encrypted_defaults = instance.device_defaults or {}
        return {
            field: bool(encrypted_defaults.get(field))
            for field in self._device_default_password_option_ids(instance)
        }

    def to_representation(self, instance):
        """Include decrypted saved_values in the response."""
        data = super().to_representation(instance)
        # Return decrypted saved values
        data['saved_values'] = instance.get_decrypted_saved_values()
        data['device_defaults'] = self._masked_device_defaults(instance)
        data['device_default_password_fields'] = self._device_default_password_fields(instance)
        return data

    def create(self, validated_data):
        """Create or update device type configuration."""
        saved_values = validated_data.pop('saved_values', {})
        device_defaults = validated_data.pop('device_defaults', {})
        instance = super().create(validated_data)
        
        # Encrypt and store saved values
        if saved_values:
            instance.set_encrypted_saved_values(saved_values)
            instance.save()

        # Encrypt and store device defaults
        if device_defaults:
            instance.set_encrypted_device_defaults(device_defaults)
            instance.save()
        
        return instance

    def update(self, instance, validated_data):
        """Update device type configuration and save encrypted user values."""
        saved_values = validated_data.pop('saved_values', {})
        device_defaults = validated_data.pop('device_defaults', None)
        
        # Get existing decrypted values
        existing_decrypted = instance.get_decrypted_saved_values()
        existing_defaults = instance.get_decrypted_device_defaults()
        
        # Merge with incoming values (preserve passwords not provided)
        merged_values = {**existing_decrypted, **saved_values}
        merged_defaults = {**existing_defaults, **(device_defaults or {})}
        
        instance = super().update(instance, validated_data)
        
        # Encrypt and store saved values
        if merged_values:
            instance.set_encrypted_saved_values(merged_values)
            instance.save()

        if device_defaults is not None:
            instance.set_encrypted_device_defaults(merged_defaults)
            instance.save()
        
        return instance


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with profile information."""
    
    role = serializers.SerializerMethodField()
    auth_source = serializers.SerializerMethodField()
    auth_type_label = serializers.SerializerMethodField()
    force_password_reset = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_active', 'role', 'auth_source', 'auth_type_label', 'force_password_reset']
        read_only_fields = ['id', 'is_active', 'auth_source', 'auth_type_label', 'full_name']
    
    def get_role(self, obj):
        """Get user role from profile."""
        return obj.profile.role if hasattr(obj, 'profile') else UserProfile.ROLE_READONLY
    
    def get_auth_source(self, obj):
        """Get authentication source from profile."""
        if hasattr(obj, 'profile'):
            return obj.profile.auth_source
        return UserProfile.AUTH_SOURCE_LOCAL

    def get_auth_type_label(self, obj):
        """Get display label for authentication source."""
        if hasattr(obj, 'profile'):
            return obj.profile.get_auth_source_display()
        return 'Local'
    
    def get_force_password_reset(self, obj):
        """Get force password reset flag from profile."""
        return obj.profile.force_password_reset if hasattr(obj, 'profile') else False
    
    def get_full_name(self, obj):
        """Get full name from first_name and last_name."""
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


