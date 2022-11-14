# Generated by Django 3.2.15 on 2022-11-14 09:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboards', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='visualisationconfig',
            name='dashboard',
            field=models.CharField(choices=[('S', 'Single Patient'), ('A', 'All Patients')], default='A', max_length=1),
            preserve_default=False,
        ),
    ]