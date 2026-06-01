# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Routing for provisioning endpoints."""
from django.urls import path

from .views import ProvisioningViewSet

provision_view = ProvisioningViewSet.as_view({"get": "retrieve"})
provision_security_asset_view = ProvisioningViewSet.as_view({"get": "security_asset"})

urlpatterns = [
    path("security/<str:asset_name>", provision_security_asset_view, name="provision-security-asset"),
    path("cfg<str:pk>.xml", provision_view, name="provision-device"),
    path("<str:pk>-phone.cfg", provision_view, name="provision-device"),
    path("<str:pk>.cfg", provision_view, name="provision-device"),
    path("<str:pk>", provision_view, name="provision-device"),
]
