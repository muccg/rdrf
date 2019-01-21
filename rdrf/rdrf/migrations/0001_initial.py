# -*- coding: utf-8 -*-


from django.db import models, migrations
import positions.fields


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='Adjudication',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('requesting_username', models.CharField(max_length=80)),
                ('patient_id', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='AdjudicationDecision',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('patient', models.IntegerField()),
                ('decision_data', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='AdjudicationDefinition',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('display_name', models.CharField(max_length=80, null=True, blank=True)),
                ('fields', models.TextField()),
                ('result_fields', models.TextField()),
                ('decision_field', models.TextField(null=True, blank=True)),
                ('adjudicator_username', models.CharField(default='admin', max_length=80)),
                ('adjudicating_users', models.TextField(
                    help_text='Either comma-seperated list of usernames and/or working group names', null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='AdjudicationRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('username', models.CharField(max_length=80)),
                ('requesting_username', models.CharField(max_length=80)),
                ('patient', models.IntegerField()),
                ('state', models.CharField(default='C', max_length=1)),
                ('definition', models.ForeignKey(to='rdrf.AdjudicationDefinition', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='AdjudicationResponse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('response_data', models.TextField()),
                ('request', models.ForeignKey(to='rdrf.AdjudicationRequest', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CDEPermittedValue',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('code', models.CharField(max_length=30)),
                ('value', models.CharField(max_length=256)),
                ('questionnaire_value', models.CharField(max_length=256, null=True, blank=True)),
                ('desc', models.TextField(null=True)),
                ('position', models.IntegerField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='CDEPermittedValueGroup',
            fields=[
                ('code', models.CharField(max_length=250, serialize=False, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='CdePolicy',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('condition', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'CDE Policy',
                'verbose_name_plural': 'CDE Policies',
            },
        ),
        migrations.CreateModel(
            name='CommonDataElement',
            fields=[
                ('code', models.CharField(max_length=30, serialize=False, primary_key=True)),
                ('name', models.CharField(help_text='Label for field in form', max_length=250)),
                ('desc', models.TextField(help_text='origin of field', blank=True)),
                ('datatype', models.CharField(help_text='type of field', max_length=50)),
                ('instructions', models.TextField(help_text='Used to indicate help text for field', blank=True)),
                ('allow_multiple', models.BooleanField(default=False,
                                                       help_text='If a range, indicate whether multiple selections allowed')),
                ('max_length', models.IntegerField(help_text='Length of field - only used for character fields', null=True, blank=True)),
                ('max_value', models.IntegerField(help_text='Only used for numeric fields', null=True, blank=True)),
                ('min_value', models.IntegerField(help_text='Only used for numeric fields', null=True, blank=True)),
                ('is_required', models.BooleanField(default=False, help_text='Indicate whether field is non-optional')),
                ('pattern', models.CharField(
                    help_text='Regular expression to validate string fields (optional)', max_length=50, blank=True)),
                ('widget_name', models.CharField(
                    help_text='If a special widget required indicate here - leave blank otherwise', max_length=80, blank=True)),
                ('calculation', models.TextField(
                    help_text='Calculation in javascript. Use context.CDECODE to refer to other CDEs. Must use context.result to set output', blank=True)),
                ('questionnaire_text', models.TextField(
                    help_text='The text to use in any public facing questionnaires/registration forms', blank=True)),
                ('pv_group', models.ForeignKey(blank=True, to='rdrf.CDEPermittedValueGroup',
                                               help_text='If a range, indicate the Permissible Value Group', null=True,
                                               on_delete=models.SET_NULL)),
            ],
            options={
                'verbose_name': 'Data Element',
                'verbose_name_plural': 'Data Elements',
            },
        ),
        migrations.CreateModel(
            name='ConsentQuestion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=20)),
                ('position', models.IntegerField(null=True, blank=True)),
                ('question_label', models.TextField()),
                ('instructions', models.TextField(blank=True)),
                ('questionnaire_label', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='ConsentSection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=20)),
                ('section_label', models.CharField(max_length=100)),
                ('information_link', models.CharField(max_length=100, null=True, blank=True)),
                ('applicability_condition', models.TextField(blank=True)),
                ('validation_rule', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='DemographicFields',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', models.CharField(max_length=50)),
                ('readonly', models.NullBooleanField()),
                ('hidden', models.NullBooleanField()),
                ('group', models.ForeignKey(to='auth.Group', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name_plural': 'Demographic Fields',
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('from_username', models.CharField(max_length=80)),
                ('to_username', models.CharField(max_length=80)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('message', models.TextField()),
                ('link', models.CharField(default='', max_length=100)),
                ('seen', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='QuestionnaireResponse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_submitted', models.DateTimeField(auto_now_add=True)),
                ('processed', models.BooleanField(default=False)),
                ('patient_id', models.IntegerField(
                    help_text='The id of the patient created from this response, if any', null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Registry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=80)),
                ('code', models.CharField(max_length=10)),
                ('desc', models.TextField()),
                ('splash_screen', models.TextField()),
                ('patient_splash_screen', models.TextField(null=True, blank=True)),
                ('version', models.CharField(max_length=20, blank=True)),
                ('metadata_json', models.TextField(blank=True)),
            ],
            options={
                'verbose_name_plural': 'registries',
            },
        ),
        migrations.CreateModel(
            name='RegistryForm',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=80)),
                ('questionnaire_display_name', models.CharField(max_length=80, blank=True)),
                ('sections', models.TextField(help_text='Comma-separated list of sections')),
                ('is_questionnaire', models.BooleanField(default=False,
                                                         help_text="Check if this form is questionnaire form for it's registry")),
                ('is_questionnaire_login', models.BooleanField(default=False,
                                                               help_text='If the form is a questionnaire, is it accessible only by logged in users?', verbose_name='Questionnaire Login Required')),
                ('position', positions.fields.PositionField(default=-1)),
                ('questionnaire_questions', models.TextField(
                    help_text='Comma-separated list of sectioncode.cdecodes for questionnnaire', blank=True)),
                ('complete_form_cdes', models.ManyToManyField(to='rdrf.CommonDataElement', blank=True)),
                ('groups_allowed', models.ManyToManyField(to='auth.Group', blank=True)),
                ('registry', models.ForeignKey(to='rdrf.Registry', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=100)),
                ('display_name', models.CharField(max_length=200)),
                ('questionnaire_display_name', models.CharField(max_length=200, blank=True)),
                ('elements', models.TextField()),
                ('allow_multiple', models.BooleanField(default=False, help_text='Allow extra items to be added')),
                ('extra', models.IntegerField(help_text='Extra rows to show if allow_multiple checked', null=True, blank=True)),
                ('questionnaire_help', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Wizard',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('registry', models.CharField(max_length=50)),
                ('forms', models.TextField(help_text='A comma-separated list of forms')),
                ('rules', models.TextField(help_text='Rules')),
            ],
        ),
        migrations.AddField(
            model_name='registry',
            name='patient_data_section',
            field=models.ForeignKey(blank=True,
                                    to='rdrf.Section',
                                    null=True,
                                    on_delete=models.SET_NULL),
        ),
        migrations.AddField(
            model_name='questionnaireresponse',
            name='registry',
            field=models.ForeignKey(to='rdrf.Registry',
                                    on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='demographicfields',
            name='registry',
            field=models.ForeignKey(to='rdrf.Registry',
                                    on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='consentsection',
            name='registry',
            field=models.ForeignKey(related_name='consent_sections',
                                    to='rdrf.Registry', 
                                    on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='consentquestion',
            name='section',
            field=models.ForeignKey(related_name='questions',
                                    to='rdrf.ConsentSection',
                                    on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='cdepolicy',
            name='cde',
            field=models.ForeignKey(to='rdrf.CommonDataElement',
                                    on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='cdepolicy',
            name='groups_allowed',
            field=models.ManyToManyField(to='auth.Group', blank=True),
        ),
        migrations.AddField(
            model_name='cdepolicy',
            name='registry',
            field=models.ForeignKey(to='rdrf.Registry',
                                    on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='cdepermittedvalue',
            name='pv_group',
            field=models.ForeignKey(related_name='permitted_value_set',
                                    to='rdrf.CDEPermittedValueGroup',
                                    on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='adjudicationdefinition',
            name='registry',
            field=models.ForeignKey(to='rdrf.Registry',
                                    on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='adjudicationdecision',
            name='definition',
            field=models.ForeignKey(to='rdrf.AdjudicationDefinition',
                                    on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='adjudication',
            name='decision',
            field=models.ForeignKey(to='rdrf.AdjudicationDecision', 
                                    null=True,
                                    on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='adjudication',
            name='definition',
            field=models.ForeignKey(to='rdrf.AdjudicationDefinition',
                                    on_delete=models.CASCADE),
        ),
    ]
