# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""URL routes for localhost-only internal APIs."""

from django.urls import path

from .views import device_context_view, normalize_number_view


urlpatterns = [
    path("device-context/", device_context_view, name="internal-device-context"),
    path("normalize-number/", normalize_number_view, name="internal-normalize-number"),
]