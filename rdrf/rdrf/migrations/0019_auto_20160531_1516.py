# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0018_auto_20160223_1709'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commondataelement',
            name='max_value',
            field=models.DecimalField(help_text='Only used for numeric fields', null=True,
                                      max_digits=10, decimal_places=2, blank=True),
        ),
        migrations.AlterField(
            model_name='commondataelement',
            name='min_value',
            field=models.DecimalField(help_text='Only used for numeric fields', null=True,
                                      max_digits=10, decimal_places=2, blank=True),
        ),
    ]
