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
router.register(r"device-type-config", core_views.DeviceTypeConfigViewSet, basename="devicetypeconfig")
router.register(r"device-types", provisioning_views.DeviceTypeViewSet, basename="devicetype")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", core_views.login, name="login"),
    path("api/timezones/", core_views.get_timezones, name="timezones"),
    path("api/", include(router.urls)),
    path("provision/", include("provisioning.urls")),
]
