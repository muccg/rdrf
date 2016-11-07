# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0004_auto_20150908_1637'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctor',
            name='fax',
            field=models.CharField(max_length=30, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='doctor',
            name='postcode',
            field=models.CharField(max_length=20, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='doctor',
            name='title',
            field=models.CharField(max_length=4, null=True, blank=True),
        ),
    ]
