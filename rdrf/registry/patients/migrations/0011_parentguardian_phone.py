# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0010_auto_20151026_1246'),
    ]

    operations = [
        migrations.AddField(
            model_name='parentguardian',
            name='phone',
            field=models.CharField(max_length=20, blank=True),
        ),
    ]
