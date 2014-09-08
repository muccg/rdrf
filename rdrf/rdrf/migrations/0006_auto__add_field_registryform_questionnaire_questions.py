# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'RegistryForm.questionnaire_questions'
        db.add_column(u'rdrf_registryform', 'questionnaire_questions',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'RegistryForm.questionnaire_questions'
        db.delete_column(u'rdrf_registryform', 'questionnaire_questions')


    models = {
        u'rdrf.cdepermittedvalue': {
            'Meta': {'object_name': 'CDEPermittedValue'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '30', 'primary_key': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'pv_group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'permitted_value_set'", 'to': u"orm['rdrf.CDEPermittedValueGroup']"}),
            'questionnaire_value': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
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
            'splash_screen': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        },
        u'rdrf.registryform': {
            'Meta': {'object_name': 'RegistryForm'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_questionnaire': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'questionnaire_questions': ('django.db.models.fields.TextField', [], {'default': "''"}),
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