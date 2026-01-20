# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

from django.db import migrations, models
from django.db.models.functions import Lower
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="device",
            name="mac_address",
            field=models.CharField(max_length=17, unique=True, validators=[core.models.mac_validator]),
        ),
        migrations.AddConstraint(
            model_name="device",
            constraint=models.UniqueConstraint(
                Lower("mac_address"), name="unique_mac_address_ci"
            ),
        ),
    ]
