# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0012_registryform_header'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(max_length=2, choices=[(b'ar', b'Arabic'),
                                                          (b'de', b'German'), (b'en', b'English'), (b'no', b'Norwegian')]),
        ),
    ]
