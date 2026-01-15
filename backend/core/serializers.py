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
    class Meta:
        model = DeviceTypeConfig
        fields = "__all__"
