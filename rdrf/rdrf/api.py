from registry.patients.models import Patient
from registry.groups.models import WorkingGroup
from rdrf.models import Registry, RegistryForm
from rdrf.utils import de_camelcase
from rdrf.form_progress import FormProgress

from django.conf.urls import url
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.core.urlresolvers import reverse
from django.templatetags.static import static

from tastypie.serializers import Serializer
from tastypie.authorization import DjangoAuthorization
from tastypie.utils import trailing_slash
from tastypie.resources import ModelResource
from tastypie import fields

import urlparse
import time
import logging

logger = logging.getLogger("registry_log")


class UrlEncodeSerializer(Serializer):
    formats = ['json', 'jsonp', 'xml', 'yaml', 'html', 'plist', 'urlencode']
    content_types = {
        'json': 'application/json',
        'jsonp': 'text/javascript',
        'xml': 'application/xml',
        'yaml': 'text/yaml',
        'html': 'text/html',
        'plist': 'application/x-plist',
        'urlencode': 'application/x-www-form-urlencoded',
    }

    def from_urlencode(self, data, options=None):
        """ handles basic formencoded url posts """
        qs = dict((k, v if len(v) > 1 else v[0])
                  for k, v in urlparse.parse_qs(data).iteritems())
        return qs

    def to_urlencode(self, content):
        pass


class WorkingGroupResource(ModelResource):
    name = fields.CharField(attribute='name')

    class Meta:
        queryset = WorkingGroup.objects.all()


