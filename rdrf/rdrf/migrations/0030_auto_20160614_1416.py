# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0029_auto_20160604_2245'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='consentquestion',
            unique_together=set([('section', 'code')]),
        ),
    ]
