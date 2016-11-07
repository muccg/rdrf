# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0010_emailnotificationhistory_template_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailnotification',
            name='recipient',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
    ]
