# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-05-21 10:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0070_auto_20180521_1047'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registryform',
            name='name',
            field=models.CharField(help_text='Internal name used by system: Alphanumeric, no spaces', max_length=80),
        ),
    ]
