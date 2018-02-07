# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0015_auto_20160711_2209'),
    ]

    operations = [
        migrations.AddField(
            model_name='patientconsent',
            name='filename',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
    ]
