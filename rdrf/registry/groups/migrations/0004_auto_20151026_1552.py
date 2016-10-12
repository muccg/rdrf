# -*- coding: utf-8 -*-


from django.db import migrations, models
import django.core.validators
import re


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0003_auto_20150831_1321'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='customuser',
            options={},
        ),
        migrations.AlterField(
            model_name='customuser',
            name='email',
            field=models.EmailField(
                max_length=254,
                verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='first_name',
            field=models.CharField(
                max_length=30,
                verbose_name='first name'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='is_active',
            field=models.BooleanField(
                default=False,
                help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.',
                verbose_name='active'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='last_name',
            field=models.CharField(
                max_length=30,
                verbose_name='last name'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='username',
            field=models.CharField(
                help_text='Required. 254 characters or fewer. Letters, numbers and @/./+/-/_ characters',
                unique=True,
                max_length=254,
                verbose_name='username',
                validators=[
                    django.core.validators.RegexValidator(
                        re.compile('^[\\w.@+-]+$'),
                        'Enter a valid username.',
                        'invalid')]),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='working_groups',
            field=models.ManyToManyField(
                related_name='working_groups',
                to='groups.WorkingGroup'),
        ),
    ]
