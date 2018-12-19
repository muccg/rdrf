# -*- coding: utf-8 -*-


from django.db import migrations, models
import rdrf.models.definition.models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0026_auto_20160314_1127'),
    ]

    operations = [
        migrations.CreateModel(
            name='CDEFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('item', models.FileField(upload_to=rdrf.models.definition.models.file_upload_to, max_length=300)),
                ('filename', models.CharField(max_length=255)),
                ('cde', models.ForeignKey(to='rdrf.CommonDataElement', on_delete=models.CASCADE)),
                ('form', models.ForeignKey(blank=True, to='rdrf.RegistryForm', null=True, on_delete=models.SET_NULL)),
                ('registry', models.ForeignKey(to='rdrf.Registry', on_delete=models.CASCADE)),
                ('section', models.ForeignKey(blank=True, to='rdrf.Section', null=True, on_delete=models.SET_NULL)),
            ],
        ),
    ]
