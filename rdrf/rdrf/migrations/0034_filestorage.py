# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0033_auto_20160823_1343'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileStorage',
            fields=[
                ('name', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('data', models.BinaryField()),
                ('size', models.IntegerField(default=0)),
            ],
        ),
    ]
