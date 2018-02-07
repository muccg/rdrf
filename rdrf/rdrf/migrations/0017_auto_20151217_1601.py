# -*- coding: utf-8 -*-

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0016_auto_20151217_1339'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mongomigrationdummymodel',
            name='version',
            field=models.CharField(
                max_length=80,
                choices=[
                    ('initial',
                     'initial'),
                    ('testing',
                     'testing'),
                    ('1.0.17',
                     'populate context_id on all patient records')]),
        ),
    ]
