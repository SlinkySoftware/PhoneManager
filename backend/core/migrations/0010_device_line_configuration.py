# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_add_device_defaults_to_devicetypeconfig"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="line_configuration",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
