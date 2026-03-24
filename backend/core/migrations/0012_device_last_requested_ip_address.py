# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_userprofile_auth_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='last_requested_ip_address',
            field=models.GenericIPAddressField(
                blank=True,
                help_text='Last resolved client IP address that requested device configuration',
                null=True,
            ),
        ),
    ]