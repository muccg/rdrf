# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Section.questionnaire_display_name'
        db.add_column(u'rdrf_section', 'questionnaire_display_name',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Section.questionnaire_display_name'
        db.delete_column(u'rdrf_section', 'questionnaire_display_name')


    models = {
        u'rdrf.adjudication': {
            'Meta': {'object_name': 'Adjudication'},
            'decision': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.AdjudicationDecision']", 'null': 'True'}),
            'definition': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.AdjudicationDefinition']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient_id': ('django.db.models.fields.IntegerField', [], {}),
            'requesting_username': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        u'rdrf.adjudicationdecision': {
            'Meta': {'object_name': 'AdjudicationDecision'},
            'decision_data': ('django.db.models.fields.TextField', [], {}),
            'definition': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.AdjudicationDefinition']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient': ('django.db.models.fields.IntegerField', [], {})
        },
        u'rdrf.adjudicationdefinition': {
            'Meta': {'object_name': 'AdjudicationDefinition'},
            'adjudicating_users': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'adjudicator_username': ('django.db.models.fields.CharField', [], {'default': "'admin'", 'max_length': '80'}),
            'decision_field': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'fields': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'registry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.Registry']"}),
            'result_fields': ('django.db.models.fields.TextField', [], {})
        },
        u'rdrf.adjudicationrequest': {
            'Meta': {'object_name': 'AdjudicationRequest'},
            'definition': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.AdjudicationDefinition']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient': ('django.db.models.fields.IntegerField', [], {}),
            'requesting_username': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        u'rdrf.adjudicationresponse': {
            'Meta': {'object_name': 'AdjudicationResponse'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.AdjudicationRequest']"}),
            'response_data': ('django.db.models.fields.TextField', [], {})
        },
        u'rdrf.cdepermittedvalue': {
            'Meta': {'object_name': 'CDEPermittedValue'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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
        u'rdrf.notification': {
            'Meta': {'object_name': 'Notification'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_username': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'seen': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'to_username': ('django.db.models.fields.CharField', [], {'max_length': '80'})
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
            'metadata_json': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'patient_data_section': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.Section']", 'null': 'True', 'blank': 'True'}),
            'patient_splash_screen': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'splash_screen': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        },
        u'rdrf.registryform': {
            'Meta': {'object_name': 'RegistryForm'},
            'complete_form_cdes': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['rdrf.CommonDataElement']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_questionnaire': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_questionnaire_login': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'questionnaire_questions': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'registry': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rdrf.Registry']"}),
            'sections': ('django.db.models.fields.TextField', [], {})
        },
        u'rdrf.section': {
            'Meta': {'object_name': 'Section'},
            'allow_multiple': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'elements': ('django.db.models.fields.TextField', [], {}),
            'extra': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'questionnaire_display_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'questionnaire_help': ('django.db.models.fields.TextField', [], {'blank': 'True'})
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