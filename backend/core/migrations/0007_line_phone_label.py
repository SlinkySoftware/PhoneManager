# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_encrypt_passwords"),
    ]

    operations = [
        migrations.AddField(
            model_name="line",
            name="phone_label",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Label displayed on device screens",
                max_length=128,
            ),
        ),
    ]
