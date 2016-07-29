# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0030_auto_20160614_1416'),
    ]

    operations = [
        migrations.AddField(
            model_name='contextformgroup',
            name='naming_cde_to_use',
            field=models.CharField(max_length=80, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='contextformgroup',
            name='naming_scheme',
            field=models.CharField(default=b'D', max_length=1, choices=[(b'D', b'Automatic - Date'), (b'N', b'Automatic - Number'), (b'M', b'Manual - Free Text'), (b'C', b'CDE - Nominate CDE to use')]),
        ),
    ]
