"""WSGI config for Phone Provisioning Manager."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "phone_manager.settings")
application = get_wsgi_application()
