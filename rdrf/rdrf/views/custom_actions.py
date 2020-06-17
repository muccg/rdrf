from datetime import datetime
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.views.generic.base import View
from django.template.context_processors import csrf
from django.http import Http404
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from rdrf.models.definition.models import CustomAction
from rdrf.models.task_models import CustomActionExecution
from registry.patients.models import Patient
import logging

logger = logging.getLogger(__name__)


def task_check(user, task_id):
    # todo fix this
    return True


class CustomActionView(View):
    @method_decorator(login_required)
    def get(self, request, action_id, patient_id):
        # user has clicked on a custom action link
        user = request.user
        custom_action = get_object_or_404(CustomAction, id=action_id)

        # this model acts as an audit trail
        cae = CustomActionExecution()
        cae.user = user
        cae.custom_action = custom_action
        cae.name = custom_action.name
        cae.status = "started"

        requires_patient = custom_action.scope == "P"
        requires_gui = custom_action.requires_input
        is_asynchronous = custom_action.asynchronous

        if requires_patient:
            logger.debug("action requires patient")
            patient_model = get_object_or_404(Patient, id=patient_id)
        else:
            logger.debug("action does not require patient")
            patient_model = None

        cae.patient = patient_model
        cae.save()

        if requires_gui:
            cae.status = "awaiting input"
            cae.save()
            return self._generate_gui(request, custom_action, cae)
        elif is_asynchronous:
            cae.status = "polling"
            cae.save()
            return self._polling_view(request,
                                      user,
                                      custom_action,
                                      patient_model,
                                      cae)
        else:
            cae.status = "running sync"
            cae.save()
            start_time = datetime.now()
            try:
                response = custom_action.execute(user, patient_model)
            except Exception as ex:
                cae.error_string = str(ex)
                cae.status = "error"
                cae.save()
                logger.error("Error custom action cae %s: %s" % (cae.id,
                                                                 ex))
                raise

            finish_time = datetime.now()
            seconds = (finish_time - start_time).seconds
            cae.runtime = seconds
            cae.status = "finished"
            cae.save()
            return response

    def _generate_gui(self,
                      request,
                      custom_action,
                      cae):
        input_form = custom_action.input_form_class(initial={"cae": cae.id})
        template_context = {
            "custom_action": custom_action,
            "input_form": input_form,
        }
        template_context.update(csrf(request))
        template = "rdrf_cdes/custom_action_input_form.html"
        return render(request, template, template_context)

    @method_decorator(login_required)
    def post(self, request, action_id, patient_id):
        cae = CustomActionExecution.objects.get(id=int(request.POST["cae"]))
        logger.debug("tracking cae = %s" % cae.id)
        cae.status = "received input"
        cae.save()

        user = request.user
        custom_action = get_object_or_404(CustomAction, id=action_id)
        if not custom_action.requires_input:
            raise Http404

        if custom_action.scope == "P":
            patient_model = get_object_or_404(Patient, id=patient_id)
        else:
            patient_model = None

        input_form = custom_action.input_form_class(request.POST)
        if not input_form.is_valid():
            cae.status = "invalid input"
            cae.save()
            raise Exception("not valid")
        input_data = input_form.cleaned_data
        cae.input_data = str(input_data)
        cae.save()

        # execute async
        if custom_action.asynchronous:
            logger.debug("running async task ...")
            task_id = custom_action.run_async(user, patient_model, input_data)
            cae.task_id = task_id
            cae.status = "started task"
            cae.save()
            logger.debug("task id = %s" % task_id)
            return self._polling_view(request,
                                      user,
                                      custom_action,
                                      task_id,
                                      patient_model)

        else:
            cae.status = "start sync"
            cae.save()
            try:
                start_time = datetime.now()
                try:
                    response = custom_action.execute(user, patient_model, input_data)
                except Exception as ex:
                    cae.status = "error"
                    cae.error_string = str(ex)
                    cae.save()
                    logger.error("Error running cae %s: %s" % (cae.id,
                                                               ex))
                    raise

                finish_time = datetime.now()
                seconds = (finish_time - start_time).seconds
                cae.runtime = seconds
                cae.status = "finished"
                cae.save()
                return response

            except Exception as ex:
                cae.status = "error"
                cae.error_string = str(ex)
                cae.save()
                logger.error("Error running cae %s: %s" % (cae.id,
                                                           ex))
                raise

    def _polling_view(self,
                      request,
                      user,
                      custom_action,
                      task_id,
                      patient_model=None,
                      cae=None):
        logger.debug("constructing polling page ...")
        if not task_check(user, task_id):
            raise Http404

        logger.debug("task check passed ...")

        template = "rdrf_cdes/custom_action_polling.html"
        task_api_url = reverse("v1:task-list", args=[task_id])

        template_context = {"task_api_url": task_api_url,
                            "cae": cae,
                            "task_id": task_id,
                            "patient_model": patient_model,
                            "custom_action": custom_action,
                            "user": user}

        logger.debug("template context = %s" % template_context)

        template_context.update(csrf(request))
        logger.debug("rendering the polling template ...")
        return render(request, template, template_context)


class CustomActionWrapper:
    """
    Used to construct action links
    """

    def __init__(self, registry, user, custom_action, patient_model):
        self.registry = registry
        self.user = user
        self.custom_action = custom_action
        self.patient_model = patient_model
        self.valid = self._check_validity()

    @property
    def url(self):
        if self.valid:
            from django.urls import reverse
            return reverse("custom_action", args=[self.custom_action.pk,
                                                  self.patient_model.pk])
        else:
            logger.debug("not valid")
            return ""

    @property
    def text(self):
        return self.custom_action.text

    def _check_validity(self):
        return self.custom_action.check_security(self.user,
                                                 self.patient_model)
