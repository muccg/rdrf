# Generated by Django 2.1.15 on 2020-07-27 16:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0134_remove_customactionexecution_custom_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='customaction',
            name='include_all',
            field=models.BooleanField(default=False, help_text='For Patient Status Report: Select this to include all data for the patients.<br>If this is not selected, then the Data field below should be filled in with the required report spec.<br>If this is selected, Data field should contain {}.'),
        ),
    ]
