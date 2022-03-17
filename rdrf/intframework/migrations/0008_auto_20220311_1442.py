# Generated by Django 2.2.26 on 2022-03-11 14:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('intframework', '0007_hl7messageconfig'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hl7messagefieldupdate',
            name='update_status',
            field=models.CharField(choices=[('Success', 'Success'), ('Failure', 'Failure'), ('Empty', 'Empty')], default='Failure', max_length=10),
        ),
    ]
