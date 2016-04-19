# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0019_emailnotification_disabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileUplodItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=255)),
                ('item', models.FileField(upload_to=b'')),
            ],
        ),
    ]
