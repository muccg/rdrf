from django.core.urlresolvers import reverse
from django.templatetags.static import static
from django.template import loader, Context
from django.utils.html import escape


class ContextMenuForm(object):
    def __init__(self, title, link, progress_percentage=0):
        self.title = title
        self.link = link
        self.progress_percentage = progress_percentage


class ContextMenuAction(object):
    def __init__(self, title, id):
        self.title = title
        self.id = id


class PatientContextMenu(object):
    def __init__(self, user, registry_model, patient_model, context_model=None):
        """
        :param user: relative to user looking
        :param patient_model:
        :param registry_model:
        :param context_model:
        :return:
        """
        self.user = user
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.context_model = context_model
        self.context_name = self._get_context_name()

    def _get_context_name(self):
        if self.registry_model.has_feature("contexts"):
            try:
                name = self.registry_model.metadata["context_name"]
            except KeyError:
                name = "Context"
        else:
            name = ""

        return name



    @property
    def html(self):
        patient_edit_link = self.get_patient_edit_link()
        #form_progress = self.get_form_progress()
        #action_buttons = self.get_actions()
        #return patient_edit_link
        return patient_edit_link + self.menu_html

    def get_patient_edit_link(self):
        registry_code = self.registry_model.code
        return "<a href='%s'>%s</a>" % \
               (reverse("patient_edit",
                        kwargs={"registry_code": registry_code,
                                "patient_id": self.patient_model.id}),
                self.patient_model.display_name)

    @property
    def menu_html(self):
        popup_template = "rdrf_cdes/patient_context_popup.html"
        forms = [ContextMenuForm("testing", "http://www.smh.com.au",66),
                 ContextMenuForm("stuff", "http://www.smh.com.au",88),
                 ]




        actions = [ContextMenuAction("Add Assessment", "test"), ContextMenuAction("Add Something else", "ggg")]


        popup_template = loader.get_template(popup_template)
        context = Context({"forms": forms,
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

    def popup(self):
        from rdrf.models import RegistryForm

        registry_code = self.registry_model.code
        if self.patient_model.rdrf_registry.count() == 0:
            return "No registry assigned"


        def nice_name(name):
            try:
                return de_camelcase(name)
            except:
                return name

        if self.registry_model is None:
            return "Filter registry first!"

        def not_generated(frm):
            return not frm.name.startswith(self.registry_model.generated_questionnaire_name)

        forms = [
            f for f in RegistryForm.objects.filter(
                registry=self.registry_model).order_by('position') if not_generated(f) and self.user.can_view(f)]

        content = ''

        if not forms:
            content = _("No modules available")

        content += "<a href=%s>Consents</a><br>" % reverse("consent_form_view", args=(registry_code, self.patient_model.id))

        for form in forms:
            if form.is_questionnaire:
                continue
            is_current = self.patient_model.form_currency(form)
            flag = "images/%s.png" % ("tick" if is_current else "cross")

            url = reverse(
                'registry_form', args=(self.registry_model.code, form.id, self.patient_model.id))
            link = "<a href=%s>%s</a>" % (url, nice_name(form.name))
            label = nice_name(form.name)

            to_form = link
            if self.user.is_working_group_staff:
                to_form = label

            if form.has_progress_indicator:
                content += "<img src=%s> <strong>%d%%</strong> %s</br>" % (
                    static(flag), self.patient_model.form_progress(form)[1], to_form)
            else:
                content += "<img src=%s> %s</br>" % (static(flag), to_form)

        return "<button type='button' class='btn btn-primary btn-xs' data-toggle='popover' data-content='%s' id='data-modules-btn'>Show</button>" % content
