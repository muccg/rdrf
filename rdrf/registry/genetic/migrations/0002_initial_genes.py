# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):

        from django.core.management import call_command
        call_command("loaddata", "initial_genes.json", exceptiononerror=True)


    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'genetic.gene': {
            'Meta': {'ordering': "['symbol']", 'object_name': 'Gene'},
            'accession_numbers': ('django.db.models.fields.TextField', [], {}),
            'chromosome': ('django.db.models.fields.TextField', [], {}),
            'hgnc_id': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'refseq_id': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'symbol': ('django.db.models.fields.TextField', [], {'primary_key': 'True'})
        },
        'genetic.moleculardata': {
            'Meta': {'ordering': "['patient']", 'object_name': 'MolecularData'},
            'patient': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['patients.Patient']", 'unique': 'True', 'primary_key': 'True'})
        },
        'genetic.variation': {
            'Meta': {'object_name': 'Variation'},
            'all_exons_in_male_relative': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'deletion_all_exons_tested': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'dna_variation': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'dna_variation_validation_override': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'duplication_all_exons_tested': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'exon': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'exon_boundaries_known': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'exon_validation_override': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'gene': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['genetic.Gene']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'molecular_data': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['genetic.MolecularData']"}),
            'point_mutation_all_exons_sequenced': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'protein_variation': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'protein_variation_validation_override': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rna_variation': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'rna_variation_validation_override': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'technique': ('django.db.models.fields.TextField', [], {})
        },
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

    complete_apps = ['genetic']
