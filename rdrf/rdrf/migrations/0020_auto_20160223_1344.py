# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0019_rdrfcontext_context_form_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='contextformgroup',
            name='naming_scheme',
            field=models.CharField(default=b'D', max_length=1, choices=[(b'D', b'Automatic - Date'), (b'N', b'Automatic - Number'), (b'M', b'Manual - Free Text')]),
        ),
        migrations.AlterField(
            model_name='contextformgroup',
            name='registry',
            field=models.ForeignKey(related_name='context_form_groups', to='rdrf.Registry'),
        ),
        migrations.AlterField(
            model_name='contextformgroupitem',
            name='context_form_group',
            field=models.ForeignKey(related_name='items', to='rdrf.ContextFormGroup'),
        ),
        migrations.AlterUniqueTogether(
            name='cdepermittedvalue',
            unique_together=set([('pv_group', 'code')]),
        ),
    ]
