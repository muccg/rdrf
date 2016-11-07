# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0005_auto_20151105_1417'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(max_length=2, choices=[('ar', 'Arabic'), ('en', 'English')]),
        ),
    ]
