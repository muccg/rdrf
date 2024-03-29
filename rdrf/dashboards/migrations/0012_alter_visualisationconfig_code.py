# Generated by Django 3.2.15 on 2023-01-23 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboards', '0011_visualisationbasedataconfig_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visualisationconfig',
            name='code',
            field=models.CharField(choices=[('tofc', 'Types of Forms Completed'), ('pcf', 'Patients Who Completed Forms'), ('cfc', 'Combined Field Comparison'), ('cpr', 'Changes in Patient Responses'), ('sgc', 'Scale Group Comparison'), ('tl', 'Traffic Lights Display')], max_length=80),
        ),
    ]
