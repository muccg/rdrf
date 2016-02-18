from django.core.urlresolvers import reverse
from django.templatetags.static import static
from django.template import loader, Context
from django.utils.html import escape
from rdrf.models import RegistryForm

from rdrf.form_progress import FormProgress

# NB "Context" is not the same as RDRF Context, it's just a "normal" context menu that pops up


class ContextMenuForm(object):
    def __init__(self, title, link, progress_percentage=0, currency=False):
        self.title = title
        self.link = link
        self.progress_percentage = progress_percentage
        self.current = currency


class ContextMenuAction(object):
    def __init__(self, title, link):
        self.title = title
        self.id = id
        self.link = link


class PatientContextMenu(object):
    def __init__(self, user, registry_model, form_progress, patient_model, context_model=None):
        """
        :param user: relative to user looking
        :param patient_model:
        :param registry_model:
        :param context_model: the rdrf context model
        :return:
        """
        self.user = user
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.context_model = context_model
        self.form_progress = form_progress
        self.context_name = self._get_context_name()

    def _get_context_name(self):
        if self.registry_model.has_feature("contexts"):
            try:
                name = self.context_model.context_name
            except Exception:
                name = "Context"
        else:
            name = "Context"

        return name

    def get_context_menu_forms(self):
        context_menu_forms = []
        self.form_progress.reset()
        for form in self.get_forms():
            form_name = form.nice_name
            form_link = form.get_link(self.patient_model, self.context_model)
            progress_percentage = self.form_progress.get_form_progress(form, self.patient_model, self.context_model)
            currency = self.form_progress.get_form_currency(form, self.patient_model, self.context_model)
            context_menu_forms.append(ContextMenuForm(form_name, form_link, progress_percentage, currency))
        return context_menu_forms

    def get_patient_edit_link(self):
        registry_code = self.registry_model.code
        return "<a href='%s'>%s</a>" % \
               (reverse("patient_edit",
                        kwargs={"registry_code": registry_code,
                                "patient_id": self.patient_model.id,
                                "context_id": self.context_model.pk}),
                self.patient_model.display_name)

    @property
    def menu_html(self):
        popup_template = "rdrf_cdes/patient_context_popup.html"
        forms = self.get_context_menu_forms()
        actions = []

        add_context_title = "Add %s" % self.context_name
        add_context_link = reverse("context_add", args=(self.registry_model.code, str(self.patient_model.pk)))
        add_context_action = ContextMenuAction(add_context_title, add_context_link)

        actions.append(add_context_action)

        popup_template = loader.get_template(popup_template)
        context = Context({"forms": forms,
                           "supports_contexts": self.registry_model.has_feature("contexts"),
                           "context_name": self.context_name,
                           "actions": actions,
                           "context": self.context_model,
                           "patient": self.patient_model})

        popup_content_html = popup_template.render(context)
        button_html = """<button type="button"
                          class="contextmenu btn btn-primary btn-xs"
                          data-toggle="popover"
                          data-html="true"
                          data-content="%s"
                          id="patientcontextmenu"
                          data-original-title=""
                          title=""
                          aria-describedby="">Show</button>""" % escape(popup_content_html)

        return button_html

    def get_forms(self):
        def not_generated(frm):
            return not frm.name.startswith(self.registry_model.generated_questionnaire_name)

        if not self.context_model.context_form_group:
            forms = [
            f for f in RegistryForm.objects.filter(
                registry=self.registry_model).order_by('position') if not_generated(f) and self.user.can_view(f)]
        else:
            forms = [ f for f in self.context_model.context_form_group.forms
                      if not_generated(f)
                      and self.user.can_view(f)]
            
        return forms
