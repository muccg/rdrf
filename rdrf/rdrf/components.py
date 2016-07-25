from django.template import loader, Context
from rdrf.models import RegistryType, RDRFContext, ContextFormGroup
from django.contrib.contenttypes.models import ContentType
from rdrf.utils import get_form_links
from rdrf.utils import consent_status_for_patient
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
import logging

logger = logging.getLogger("registry_log")

class Link(object):
    def __init__(self, url, text, current):
        self.url = url
        self.text = text
        self.current = current
        

        
class LauncherError(Exception):
    pass

class _Form(object):
    def __init__(self, url, text, current=False, add_link_url=None, add_link_text=None):
        self.id = None
        self.url = url
        self.text = text
        self.current = current
        self.add_link_url = add_link_url
        self.add_link_text = add_link_text
        self.heading = ""
        self.existing_links = [] # for multiple contexts
        

    def __unicode__(self):
        return "Form %s %s %s" % (self.text, self.url, self.current)


class _FormGroup(object):
    def __init__(self, name):
        self.name = name
        self.forms = []


class RDRFComponent(object):
    TEMPLATE = ""

    @property
    def html(self):
        return self._fill_template()

    def _fill_template(self):
        if not self.TEMPLATE:
            raise NotImplementedError("need to supply template")
        else:
            template = loader.get_template(self.TEMPLATE)
            data = self._get_template_data()
            context = Context(data)
            return template.render(context)

    def _get_template_data(self):
        # subclass should build dictionary for template
        return {}


