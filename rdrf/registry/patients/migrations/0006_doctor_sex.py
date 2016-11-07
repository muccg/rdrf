# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0005_auto_20150915_1518'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctor',
            name='sex',
            field=models.CharField(blank=True, max_length=1, null=True, choices=[
                                   ('1', 'Male'), ('2', 'Female'), ('3', 'Indeterminate')]),
        ),
    ]
