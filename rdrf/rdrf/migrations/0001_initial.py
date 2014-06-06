# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Registry'
        db.create_table(u'rdrf_registry', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('desc', self.gf('django.db.models.fields.TextField')()),
            ('splash_screen', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'rdrf', ['Registry'])

        # Adding model 'CDEPermittedValueGroup'
        db.create_table(u'rdrf_cdepermittedvaluegroup', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=250, primary_key=True)),
        ))
        db.send_create_signal(u'rdrf', ['CDEPermittedValueGroup'])

        # Adding model 'CDEPermittedValue'
        db.create_table(u'rdrf_cdepermittedvalue', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=30, primary_key=True)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('desc', self.gf('django.db.models.fields.TextField')(null=True)),
            ('pv_group', self.gf('django.db.models.fields.related.ForeignKey')(related_name='permitted_value_set', to=orm['rdrf.CDEPermittedValueGroup'])),
        ))
        db.send_create_signal(u'rdrf', ['CDEPermittedValue'])

        # Adding model 'CommonDataElement'
        db.create_table(u'rdrf_commondataelement', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=30, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('desc', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('datatype', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('instructions', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('pv_group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['rdrf.CDEPermittedValueGroup'], null=True, blank=True)),
            ('allow_multiple', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('max_length', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('max_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('min_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('is_required', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('pattern', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('widget_name', self.gf('django.db.models.fields.CharField')(max_length=80, blank=True)),
            ('calculation', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('questionnaire_text', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'rdrf', ['CommonDataElement'])

        # Adding model 'RegistryForm'
        db.create_table(u'rdrf_registryform', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('registry', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['rdrf.Registry'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('sections', self.gf('django.db.models.fields.TextField')()),
            ('is_questionnaire', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'rdrf', ['RegistryForm'])

        # Adding model 'Section'
        db.create_table(u'rdrf_section', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('elements', self.gf('django.db.models.fields.TextField')()),
            ('allow_multiple', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('extra', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'rdrf', ['Section'])

        # Adding model 'Wizard'
        db.create_table(u'rdrf_wizard', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('registry', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('forms', self.gf('django.db.models.fields.TextField')()),
            ('rules', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'rdrf', ['Wizard'])

        # Adding model 'QuestionnaireResponse'
        db.create_table(u'rdrf_questionnaireresponse', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('registry', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['rdrf.Registry'])),
            ('date_submitted', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('processed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('patient_id', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'rdrf', ['QuestionnaireResponse'])


    def backwards(self, orm):
        # Deleting model 'Registry'
        db.delete_table(u'rdrf_registry')

        # Deleting model 'CDEPermittedValueGroup'
        db.delete_table(u'rdrf_cdepermittedvaluegroup')

        # Deleting model 'CDEPermittedValue'
        db.delete_table(u'rdrf_cdepermittedvalue')

        # Deleting model 'CommonDataElement'
        db.delete_table(u'rdrf_commondataelement')

        # Deleting model 'RegistryForm'
        db.delete_table(u'rdrf_registryform')

        # Deleting model 'Section'
        db.delete_table(u'rdrf_section')

        # Deleting model 'Wizard'
        db.delete_table(u'rdrf_wizard')

        # Deleting model 'QuestionnaireResponse'
        db.delete_table(u'rdrf_questionnaireresponse')


    models = {
        u'rdrf.cdepermittedvalue': {
            'Meta': {'object_name': 'CDEPermittedValue'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '30', 'primary_key': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'pv_group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'permitted_value_set'", 'to': u"orm['rdrf.CDEPermittedValueGroup']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        u'rdrf.cdepermittedvaluegroup': {
            'Meta': {'object_name': 'CDEPermittedValueGroup'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '250', 'primary_key': 'True'})
        },
        u'rdrf.commondataelement': {
            'Meta': {'object_name': 'CommonDataElement'},
            'allow_multiple': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'calculation': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '30', 'primary_key': 'True'}),
            'datatype': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'desc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'instructions': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'is_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'pattern': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'pv_group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.CDEPermittedValueGroup']", 'null': 'True', 'blank': 'True'}),
            'questionnaire_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'widget_name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        u'rdrf.questionnaireresponse': {
            'Meta': {'object_name': 'QuestionnaireResponse'},
            'date_submitted': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'registry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.Registry']"})
        },
        u'rdrf.registry': {
            'Meta': {'object_name': 'Registry'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'desc': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'splash_screen': ('django.db.models.fields.TextField', [], {})
        },
        u'rdrf.registryform': {
            'Meta': {'object_name': 'RegistryForm'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_questionnaire': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'registry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.Registry']"}),
            'sections': ('django.db.models.fields.TextField', [], {})
        },
        u'rdrf.section': {
            'Meta': {'object_name': 'Section'},
            'allow_multiple': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'elements': ('django.db.models.fields.TextField', [], {}),
            'extra': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'rdrf.wizard': {
            'Meta': {'object_name': 'Wizard'},
            'forms': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'registry': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'rules': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['rdrf']