# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0004_auto_20151026_1552'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='password_change_date',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
