# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0006_auto_20160208_1606'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser', name='registry', field=models.ManyToManyField(
                related_name='registry', to='rdrf.Registry', blank=True), ), migrations.AlterField(
            model_name='customuser', name='title', field=models.CharField(
                max_length=50, null=True, verbose_name='position', blank=True), ), migrations.AlterField(
            model_name='customuser', name='working_groups', field=models.ManyToManyField(
                related_name='working_groups', to='groups.WorkingGroup', blank=True), ), ]
