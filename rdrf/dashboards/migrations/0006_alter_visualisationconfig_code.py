# Generated by Django 3.2.15 on 2022-11-15 12:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboards', '0005_alter_visualisationconfig_config'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visualisationconfig',
            name='code',
            field=models.CharField(choices=[('tofc', 'Types of Forms Completed'), ('pcf', 'Patients Who Completed Forms'), ('fgc', 'Field Group Comparison'), ('cpr', 'Changes in Patient Responses')], max_length=80),
        ),
    ]
