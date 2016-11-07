# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0011_auto_20151109_1238'),
    ]

    operations = [
        migrations.AddField(
            model_name='registryform',
            name='header',
            field=models.TextField(blank=True),
        ),
    ]
