# Generated by Django 2.2.20 on 2021-07-22 10:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0137_auto_20201021_1419'),
    ]

    operations = [
        migrations.AddField(
            model_name='survey',
            name='client_rep_json',
            field=models.TextField(blank=True, null=True),
        ),
    ]