class RDRFContextLauncherComponent(RDRFComponent):
    TEMPLATE = "rdrf_cdes/rdrfcontext_launcher.html"

    def __init__(self,
                 user,
                 registry_model,
                 patient_model,
                 current_form_name="Demographics",
                 current_rdrf_context_model=None):
        self.user = user
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.current_form_name = current_form_name
        self.content_type = ContentType.objects.get(model='patient')
        # below only used when navigating to form in a context
        # associated with a multiple context form group
        self.current_rdrf_context_model = current_rdrf_context_model
        self.consent_locked = self._is_consent_locked()

    def _get_template_data(self):
        existing_data_link = self._get_existing_data_link()

        return {
            "current_form_name" : self.current_form_name,
            "patient_listing_link": existing_data_link,
            "actions": self._get_actions(),
            "fixed_contexts": self._get_fixed_contexts(),
            "multiple_contexts": self._get_multiple_contexts(),
            "current_multiple_context": self._get_current_multiple_context(),
            "demographics_link": self._get_demographics_link(),
            "consents_link" : self._get_consents_link(),
            "family_linkage_link" : self._get_family_linkage_link(),
            "consent_locked" : self.consent_locked,
            }

    def _is_consent_locked(self):
        if self.registry_model.has_feature("consent_lock"):
            return not consent_status_for_patient(self.registry_model.code,
                                              self.patient_model)
        else:
            return False

    def _get_consents_link(self):
        return reverse("consent_form_view", args=[self.registry_model.code, self.patient_model.pk])

    def _get_demographics_link(self):
        return reverse("patient_edit", args=[self.registry_model.code, self.patient_model.pk])


    def _get_family_linkage_link(self):
        if self.registry_model.has_feature("family_linkage"):
            registry_code = self.registry_model.code
            if self.patient_model.is_index:
                family_linkage_link = reverse('family_linkage', args=(registry_code,
                                                                      self.patient_model.pk))
            else:
                family_linkage_link = reverse('family_linkage', args=(registry_code,
                                                                      self.patient_model.my_index.pk))
            return family_linkage_link
        else:
            return None

    def _get_existing_data_link(self):
        if self.registry_model.registry_type == RegistryType.NORMAL:
            # No need
            return None
        return self.patient_model.get_contexts_url(self.registry_model)

    def _get_actions(self):
        from rdrf.context_menu import PatientContextMenu
        patient_context_menu = PatientContextMenu(self.user,
                                                  self.registry_model,
                                                  None,
                                                  self.patient_model)

        return patient_context_menu.actions


    def _get_multiple_contexts(self):
        return []
        # provide links to filtered view of the existing data
        # reuses the patient/context listing
        contexts_listing_url = reverse("contextslisting")
        links = []
        for context_form_group in ContextFormGroup.objects.filter(registry=self.registry_model,
                                                                  context_type="M").order_by("name"):
            name = _("All " + context_form_group.direct_name + "s") 
            filter_url = contexts_listing_url + "?registry_code=%s&patient_id=%s&context_form_group_id=%s" % (self.registry_model.code,
                                                                                                              self.patient_model.pk,
                                                                                                              context_form_group.pk)


             
            
            link_pair  = context_form_group.get_add_action(self.patient_model)
            if link_pair:
                add_link_url, add_link_text = link_pair
                form = _Form(filter_url,
                                   name,
                                   add_link_url=add_link_url,
                                   add_link_text=add_link_text)
                
                form.heading = _(context_form_group.direct_name + "s")
                form.id = context_form_group.pk
                form.existing_links = self._get_existing_links(context_form_group)
                links.append(form)
                
                          
        return links

    def _get_existing_links(self, context_form_group):
        links = []
        def is_current(url):
            parts = url.split("/")
            context_id = int(parts[-1])
            if self.current_rdrf_context_model:
                return context_id == self.current_rdrf_context_model.pk
            else:
                return False
        
        for url, text in self.patient_model.get_forms_by_group(context_form_group):
            link_obj = Link(url, text, is_current(url))
            links.append(link_obj)
        return links
    

    def _get_current_multiple_context(self):
        #def get_form_links(user, patient_id, registry_model, context_model=None, current_form_name=""):
        # provide links to other forms in this current context
        # used when landing on a form in multiple context
        registry_type = self.registry_model.registry_type
        fg = None
        if registry_type == RegistryType.HAS_CONTEXT_GROUPS:
            if self.current_rdrf_context_model and self.current_rdrf_context_model.context_form_group:
                cfg = self.current_rdrf_context_model.context_form_group
                if cfg.context_type == "M":
                    fg = _FormGroup(self.current_rdrf_context_model.display_name)
                    for form_link in get_form_links(self.user,
                                                    self.patient_model.pk,
                                                    self.registry_model,
                                                    self.current_rdrf_context_model,
                                                    self.current_form_name):
                       form = _Form(form_link.url,
                                    form_link.text,
                                    current=form_link.selected)
                       fg.forms.append(form)
        return fg
                        
                    
                    



    def _get_fixed_contexts(self):
        # We can provide direct links to forms in these contexts as they
        # will be created on patient creation
        fixed_contexts = []
        registry_type = self.registry_model.registry_type
        if registry_type == RegistryType.NORMAL:
            # just show all the forms
            fg = _FormGroup("Modules")
            for form_link in self._get_normal_form_links():
                form = _Form(form_link.url, form_link.text, current=form_link.selected)
                fg.forms.append(form)
                logger.debug("added %s" % form)
            return [fg]
        elif registry_type == RegistryType.HAS_CONTEXTS:
            # nothing to show here
            return []
        else:
            # has context form groups , display form links for each "fixed" context
            for fixed_context_group in self._get_fixed_context_form_groups():
                rdrf_context = self._get_context_for_group(fixed_context_group)
                fg = _FormGroup(fixed_context_group.name)
                for form_link in self._get_visible_form_links(fixed_context_group, rdrf_context):
                    form = _Form(form_link.url, form_link.text, current=form_link.selected)
                    fg.forms.append(form)
                fixed_contexts.append(fg)
            return fixed_contexts

    def _get_normal_form_links(self):
        default_context = self.patient_model.default_context(self.registry_model)
        if default_context is None:
            raise LauncherError("Expected a default context for patient")
        else:
            return get_form_links(self.user,
                                  self.patient_model.id,
                                  self.registry_model,
                                  default_context,
                                  self.current_form_name)

    def _get_visible_form_links(self, fixed_context_group, rdrf_context):
        return get_form_links(self.user,
                              self.patient_model.id,
                              self.registry_model,
                              rdrf_context,
                              self.current_form_name)

    def _get_fixed_context_form_groups(self):
        return ContextFormGroup.objects.filter(registry=self.registry_model,
                                               context_type="F")

    def _get_context_for_group(self, fixed_context_form_group):
        try:
            rdrf_context = RDRFContext.objects.get(registry=self.registry_model,
                                                   context_form_group=fixed_context_form_group,
                                                   object_id=self.patient_model.pk,
                                                   content_type=self.content_type)
            return rdrf_context
        except RDRFContext.DoesNotExist:
            return None
