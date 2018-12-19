# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0009_auto_20150911_1128'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClinicianOther',
            fields=[
                ('id',
                 models.AutoField(
                     verbose_name='ID',
                     serialize=False,
                     auto_created=True,
                     primary_key=True)),
                ('clinician_name',
                 models.CharField(
                     max_length=200,
                     null=True)),
                ('clinician_hospital',
                 models.CharField(
                     max_length=200,
                     null=True)),
                ('clinician_address',
                 models.CharField(
                     max_length=200,
                     null=True)),
                ('patient',
                 models.ForeignKey(
                     to='patients.Patient',
                     null=True,
                     on_delete=models.SET_NULL)),
            ],
        ),
        migrations.AlterField(
            model_name='patientrelative',
            name='relationship',
            field=models.CharField(
                max_length=80,
                choices=[
                    ('Parent (1st degree)',
                     'Parent (1st degree)'),
                    ('Child (1st degree)',
                     'Child (1st degree)'),
                    ('Sibling (1st degree)',
                     'Sibling (1st degree)'),
                    ('Identical Twin (0th degree)',
                     'Identical Twin (0th degree)'),
                    ('Non-identical Twin (1st degree)',
                     'Non-identical Twin (1st degree)'),
                    ('Half Sibling (1st degree)',
                     'Half Sibling (1st degree)'),
                    ('Grandparent (2nd degree)',
                     'Grandparent (2nd degree)'),
                    ('Grandchild (2nd degree)',
                     'Grandchild (2nd degree)'),
                    ('Uncle/Aunt (2nd degree)',
                     'Uncle/Aunt (2nd degree)'),
                    ('Niece/Nephew (2nd degree)',
                     'Niece/Nephew (2nd degree)'),
                    ('1st Cousin (3rd degree)',
                     '1st Cousin (3rd degree)'),
                    ('Great Grandparent (3rd degree)',
                     'Great Grandparent (3rd degree)'),
                    ('Great Grandchild (3rd degree)',
                     'Great Grandchild (3rd degree)'),
                    ('Great Uncle/Aunt (3rd degree)',
                     'Great Uncle/Aunt (3rd degree)'),
                    ('Grand Niece/Nephew (3rd degree)',
                     'Grand Niece/Nephew (3rd degree)'),
                    ('1st Cousin once removed (4th degree)',
                     '1st Cousin once removed (4th degree)'),
                    ('Spouse',
                     'Spouse'),
                    ('Unknown',
                     'Unknown'),
                    ('Other',
                     'Other')]),
        ),
    ]
