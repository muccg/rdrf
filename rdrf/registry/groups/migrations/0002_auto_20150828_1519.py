# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0001_initial'),
        ('auth', '0006_require_contenttypes_0002'),
        ('rdrf', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='workinggroup',
            name='registry',
            field=models.ForeignKey(
                to='rdrf.Registry',
                null=True,
                on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='customuser',
            name='groups',
            field=models.ManyToManyField(
                related_query_name='user',
                related_name='user_set',
                to='auth.Group',
                blank=True,
                help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
                verbose_name='groups'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='registry',
            field=models.ManyToManyField(
                related_name='registry',
                to='rdrf.Registry'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='user_permissions',
            field=models.ManyToManyField(
                related_query_name='user',
                related_name='user_set',
                to='auth.Permission',
                blank=True,
                help_text='Specific permissions for this user.',
                verbose_name='user permissions'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='working_groups',
            field=models.ManyToManyField(
                related_name='working_groups',
                null=True,
                to='groups.WorkingGroup'),
        ),
    ]
