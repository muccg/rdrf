# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0009_auto_20150911_1128'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClinicianOther',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('clinician_name', models.CharField(max_length=200, null=True)),
                ('clinician_hospital', models.CharField(max_length=200, null=True)),
                ('clinician_address', models.CharField(max_length=200, null=True)),
                ('patient', models.ForeignKey(to='patients.Patient', null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='patientrelative',
            name='relationship',
            field=models.CharField(max_length=80, choices=[(b'Parent (1st degree)', b'Parent (1st degree)'), (b'Child (1st degree)', b'Child (1st degree)'), (b'Sibling (1st degree)', b'Sibling (1st degree)'), (b'Identical Twin (0th degree)', b'Identical Twin (0th degree)'), (b'Non-identical Twin (1st degree)', b'Non-identical Twin (1st degree)'), (b'Half Sibling (1st degree)', b'Half Sibling (1st degree)'), (b'Grandparent (2nd degree)', b'Grandparent (2nd degree)'), (b'Grandchild (2nd degree)', b'Grandchild (2nd degree)'), (b'Uncle/Aunt (2nd degree)', b'Uncle/Aunt (2nd degree)'), (b'Niece/Nephew (2nd degree)', b'Niece/Nephew (2nd degree)'), (b'1st Cousin (3rd degree)', b'1st Cousin (3rd degree)'), (b'Great Grandparent (3rd degree)', b'Great Grandparent (3rd degree)'), (b'Great Grandchild (3rd degree)', b'Great Grandchild (3rd degree)'), (b'Great Uncle/Aunt (3rd degree)', b'Great Uncle/Aunt (3rd degree)'), (b'Grand Niece/Nephew (3rd degree)', b'Grand Niece/Nephew (3rd degree)'), (b'1st Cousin once removed (4th degree)', b'1st Cousin once removed (4th degree)'), (b'Spouse', b'Spouse'), (b'Unknown', b'Unknown'), (b'Other', b'Other')]),
        ),
    ]
