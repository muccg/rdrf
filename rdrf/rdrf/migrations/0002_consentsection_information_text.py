# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='consentsection',
            name='information_text',
            field=models.TextField(null=True, blank=True),
        ),
    ]
