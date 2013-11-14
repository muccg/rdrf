# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Country'
        db.create_table('patients_country', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50, primary_key=True)),
        ))
        db.send_create_signal('patients', ['Country'])

        # Adding model 'State'
        db.create_table('patients_state', (
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=3, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.Country'])),
        ))
        db.send_create_signal('patients', ['State'])

        # Adding model 'Doctor'
        db.create_table('patients_doctor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
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
        db.send_create_signal('patients', ['Doctor'])

        # Adding model 'Patient'
        db.create_table('patients_patient', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('working_group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['groups.WorkingGroup'])),
            ('consent', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('family_name', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('given_names', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('date_of_birth', self.gf('django.db.models.fields.DateField')()),
            ('sex', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('address', self.gf('django.db.models.fields.TextField')()),
            ('suburb', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('state', self.gf('django.db.models.fields.related.ForeignKey')(related_name='patient_set', to=orm['patients.State'])),
            ('postcode', self.gf('django.db.models.fields.IntegerField')()),
            ('home_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('mobile_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('work_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
            ('next_of_kin_family_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('next_of_kin_given_names', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('next_of_kin_address', self.gf('django.db.models.fields.TextField')()),
            ('next_of_kin_suburb', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('next_of_kin_state', self.gf('django.db.models.fields.related.ForeignKey')(related_name='next_of_kin_set', to=orm['patients.State'])),
            ('next_of_kin_postcode', self.gf('django.db.models.fields.IntegerField')()),
            ('next_of_kin_home_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('next_of_kin_mobile_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('next_of_kin_work_phone', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('next_of_kin_email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('patients', ['Patient'])

        # Adding unique constraint on 'Patient', fields ['family_name', 'given_names', 'working_group']
        db.create_unique('patients_patient', ['family_name', 'given_names', 'working_group_id'])

        # Adding model 'PatientDoctor'
        db.create_table('patients_patientdoctor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('patient', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.Patient'])),
            ('doctor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['patients.Doctor'])),
            ('relationship', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('patients', ['PatientDoctor'])


    def backwards(self, orm):

        # Removing unique constraint on 'Patient', fields ['family_name', 'given_names', 'working_group']
        db.delete_unique('patients_patient', ['family_name', 'given_names', 'working_group_id'])

        # Deleting model 'Country'
        db.delete_table('patients_country')

        # Deleting model 'State'
        db.delete_table('patients_state')

        # Deleting model 'Doctor'
        db.delete_table('patients_doctor')

        # Deleting model 'Patient'
        db.delete_table('patients_patient')

        # Deleting model 'PatientDoctor'
        db.delete_table('patients_patientdoctor')


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
        'patients.patient': {
            'Meta': {'ordering': "['family_name', 'given_names', 'date_of_birth']", 'unique_together': "(('family_name', 'given_names', 'working_group'),)", 'object_name': 'Patient'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'address': ('django.db.models.fields.TextField', [], {}),
            'consent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_of_birth': ('django.db.models.fields.DateField', [], {}),
            'doctors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['patients.Doctor']", 'through': "orm['patients.PatientDoctor']", 'symmetrical': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'given_names': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'home_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mobile_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_address': ('django.db.models.fields.TextField', [], {}),
            'next_of_kin_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_family_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'next_of_kin_given_names': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'next_of_kin_home_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_mobile_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'next_of_kin_postcode': ('django.db.models.fields.IntegerField', [], {}),
            'next_of_kin_state': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'next_of_kin_set'", 'to': "orm['patients.State']"}),
            'next_of_kin_suburb': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'next_of_kin_work_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'postcode': ('django.db.models.fields.IntegerField', [], {}),
            'sex': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'patient_set'", 'to': "orm['patients.State']"}),
            'suburb': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
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
        'patients.state': {
            'Meta': {'ordering': "['country__name', 'name']", 'object_name': 'State'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['patients.Country']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '3', 'primary_key': 'True'})
        }
    }

    complete_apps = ['patients']
