# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0012_auto_20160530_1356'),
    ]

    operations = [
        migrations.AlterField(
            model_name='addresstype',
            name='type',
            field=models.CharField(unique=True, max_length=100),
        ),
    ]
