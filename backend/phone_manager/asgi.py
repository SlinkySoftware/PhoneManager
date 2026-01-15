"""ASGI config for Phone Provisioning Manager."""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "phone_manager.settings")
application = get_asgi_application()
