# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        ('rdrf', '0002_consentsection_information_text'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailNotification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=100)),
                ('recipient', models.EmailField(max_length=254, null=True, blank=True)),
                ('subject', models.CharField(max_length=50)),
                ('body', models.TextField()),
                ('group_recipient', models.ForeignKey(blank=True, to='auth.Group', null=True,
                                                      on_delete=models.SET_NULL)),
                ('registry', models.ForeignKey(to='rdrf.Registry',
                                                on_delete=models.CASCADE)),
            ],
        ),
    ]
