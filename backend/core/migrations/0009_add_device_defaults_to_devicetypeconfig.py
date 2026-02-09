# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_dialplan_site_dial_plan_dialplanrule"),
    ]

    operations = [
        migrations.AddField(
            model_name="devicetypeconfig",
            name="device_defaults",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
