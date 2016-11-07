# -*- coding: utf-8 -*-


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0029_auto_20160604_2245'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='consentquestion',
            unique_together=set([('section', 'code')]),
        ),
    ]
