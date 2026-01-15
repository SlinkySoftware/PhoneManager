"""Routing for provisioning endpoints."""
from django.urls import path

from .views import ProvisioningViewSet

provision_view = ProvisioningViewSet.as_view({"get": "retrieve"})

urlpatterns = [
    path("<str:pk>/", provision_view, name="provision-device"),
]
