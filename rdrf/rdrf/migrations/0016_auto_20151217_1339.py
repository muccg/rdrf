# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def forwards_func(apps, schema_editor):
    pass


def backwards_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0015_mongomigrationdummymodel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mongomigrationdummymodel',
            name='version',
            field=models.CharField(max_length=80, choices=[(b'initial', b'initial'), (b'testing', b'testing')]),
        ),
        migrations.RunPython(forwards_func, backwards_func),
    ]

