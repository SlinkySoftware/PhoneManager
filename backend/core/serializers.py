"""Serializers for core models."""
from rest_framework import serializers

from .models import Device, DeviceTypeConfig, Line, SIPServer, Site


class SIPServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SIPServer
        fields = "__all__"


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = "__all__"


class LineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Line
        fields = "__all__"


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = "__all__"


class DeviceTypeConfigSerializer(serializers.ModelSerializer):
    """
    Serializer for device type configuration.
    
    Handles both the schema (common_options) and user-saved values.
    The 'saved_values' field stores the actual option values entered by users.
    """
    saved_values = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = DeviceTypeConfig
        fields = ["type_id", "common_options", "saved_values"]

    def to_representation(self, instance):
        """Include saved_values in the response."""
        data = super().to_representation(instance)
        # Extract saved values from the model if stored
        data['saved_values'] = instance.common_options.get('_saved_values', {})
        return data

    def create(self, validated_data):
        """Create or update device type configuration."""
        saved_values = validated_data.pop('saved_values', {})
        instance = super().create(validated_data)
        
        # Store saved values within common_options
        if saved_values:
            instance.common_options['_saved_values'] = saved_values
            instance.save()
        
        return instance

    def update(self, instance, validated_data):
        """Update device type configuration and save user values."""
        saved_values = validated_data.pop('saved_values', {})
        instance = super().update(instance, validated_data)
        
        # Store saved values within common_options
        if saved_values:
            instance.common_options['_saved_values'] = saved_values
            instance.save()
        
        return instance

