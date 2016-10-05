# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0019_auto_20160531_1516'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailnotification',
            name='disabled',
            field=models.BooleanField(default=False),
        ),
    ]
