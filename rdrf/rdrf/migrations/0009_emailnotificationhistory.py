# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0008_emailtemplate_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailNotificationHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_stamp', models.DateTimeField(auto_now_add=True)),
                ('language', models.CharField(max_length=10)),
                ('email_notification', models.ForeignKey(to='rdrf.EmailNotification',
                                                        on_delete=models.CASCADE)),
            ],
        ),
    ]
