# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0014_rdrfcontext'),
    ]

    operations = [
        migrations.CreateModel(
            name='MongoMigrationDummyModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('version', models.CharField(max_length=80, choices=[(b'initial', b'initial')])),
            ],
        ),
    ]
