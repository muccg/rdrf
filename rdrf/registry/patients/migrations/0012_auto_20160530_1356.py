# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0011_parentguardian_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinicianother',
            name='clinician_email',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='clinicianother',
            name='clinician_phone_number',
            field=models.CharField(max_length=254, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='patient',
            name='rdrf_registry',
            field=models.ManyToManyField(related_name='patients', to='rdrf.Registry'),
        ),
    ]
