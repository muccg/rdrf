# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def move_username(apps, schema_editor):
    CustomUser = apps.get_model("groups", "CustomUser")
    for user in CustomUser.objects.all():
        user.rdrf_username = user.username
        user.save()

class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0004_auto_20151023_1252'),
    ]

    operations = [
        migrations.RunPython(move_username)
    ]
