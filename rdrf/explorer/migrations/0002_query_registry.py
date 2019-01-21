# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0001_initial'),
        ('rdrf', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='query',
            name='registry',
            field=models.ForeignKey(to='rdrf.Registry', on_delete=models.CASCADE),
        ),
    ]
