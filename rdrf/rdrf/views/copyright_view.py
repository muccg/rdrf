from django.shortcuts import render
from django.views.generic.base import View
from rdrf.models.definition.models import Registry
from rdrf.models.proms.models import Survey


import logging

logger = logging.getLogger(__name__)

class CopyrightView(View):
    
    def get(self, request):
        registry_models = Registry.objects.all()
        copyright_texts = set([])
        # get all surveys and survey questions

        for registry in registry_models:
            for survey_model in Survey.objects.filter(registry=registry):
                for survey_question in survey_model.survey_questions.all():
                    if survey_question.copyright_text is not None:
                        copyright_texts.add(survey_question.copyright_text)

        context = {
            "copyright_texts": copyright_texts,
        }
        return render(request, "rdrf_cdes/copyright.html", context)
    