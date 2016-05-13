# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import rdrf.models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0019_auto_20160531_1516'),
    ]

    operations = [
        migrations.CreateModel(
            name='CDEFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('item', models.FileField(upload_to=rdrf.models.file_upload_to, max_length=300)),
                ('filename', models.CharField(max_length=255)),
                ('cde', models.ForeignKey(to='rdrf.CommonDataElement')),
                ('form', models.ForeignKey(blank=True, to='rdrf.RegistryForm', null=True)),
                ('registry', models.ForeignKey(to='rdrf.Registry')),
                ('section', models.ForeignKey(blank=True, to='rdrf.Section', null=True)),
            ],
        ),
    ]
