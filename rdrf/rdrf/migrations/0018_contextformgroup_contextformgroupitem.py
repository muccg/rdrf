# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0017_auto_20151217_1601'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContextFormGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('context_type', models.CharField(default=b'F', max_length=1, choices=[(b'F', b'Fixed'), (b'M', b'Multiple')])),
                ('name', models.CharField(max_length=80)),
                ('registry', models.ForeignKey(to='rdrf.Registry')),
            ],
        ),
        migrations.CreateModel(
            name='ContextFormGroupItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('context_form_group', models.ForeignKey(to='rdrf.ContextFormGroup')),
                ('registry_form', models.ForeignKey(to='rdrf.RegistryForm')),
            ],
        ),
    ]
