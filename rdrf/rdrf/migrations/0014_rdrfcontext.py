# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('rdrf', '0013_auto_20151201_1410'),
    ]

    operations = [
        migrations.CreateModel(
            name='RDRFContext',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('display_name', models.CharField(max_length=80, null=True, blank=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType',
                                                    on_delete=models.CASCADE)),
                ('registry', models.ForeignKey(to='rdrf.Registry',
                                                on_delete=models.CASCADE)),
            ],
        ),
    ]
