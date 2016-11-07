# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0028_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registry',
            name='code',
            field=models.CharField(unique=True, max_length=10),
        ),
        migrations.AlterField(
            model_name='section',
            name='code',
            field=models.CharField(unique=True, max_length=100),
        ),
    ]
