# Generated by Django 2.2.24 on 2021-11-02 14:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('intframework', '0005_auto_20211102_1413'),
    ]

    operations = [
        migrations.AddField(
            model_name='hl7message',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
