# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0001_initial'),
        ('rdrf', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('groups', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='rdrf_registry',
            field=models.ManyToManyField(
                to='rdrf.Registry'),
        ),
        migrations.AddField(
            model_name='patient',
            name='user',
            field=models.ForeignKey(
                related_name='user_object',
                on_delete=models.SET_NULL,
                blank=True,
                to=settings.AUTH_USER_MODEL,
                null=True),
        ),
        migrations.AddField(
            model_name='patient',
            name='working_groups',
            field=models.ManyToManyField(
                related_name='my_patients',
                verbose_name='Centre',
                to='groups.WorkingGroup'),
        ),
        migrations.AddField(
            model_name='parentguardian',
            name='patient',
            field=models.ManyToManyField(
                to='patients.Patient'),
        ),
        migrations.AddField(
            model_name='parentguardian',
            name='self_patient',
            field=models.ForeignKey(
                related_name='self_patient',
                blank=True,
                to='patients.Patient',
                null=True,
                on_delete=models.SET_NULL),
        ),
        migrations.AddField(
            model_name='parentguardian',
            name='user',
            field=models.ForeignKey(
                related_name='parent_user_object',
                on_delete=models.SET_NULL,
                blank=True,
                to=settings.AUTH_USER_MODEL,
                null=True),
        ),
        migrations.AddField(
            model_name='doctor',
            name='state',
            field=models.ForeignKey(
                verbose_name='State/Province/Territory',
                to='patients.State',
                on_delete=models.DO_NOTHING),
        ),
        migrations.AddField(
            model_name='consentvalue',
            name='consent_question',
            field=models.ForeignKey(
                to='rdrf.ConsentQuestion',
                on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='consentvalue',
            name='patient',
            field=models.ForeignKey(
                related_name='consents',
                to='patients.Patient',
                on_delete=models.CASCADE),
        ),
    ]
