# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0004_auto_20160401_1115'),
    ]

    operations = [
        migrations.AddField(
            model_name='query',
            name='max_items',
            field=models.IntegerField(default=3),
        ),
    ]
