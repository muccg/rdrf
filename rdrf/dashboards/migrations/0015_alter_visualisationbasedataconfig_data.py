# Generated by Django 3.2.15 on 2023-03-07 13:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboards', '0014_alter_visualisationconfig_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visualisationbasedataconfig',
            name='data',
            field=models.JSONField(default='{}'),
        ),
    ]