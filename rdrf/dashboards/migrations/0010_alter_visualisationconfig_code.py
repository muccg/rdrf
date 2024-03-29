# Generated by Django 3.2.15 on 2022-12-02 13:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboards', '0009_visualisationconfig_position'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visualisationconfig',
            name='code',
            field=models.CharField(choices=[('tofc', 'Types of Forms Completed'), ('pcf', 'Patients Who Completed Forms'), ('cfc', 'Combined Field Comparison'), ('cpr', 'Changes in Patient Responses'), ('sgc', 'Scale Group Comparison')], max_length=80),
        ),
    ]
