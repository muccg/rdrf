# -*- coding: utf-8 -*-


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0017_auto_20151217_1601'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='cdepermittedvalue',
            unique_together=set([('pv_group', 'code')]),
        ),
    ]
