# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0004_emailnotification_email_from'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('language', models.TextField(choices=[('ar', 'Arabic'), ('en', 'English')])),
                ('subject', models.CharField(max_length=50)),
                ('body', models.TextField()),
            ],
        ),
        migrations.RemoveField(
            model_name='emailnotification',
            name='body',
        ),
        migrations.RemoveField(
            model_name='emailnotification',
            name='subject',
        ),
        migrations.AddField(
            model_name='emailnotification',
            name='email_templates',
            field=models.ManyToManyField(to='rdrf.EmailTemplate'),
        ),
    ]
