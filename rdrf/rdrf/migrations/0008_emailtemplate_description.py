# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0007_auto_20151105_1603'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailtemplate',
            name='description',
            field=models.TextField(default='Template description'),
            preserve_default=False,
        ),
    ]
