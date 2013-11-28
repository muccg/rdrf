# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Country'
        db.create_table(u'patients_country', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50, primary_key=True)),
        ))
        db.send_create_signal(u'patients', ['Country'])

        # Adding model 'State'
        db.create_table(u'patients_state', (
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=3, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.Country'])),
        ))
        db.send_create_signal(u'patients', ['State'])

        # Adding model 'Doctor'
        db.create_table(u'patients_doctor', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('family_name', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('given_names', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('surgery_name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('speciality', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('address', self.gf('django.db.models.fields.TextField')()),
            ('suburb', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('state', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.State'])),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
        ))
        db.send_create_signal(u'patients', ['Doctor'])

        # Adding model 'NextOfKinRelationship'
        db.create_table(u'patients_nextofkinrelationship', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('relationship', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'patients', ['NextOfKinRelationship'])

        # Adding model 'Parent'
        db.create_table(u'patients_parent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent_given_names', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('parent_family_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('parent_place_of_birth', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('parent_date_of_migration', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'patients', ['Parent'])

        # Adding model 'Patient'
        db.create_table(u'patients_patient', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rdrf_registry', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['rdrf.Registry'])),
            ('working_group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['groups.WorkingGroup'])),
            ('consent', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('family_name', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('given_names', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('umrn', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=50, null=True, blank=True)),
            ('date_of_birth', self.gf('django.db.models.fields.DateField')()),
            ('place_of_birth', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('date_of_migration', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('sex', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('address', self.gf('django.db.models.fields.TextField')()),
            ('suburb', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('state', self.gf('django.db.models.fields.related.ForeignKey')(related_name='patient_set', to=orm['patients.State'])),
            ('postcode', self.gf('django.db.models.fields.IntegerField')()),
            ('home_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('mobile_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('work_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
            ('next_of_kin_family_name', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('next_of_kin_given_names', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('next_of_kin_relationship', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.NextOfKinRelationship'], null=True, blank=True)),
            ('next_of_kin_address', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('next_of_kin_suburb', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('next_of_kin_state', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='next_of_kin_set', null=True, to=orm['patients.State'])),
            ('next_of_kin_postcode', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('next_of_kin_home_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('next_of_kin_mobile_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('next_of_kin_work_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('next_of_kin_email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
            ('next_of_kin_parent_place_of_birth', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('inactive_reason', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'patients', ['Patient'])

        # Adding unique constraint on 'Patient', fields ['family_name', 'given_names', 'working_group']
        db.create_unique(u'patients_patient', ['family_name', 'given_names', 'working_group_id'])

        # Adding model 'PatientConsent'
        db.create_table(u'patients_patientconsent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('patient', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.Patient'])),
            ('form', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal(u'patients', ['PatientConsent'])

        # Adding model 'PatientParent'
        db.create_table(u'patients_patientparent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('patient', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.Patient'])),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.Parent'])),
            ('relationship', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal(u'patients', ['PatientParent'])

        # Adding model 'PatientDoctor'
        db.create_table(u'patients_patientdoctor', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('patient', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.Patient'])),
            ('doctor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.Doctor'])),
            ('relationship', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'patients', ['PatientDoctor'])


    def backwards(self, orm):
        # Removing unique constraint on 'Patient', fields ['family_name', 'given_names', 'working_group']
        db.delete_unique(u'patients_patient', ['family_name', 'given_names', 'working_group_id'])

        # Deleting model 'Country'
        db.delete_table(u'patients_country')

        # Deleting model 'State'
        db.delete_table(u'patients_state')

        # Deleting model 'Doctor'
        db.delete_table(u'patients_doctor')

        # Deleting model 'NextOfKinRelationship'
        db.delete_table(u'patients_nextofkinrelationship')

        # Deleting model 'Parent'
        db.delete_table(u'patients_parent')

        # Deleting model 'Patient'
        db.delete_table(u'patients_patient')

        # Deleting model 'PatientConsent'
        db.delete_table(u'patients_patientconsent')

        # Deleting model 'PatientParent'
        db.delete_table(u'patients_patientparent')

        # Deleting model 'PatientDoctor'
        db.delete_table(u'patients_patientdoctor')


    models = {
        u'groups.workinggroup': {
            'Meta': {'ordering': "['name']", 'object_name': 'WorkingGroup'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'})
        },
        u'patients.country': {
            'Meta': {'ordering': "['name']", 'object_name': 'Country'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'primary_key': 'True'})
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
        u'patients.parent': {
            'Meta': {'object_name': 'Parent'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent_date_of_migration': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'parent_family_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'parent_given_names': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'parent_place_of_birth': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'patients.patient': {
            'Meta': {'ordering': "['family_name', 'given_names', 'date_of_birth']", 'unique_together': "(('family_name', 'given_names', 'working_group'),)", 'object_name': 'Patient'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'address': ('django.db.models.fields.TextField', [], {}),
            'consent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_of_birth': ('django.db.models.fields.DateField', [], {}),
            'date_of_migration': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'doctors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['patients.Doctor']", 'through': u"orm['patients.PatientDoctor']", 'symmetrical': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'given_names': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'home_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inactive_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
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
            'parents': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['patients.Parent']", 'through': u"orm['patients.PatientParent']", 'symmetrical': 'False'}),
            'place_of_birth': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'postcode': ('django.db.models.fields.IntegerField', [], {}),
            'rdrf_registry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.Registry']"}),
            'sex': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'patient_set'", 'to': u"orm['patients.State']"}),
            'suburb': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'umrn': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'work_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'working_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['groups.WorkingGroup']"})
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
        u'patients.patientparent': {
            'Meta': {'object_name': 'PatientParent'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.Parent']"}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.Patient']"}),
            'relationship': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'patients.state': {
            'Meta': {'ordering': "['country__name', 'name']", 'object_name': 'State'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['patients.Country']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '3', 'primary_key': 'True'})
        },
        u'rdrf.registry': {
            'Meta': {'object_name': 'Registry'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'desc': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'splash_screen': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['patients']