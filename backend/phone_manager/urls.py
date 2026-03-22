# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""URL configuration for Phone Provisioning Manager."""
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from core import views as core_views
from provisioning import views as provisioning_views

router = routers.DefaultRouter()
router.register(r"devices", core_views.DeviceViewSet, basename="device")
router.register(r"lines", core_views.LineViewSet, basename="line")
router.register(r"sites", core_views.SiteViewSet, basename="site")
router.register(r"sip-servers", core_views.SIPServerViewSet, basename="sipserver")
router.register(r"dial-plans", core_views.DialPlanViewSet, basename="dialplan")
router.register(r"device-type-config", core_views.DeviceTypeConfigViewSet, basename="devicetypeconfig")
router.register(r"device-types", provisioning_views.DeviceTypeViewSet, basename="devicetype")
router.register(r"users", core_views.UserViewSet, basename="user")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", core_views.login, name="login"),
    path("api/auth/ldap/login/", core_views.ldap_login, name="ldap_login"),
    path("api/auth/config/", core_views.auth_config, name="auth_config"),
    path("api/auth/change-password/", core_views.change_password, name="change_password"),
    path("api/auth/saml/login/", core_views.saml_login, name="saml_login"),
    path("api/auth/saml/acs/", core_views.saml_acs, name="saml_acs"),
    path("api/auth/saml/metadata/", core_views.saml_metadata, name="saml_metadata"),
    path("api/timezones/", core_views.get_timezones, name="timezones"),
    path("api/", include(router.urls)),
    path("provision/", include("provisioning.urls")),
]
