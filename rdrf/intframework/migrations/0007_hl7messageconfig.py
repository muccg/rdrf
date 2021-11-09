# Generated by Django 2.2.24 on 2021-11-03 14:09

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('intframework', '0006_hl7message_updated'),
    ]

    operations = [
        migrations.CreateModel(
            name='HL7MessageConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('event_code', models.CharField(default='', max_length=10)),
                ('config', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
            ],
        ),
    ]