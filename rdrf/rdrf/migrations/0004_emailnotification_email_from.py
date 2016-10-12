# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0003_emailnotification'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailnotification',
            name='email_from',
            field=models.EmailField(default='no-reply@DOMAIN.COM', max_length=254),
        ),
    ]
