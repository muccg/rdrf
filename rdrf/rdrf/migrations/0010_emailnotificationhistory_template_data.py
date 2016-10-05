# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0009_emailnotificationhistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailnotificationhistory',
            name='template_data',
            field=models.TextField(null=True, blank=True),
        ),
    ]
