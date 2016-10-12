# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.utils.timezone
import django.core.validators
import django.contrib.auth.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id',
                 models.AutoField(
                     verbose_name='ID',
                     serialize=False,
                     auto_created=True,
                     primary_key=True)),
                ('password',
                 models.CharField(
                     max_length=128,
                     verbose_name='password')),
                ('last_login',
                 models.DateTimeField(
                     verbose_name='last login',
                     blank=True)),
                ('is_superuser',
                 models.BooleanField(
                     default=False,
                     help_text='Designates that this user has all permissions without explicitly assigning them.',
                     verbose_name='superuser status')),
                ('username',
                 models.CharField(
                     error_messages={
                         'unique': 'A user with that username already exists.'},
                     max_length=30,
                     validators=[
                         django.core.validators.RegexValidator(
                             '^[\\w.@+-]+$',
                             'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.',
                             'invalid')],
                     help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.',
                     unique=True,
                     verbose_name='username')),
                ('first_name',
                 models.CharField(
                     max_length=30,
                     verbose_name='first name',
                     blank=True)),
                ('last_name',
                 models.CharField(
                     max_length=30,
                     verbose_name='last name',
                     blank=True)),
                ('email',
                 models.EmailField(
                     max_length=254,
                     verbose_name='email address',
                     blank=True)),
                ('is_staff',
                 models.BooleanField(
                     default=False,
                     help_text='Designates whether the user can log into this admin site.',
                     verbose_name='staff status')),
                ('is_active',
                 models.BooleanField(
                     default=True,
                     help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.',
                     verbose_name='active')),
                ('date_joined',
                 models.DateTimeField(
                     default=django.utils.timezone.now,
                     verbose_name='date joined')),
                ('title',
                 models.CharField(
                     max_length=50,
                     null=True,
                     verbose_name='position')),
            ],
            options={
                'abstract': False,
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            managers=[
                ('objects',
                 django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='WorkingGroup',
            fields=[
                ('id',
                 models.AutoField(
                     verbose_name='ID',
                     serialize=False,
                     auto_created=True,
                     primary_key=True)),
                ('name',
                 models.CharField(
                     max_length=100)),
            ],
            options={
                'ordering': ['registry__code'],
            },
        ),
    ]
