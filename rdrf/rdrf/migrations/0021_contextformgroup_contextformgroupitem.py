# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0020_emailnotification_disabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContextFormGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('context_type', models.CharField(default='F', max_length=1,
                                                  choices=[('F', 'Fixed'), ('M', 'Multiple')])),
                ('name', models.CharField(max_length=80)),
                ('registry', models.ForeignKey(to='rdrf.Registry', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='ContextFormGroupItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('context_form_group', models.ForeignKey(to='rdrf.ContextFormGroup', on_delete=models.CASCADE)),
                ('registry_form', models.ForeignKey(to='rdrf.RegistryForm', on_delete=models.CASCADE)),
            ],
        ),
    ]
