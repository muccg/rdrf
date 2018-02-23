# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0002_query_registry'),
    ]

    operations = [
        migrations.AlterField(
            model_name='query', name='mongo_search_type', field=models.CharField(
                default='C', max_length=1, choices=[
                    ('C', 'Current'), ('L', 'Longitudinal')]), ), ]
