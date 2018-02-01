# -*- coding: utf-8 -*-


from django.db import migrations, models
import registry.patients.models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0013_auto_20160604_2245'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patientconsent',
            name='form',
            field=models.FileField(
                storage=registry.patients.models.PatientConsentStorage(),
                upload_to='consents',
                null=True,
                verbose_name='Consent form',
                blank=True),
        ),
    ]
