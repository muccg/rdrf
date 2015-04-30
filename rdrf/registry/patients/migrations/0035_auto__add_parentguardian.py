# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ParentGuardian'
        db.create_table(u'patients_parentguardian', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('date_of_birth', self.gf('django.db.models.fields.DateField')()),
            ('gender', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('address', self.gf('django.db.models.fields.TextField')()),
            ('suburb', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('postcode', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal(u'patients', ['ParentGuardian'])

        # Adding M2M table for field patient on 'ParentGuardian'
        m2m_table_name = db.shorten_name(u'patients_parentguardian_patient')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('parentguardian', models.ForeignKey(orm[u'patients.parentguardian'], null=False)),
            ('patient', models.ForeignKey(orm[u'patients.patient'], null=False))
        ))
        db.create_unique(m2m_table_name, ['parentguardian_id', 'patient_id'])


    def backwards(self, orm):
        # Deleting model 'ParentGuardian'
        db.delete_table(u'patients_parentguardian')

        # Removing M2M table for field patient on 'ParentGuardian'
        db.delete_table(db.shorten_name(u'patients_parentguardian_patient'))


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'groups.customuser': {
            'Meta': {'object_name': 'CustomUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'registry': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'registry'", 'symmetrical': 'False', 'to': u"orm['rdrf.Registry']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'working_groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'working_groups'", 'null': 'True', 'to': u"orm['groups.WorkingGroup']"})
        },
        u'groups.workinggroup': {
            'Meta': {'ordering': "['name']", 'object_name': 'WorkingGroup'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'registry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.Registry']", 'null': 'True'})
        },
        u'patients.addresstype': {
            'Meta': {'object_name': 'AddressType'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'patients.doctor': {
            'Meta': {'ordering': "['family_name']", 'object_name': 'Doctor'},
            'address': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'given_names': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'speciality': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.State']"}),
            'suburb': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'surgery_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'})
        },
        u'patients.nextofkinrelationship': {
            'Meta': {'object_name': 'NextOfKinRelationship'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'relationship': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'patients.parentguardian': {
            'Meta': {'object_name': 'ParentGuardian'},
            'address': ('django.db.models.fields.TextField', [], {}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'date_of_birth': ('django.db.models.fields.DateField', [], {}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'patient': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['patients.Patient']", 'symmetrical': 'False'}),
            'postcode': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'suburb': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'patients.patient': {
            'Meta': {'ordering': "['family_name', 'given_names', 'date_of_birth']", 'object_name': 'Patient'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'clinician': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['groups.CustomUser']", 'null': 'True', 'blank': 'True'}),
            'consent': ('django.db.models.fields.BooleanField', [], {}),
            'consent_clinical_trials': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'consent_provided_by_parent_guardian': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'consent_sent_information': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'country_of_birth': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'date_of_birth': ('django.db.models.fields.DateField', [], {}),
            'doctors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['patients.Doctor']", 'through': u"orm['patients.PatientDoctor']", 'symmetrical': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'ethnic_origin': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'given_names': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'home_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inactive_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'maiden_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'mobile_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_address': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'next_of_kin_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_family_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_given_names': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_home_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_mobile_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_parent_place_of_birth': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_postcode': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'next_of_kin_relationship': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.NextOfKinRelationship']", 'null': 'True', 'blank': 'True'}),
            'next_of_kin_state': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'next_of_kin_set'", 'null': 'True', 'to': u"orm['patients.State']"}),
            'next_of_kin_suburb': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_work_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'place_of_birth': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'rdrf_registry': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['rdrf.Registry']", 'symmetrical': 'False'}),
            'sex': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'umrn': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'user_object'", 'null': 'True', 'to': u"orm['groups.CustomUser']"}),
            'work_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'working_groups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'my_patients'", 'symmetrical': 'False', 'to': u"orm['groups.WorkingGroup']"})
        },
        u'patients.patientaddress': {
            'Meta': {'object_name': 'PatientAddress'},
            'address': ('django.db.models.fields.TextField', [], {}),
            'address_type': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['patients.AddressType']"}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.Patient']"}),
            'postcode': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'suburb': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'patients.patientconsent': {
            'Meta': {'object_name': 'PatientConsent'},
            'form': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.Patient']"})
        },
        u'patients.patientdoctor': {
            'Meta': {'object_name': 'PatientDoctor'},
            'doctor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.Doctor']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.Patient']"}),
            'relationship': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'patients.patientrelative': {
            'Meta': {'object_name': 'PatientRelative'},
            'date_of_birth': ('django.db.models.fields.DateField', [], {}),
            'family_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'given_names': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'living_status': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relatives'", 'to': u"orm['patients.Patient']"}),
            'relationship': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'relative_patient': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'as_a_relative'", 'unique': 'True', 'null': 'True', 'to': u"orm['patients.Patient']"}),
            'sex': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        u'patients.state': {
            'Meta': {'ordering': "['name']", 'object_name': 'State'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '3', 'primary_key': 'True'})
        },
        u'rdrf.registry': {
            'Meta': {'object_name': 'Registry'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'desc': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metadata_json': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'patient_data_section': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.Section']", 'null': 'True', 'blank': 'True'}),
            'patient_splash_screen': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'splash_screen': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        },
        u'rdrf.section': {
            'Meta': {'object_name': 'Section'},
            'allow_multiple': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'elements': ('django.db.models.fields.TextField', [], {}),
            'extra': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'questionnaire_display_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'questionnaire_help': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['patients']