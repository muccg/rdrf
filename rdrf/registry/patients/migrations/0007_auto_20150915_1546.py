# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0006_doctor_sex'),
    ]

    operations = [
        migrations.AlterField(
            model_name='doctor',
            name='state',
            field=models.ForeignKey(
                on_delete=models.SET_NULL,
                verbose_name='State/Province/Territory',
                blank=True,
                to='patients.State',
                null=True),
        ),
    ]
