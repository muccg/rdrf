# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0032_change_default_notification_from_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate', name='language', field=models.CharField(
                max_length=2, choices=[
                    ('ar', 'Arabic'), ('de', 'German'), ('en', 'English')]), ), ]
