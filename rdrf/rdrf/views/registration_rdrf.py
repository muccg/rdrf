from django.shortcuts import redirect
from django.urls import reverse
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, get_object_or_404
from registration.backends.default.views import RegistrationView
from rdrf.models.definition.models import Registry
from rdrf.workflows.registration import get_registration_workflow
import logging


logger = logging.getLogger(__name__)


class RdrfRegistrationView(RegistrationView):

    registry_code = None

    def get(self, request, *args, **kwargs):
        try:
            get_object_or_404(Registry, code=kwargs['registry_code'])
        except Registry.DoesNotExist:
            raise Http404

        self.registry_code = kwargs['registry_code']
        workflow = None
        token = request.GET.get("t", None)
        if token:
            workflow = get_registration_workflow(token)
            if workflow:
                request.session["token"] = token
                self.template_name = workflow.get_template()

        form_class = self.get_form_class()
        form = self.get_form(form_class)
        context = self.get_context_data(form=form)
        context["is_mobile"] = request.user_agent.is_mobile
        if workflow:
            context["username"] = workflow.username
            context["first_name"] = workflow.first_name
            context["last_name"] = workflow.last_name

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        token = request.session.get("token", None)
        # TODO: confirm we run this following line for checking (it does not seem the case -
        # that may be some old code we forgot to remove)
        get_registration_workflow(token)
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            return self.form_valid(form)
        else:
            logger.warning(f"Backend validation of the registration has failed: {form.errors.get_json_data()}")
            context = self.get_context_data(form=form)
            context['registry_code'] = request.POST.get('registry_code', '')
            return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        context = super(RdrfRegistrationView, self).get_context_data(**kwargs)
        context['registry_code'] = self.registry_code
        context["preferred_languages"] = self._get_preferred_languages()
        return context

    def _get_preferred_languages(self):
        # Registration allows choice of preferred language
        # But we allow different sites to expose different values
        # over time without code change via env --> settings

        # The default list is english only which we don't bother to show
        from rdrf.helpers.utils import get_supported_languages
        languages = get_supported_languages()

        if len(languages) == 1 and languages[0].code == "en":
            return []
        else:
            return languages

    def form_valid(self, form):
        # this is only for user validation
        # if any validation errors occur server side
        # on related object creation in signal handler occur
        # we roll back here
        failure_url = reverse("registration_failed")
        username = None
        with transaction.atomic():
            try:
                new_user = self.register(form)
                username = new_user.username
                success_url = self.get_success_url(new_user)
            except Exception as ex:
                logger.error("Unhandled error in registration for user %s: %s" % (username,
                                                                                  ex))
                return redirect(failure_url)

        try:
            to, args, kwargs = success_url
        except ValueError:
            return redirect(success_url)
        else:
            return redirect(to, *args, **kwargs)
