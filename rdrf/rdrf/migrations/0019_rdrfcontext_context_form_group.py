# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0018_contextformgroup_contextformgroupitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='rdrfcontext',
            name='context_form_group',
            field=models.ForeignKey(blank=True, to='rdrf.ContextFormGroup', null=True),
        ),
    ]
