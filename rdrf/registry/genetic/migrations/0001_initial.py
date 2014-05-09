# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Gene'
        db.create_table(u'genetic_gene', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('symbol', self.gf('django.db.models.fields.TextField')()),
            ('hgnc_id', self.gf('django.db.models.fields.TextField')()),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('status', self.gf('django.db.models.fields.TextField')()),
            ('chromosome', self.gf('django.db.models.fields.TextField')()),
            ('accession_numbers', self.gf('django.db.models.fields.TextField')()),
            ('refseq_id', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'genetic', ['Gene'])

        # Adding model 'Technique'
        db.create_table(u'genetic_technique', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50, primary_key=True)),
        ))
        db.send_create_signal(u'genetic', ['Technique'])

        # Adding model 'Laboratory'
        db.create_table(u'genetic_laboratory', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('address', self.gf('django.db.models.fields.TextField')(max_length=200, blank=True)),
            ('contact_name', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('contact_email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('contact_phone', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
        ))
        db.send_create_signal(u'genetic', ['Laboratory'])


    def backwards(self, orm):
        # Deleting model 'Gene'
        db.delete_table(u'genetic_gene')

        # Deleting model 'Technique'
        db.delete_table(u'genetic_technique')

        # Deleting model 'Laboratory'
        db.delete_table(u'genetic_laboratory')


    models = {
        u'genetic.gene': {
            'Meta': {'ordering': "['symbol']", 'object_name': 'Gene'},
            'accession_numbers': ('django.db.models.fields.TextField', [], {}),
            'chromosome': ('django.db.models.fields.TextField', [], {}),
            'hgnc_id': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'refseq_id': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.TextField', [], {}),
            'symbol': ('django.db.models.fields.TextField', [], {})
        },
        u'genetic.laboratory': {
            'Meta': {'object_name': 'Laboratory'},
            'address': ('django.db.models.fields.TextField', [], {'max_length': '200', 'blank': 'True'}),
            'contact_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'contact_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        u'genetic.technique': {
            'Meta': {'object_name': 'Technique'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'primary_key': 'True'})
        }
    }

    complete_apps = ['genetic']