# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

from django.db import migrations, models


def backfill_auth_source(apps, schema_editor):
    user_profile = apps.get_model("core", "UserProfile")
    user_profile.objects.filter(is_sso=True).update(auth_source="saml")
    user_profile.objects.filter(is_sso=False).update(auth_source="local")


def reverse_auth_source(apps, schema_editor):
    user_profile = apps.get_model("core", "UserProfile")
    user_profile.objects.filter(auth_source="saml").update(is_sso=True)
    user_profile.objects.exclude(auth_source="saml").update(is_sso=False)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_device_line_configuration"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="auth_source",
            field=models.CharField(
                choices=[("local", "Local"), ("saml", "SAML"), ("ldap", "LDAP")],
                default="local",
                help_text="Authentication source for this user account",
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_auth_source, reverse_auth_source),
    ]