class PatientResource(ModelResource):
    working_groups = fields.ToManyField(WorkingGroupResource, 'working_groups')

    class Meta:
        queryset = Patient.objects.all()
        serializer = UrlEncodeSerializer()
        authorization = DjangoAuthorization()

    def dehydrate(self, bundle):
        start = time.time()
        id = int(bundle.data['id'])
        p = Patient.objects.get(id=id)
        registry_code = bundle.request.GET.get("registry_code", "")
        registry_model = Registry.objects.get(code=registry_code)

        form_progress = getattr(bundle, "form_progress")
        form_progress.reset()

        bundle.data["working_groups_display"] = p.working_groups_display
        bundle.data["reg_list"] = self._get_reg_list(p, bundle.request.user)
        if bundle.request.user.is_superuser:
            bundle.data["reg_code"] = [reg.code for reg in Registry.objects.all()]
        else:
            bundle.data["reg_code"] = [reg.code for reg in bundle.request.user.registry.all()]

        if registry_code:
            bundle.data["full_name"] = "<a href='%s'>%s</a>" % (reverse("patient_edit",
                                                                        kwargs={"registry_code": registry_code,
                                                                                "patient_id": p.id}), p.display_name)
        else:
            # calls from calculated field plugin don't pass a registry code
            bundle.data["full_name"] = p.display_name

        bundle.data["diagnosis_progress"] = self._set_diagnosis_progress(form_progress, p)
        bundle.data["has_genetic_data"] = self._set_has_genetic_data(form_progress, p)
        #bundle.data["genetic_data_map"] = self._set_genetic_data(form_progress, p)

        logger.debug("calculating data modules for patient %s" % id)
        bundle.data["data_modules"] = self._set_data_modules(form_progress, p, bundle.request.user)
        bundle.data["diagnosis_currency"] = self._set_diagnosis_currency(form_progress, p)

        finish = time.time()
        elapsed = finish - start
        logger.debug("dehydrate took %s" % elapsed)

        return bundle

    def _set_diagnosis_progress(self, form_progress, patient_model):
        progress_number = form_progress.get_group_progress("diagnosis", patient_model)
        return "<div class='progress'><div class='progress-bar progress-bar-custom' role='progressbar' aria-valuenow='%s' aria-valuemin='0' aria-valuemax='100' style='width: %s%%'><span class='progress-label'>%s%%</span></div></div>" % (progress_number, progress_number, progress_number)

    def _set_has_genetic_data(self, form_progress, patient_model):
        has_genetic_data = form_progress.get_group_has_data("genetic", patient_model)
        icon = "ok" if has_genetic_data else "remove"
        color = "green" if has_genetic_data else "red"
        return "<span class='glyphicon glyphicon-%s' style='color:%s'></span>" % (icon, color)

    def _set_data_modules(self, form_progress, patient_model, user):
        return form_progress.get_data_modules(user, patient_model)

    def _set_diagnosis_currency(self, form_progress, patient_model):
        diagnosis_currency = form_progress.get_group_currency("diagnosis", patient_model)
        icon = "ok" if diagnosis_currency else "remove"
        color = "green" if diagnosis_currency else "red"
        return "<span class='glyphicon glyphicon-%s' style='color:%s'></span>" % (icon, color)

    def _get_reg_list(self, patient, user):
        if user.is_superuser:
            return patient.get_reg_list()
        regs = []
        for patient_registry in patient.rdrf_registry.all():
            if patient_registry in user.registry.all():
                regs.append(patient_registry.name)
        return ", ".join(regs)

    def _get_data_modules(self, patient_model, registry_code, user):
        if patient_model.rdrf_registry.count() == 0:
            return "No registry assigned"

        if not registry_code:
            if user.registry.count() == 1:
                registry_model = user.registry.get()
            else:
                registry_model = None    # user must filter registry first
        else:
            registry_model = Registry.objects.get(code=registry_code)

        def nice_name(name):
            try:
                return de_camelcase(name)
            except:
                return name

        if registry_model is None:
            return "Filter registry first!"

        def not_generated(frm):
            return not frm.name.startswith(registry_model.generated_questionnaire_name)

        forms = [
            f for f in RegistryForm.objects.filter(
                registry=registry_model).order_by('position') if not_generated(f) and user.can_view(f)]

        content = ''

        if not forms:
            content = _("No modules available")
        
        content += "<a href=%s>Consents</a><br>" % reverse("consent_form_view", args=(registry_code, patient_model.id))

        for form in forms:
            if form.is_questionnaire:
                continue
            is_current = patient_model.form_currency(form)
            flag = "images/%s.png" % ("tick" if is_current else "cross")

            url = reverse(
                'registry_form', args=(registry_model.code, form.id, patient_model.id))
            link = "<a href=%s>%s</a>" % (url, nice_name(form.name))
            label = nice_name(form.name)

            to_form = link
            if user.is_working_group_staff:
                to_form = label

            if form.has_progress_indicator:
                content += "<img src=%s> <strong>%d%%</strong> %s</br>" % (
                    static(flag), patient_model.form_progress(form)[1], to_form)
            else:
                content += "<img src=%s> %s</br>" % (static(flag), to_form)

        return "<button type='button' class='btn btn-primary btn-xs' data-toggle='popover' data-content='%s' id='data-modules-btn'>Show</button>" % content

    # https://django-tastypie.readthedocs.org/en/latest/cookbook.html#adding-search-functionality
    def prepend_urls(self):
        return [url(r"^(?P<resource_name>%s)/search%s$" % (self._meta.resource_name,
                                                           trailing_slash()),
                    self.wrap_view('get_search'),
                    name="api_get_search"),
                ]

    def get_search(self, request, **kwargs):
        from django.db.models import Q
        logger.debug("get_search request.GET = %s" % request.GET)
        chosen_registry_code = request.GET.get("registry_code", None)

        if chosen_registry_code:
            try:
                chosen_registry = Registry.objects.get(code=chosen_registry_code)
            except Registry.DoesNotExist:
                chosen_registry = None

        else:
            chosen_registry = None

        if chosen_registry:
            registry_queryset = [chosen_registry]
        else:

            if request.user.num_registries == 1:
                chosen_registry = request.user.registry.get()
                registry_queryset = [chosen_registry]
                chosen_registry_code = chosen_registry.code
            else:
                registry_queryset = []

        if chosen_registry:
            clinicians_have_patients = chosen_registry.has_feature("clinicians_have_patients")
        else:
            clinicians_have_patients = False

        patients = Patient.objects.all()

        form_progress = FormProgress(chosen_registry)

        if not request.user.is_superuser:
            if request.user.is_curator:
                query_patients = Q(rdrf_registry__in=registry_queryset) & Q(
                    working_groups__in=request.user.working_groups.all())
                patients = patients.filter(query_patients)
            elif request.user.is_genetic_staff:
                # unclear what to do here
                patients = patients.filter(working_groups__in=request.user.working_groups.all())
            elif request.user.is_genetic_curator:
                # unclear what to do here
                patients = patients.filter(working_groups__in=request.user.working_groups.all())
            elif request.user.is_working_group_staff:
                # unclear what to do here
                patients = patients.filter(working_groups__in=request.user.working_groups.all())
            elif request.user.is_clinician and clinicians_have_patients:
                patients = patients.filter(clinician=request.user)
            elif request.user.is_clinician and not clinicians_have_patients:
                query_patients = Q(rdrf_registry__in=registry_queryset) & Q(
                    working_groups__in=request.user.working_groups.all())
                patients = patients.filter(query_patients)
            elif request.user.is_patient:
                patients = patients.filter(user=request.user)
            else:
                patients = patients.none()
        else:

            patients = patients.filter(rdrf_registry__in=registry_queryset)

        # ] request.GET = <QueryDict: {u'current': [u'1'], u'rowCount': [u'10'], u'searchPhrase': [u'ffff']}>

        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        row_count = int(request.GET.get('rowCcount', 20))
        logger.debug("row count = %s" % row_count)
        search_phrase = request.GET.get("searchPhrase", None)
        current = int(request.GET.get("current", 1))
        sort_field, sort_direction = self._get_sorting(request)

        # Do the query.

        query_set = patients

        if sort_field and sort_direction:
            if sort_direction == "desc":
                sort_field = "-" + sort_field
            query_set = query_set.order_by(sort_field)
            logger.debug("sort field = %s" % sort_field)

        if search_phrase:
            from django.db.models import Q
            query_set = query_set.filter(
                Q(given_names__icontains=search_phrase) | Q(family_name__icontains=search_phrase))

        total = query_set.count()

        if total == 0:
            # No patients found
            results = {
                "current": 1,
                "rowCount": 0,
                "searchPhrase": search_phrase,
                "rows": [],
                "total": total,
                "show_add_patient": not chosen_registry.has_feature("no_add_patient_button"),
            }
            self.log_throttled_access(request)
            return self.create_response(request, results)

        if row_count == -1:
            # All
            row_count = total

        paginator = Paginator(query_set, row_count)

        try:
            page = paginator.page(current)
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []

        logger.debug("reg code = %s" % chosen_registry_code)
        logger.debug("user = %s" % request.user)

        for result in page.object_list:
            bundle = self.build_bundle(obj=result, request=request)
            setattr(bundle, "form_progress", form_progress)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)

        # Adapt the results to fit what jquery bootgrid expects

        results = {
            "current": current,
            "rowCount": row_count,
            "searchPhrase": search_phrase,
            "rows": objects,
            "total": total,
            "show_add_patient": not chosen_registry.has_feature("no_add_patient_button"),
        }

        self.log_throttled_access(request)
        return self.create_response(request, results)

    def _get_sorting(self, request):
        # boot grid uses this convention
        # sort[given_names]': [u'desc']
        for k in request.GET:
            if k.startswith("sort["):
                import re
                pattern = re.compile(r'^sort\[(.*?)\]$')
                m = pattern.match(k)
                if m:
                    sort_field = m.groups(1)[0]
                    sort_direction = request.GET.get(k)
                    return sort_field, sort_direction

        return None, None
