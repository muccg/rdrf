# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Patient.inactive_reason'
        db.add_column('patients_patient', 'inactive_reason',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Patient.inactive_reason'
        db.delete_column('patients_patient', 'inactive_reason')


    models = {
        'groups.workinggroup': {
            'Meta': {'ordering': "['name']", 'object_name': 'WorkingGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'})
        },
        'patients.country': {
            'Meta': {'ordering': "['name']", 'object_name': 'Country'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'primary_key': 'True'})
        },
        'patients.doctor': {
            'Meta': {'object_name': 'Doctor'},
            'address': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'given_names': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'speciality': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['patients.State']"}),
            'suburb': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'surgery_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'})
        },
        'patients.nextofkinrelationship': {
            'Meta': {'object_name': 'NextOfKinRelationship'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'relationship': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'patients.parent': {
            'Meta': {'object_name': 'Parent'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent_date_of_migration': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'parent_family_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'parent_given_names': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'parent_place_of_birth': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'patients.patient': {
            'Meta': {'ordering': "['family_name', 'given_names', 'date_of_birth']", 'unique_together': "(('family_name', 'given_names', 'working_group'),)", 'object_name': 'Patient'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'address': ('django.db.models.fields.TextField', [], {}),
            'consent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'consent_form': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'date_of_birth': ('django.db.models.fields.DateField', [], {}),
            'date_of_migration': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'doctors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['patients.Doctor']", 'through': "orm['patients.PatientDoctor']", 'symmetrical': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'given_names': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'home_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inactive_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'mobile_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_address': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'next_of_kin_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_family_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_given_names': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_home_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_mobile_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_postcode': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'next_of_kin_relationship': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['patients.NextOfKinRelationship']", 'null': 'True', 'blank': 'True'}),
            'next_of_kin_state': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'next_of_kin_set'", 'null': 'True', 'to': "orm['patients.State']"}),
            'next_of_kin_suburb': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_work_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'parents': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['patients.Parent']", 'through': "orm['patients.PatientParent']", 'symmetrical': 'False'}),
            'place_of_birth': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'postcode': ('django.db.models.fields.IntegerField', [], {}),
            'sex': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'patient_set'", 'to': "orm['patients.State']"}),
            'suburb': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'umrn': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'work_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'working_group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['groups.WorkingGroup']"})
        },
        'patients.patientdoctor': {
            'Meta': {'object_name': 'PatientDoctor'},
            'doctor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['patients.Doctor']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['patients.Patient']"}),
            'relationship': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'patients.patientparent': {
            'Meta': {'object_name': 'PatientParent'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['patients.Parent']"}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['patients.Patient']"}),
            'relationship': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'patients.state': {
            'Meta': {'ordering': "['country__name', 'name']", 'object_name': 'State'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['patients.Country']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '3', 'primary_key': 'True'})
        }
    }

    complete_apps = ['patients']
