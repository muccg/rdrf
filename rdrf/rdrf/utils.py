from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db import transaction
from django.utils.html import strip_tags
from django.utils.encoding import smart_bytes
from functools import total_ordering
from copy import deepcopy

import datetime
import dateutil.parser
import logging
import re
import os.path
import subprocess

logger = logging.getLogger(__name__)


class BadKeyError(Exception):
    pass


def get_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)[-1]


def get_form_section_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)


def mongo_key(form_name, section_code, cde_code):
    return settings.FORM_SECTION_DELIMITER.join([form_name, section_code, cde_code])


def mongo_key_from_models(form_model, section_model, cde_model):
    return mongo_key(form_model.name, section_model.code, cde_model.code)


def models_from_mongo_key(registry_model, delimited_key):
    from rdrf.models import RegistryForm, Section, CommonDataElement
    form_name, section_code, cde_code = get_form_section_code(delimited_key)
    try:
        form_model = RegistryForm.objects.get(name=form_name, registry=registry_model)
    except RegistryForm.DoesNotExist:
        raise BadKeyError()

    try:
        section_model = Section.objects.get(code=section_code)
    except Section.DoesNotExist:
        raise BadKeyError()

    try:
        cde_model = CommonDataElement.objects.get(code=cde_code)
    except CommonDataElement.DoesNotExist:
        raise BadKeyError()

    return form_model, section_model, cde_model


def is_delimited_key(s):
    try:
        parts = s.split(settings.FORM_SECTION_DELIMITER)
        if len(parts) == 3:
            return True
    except Exception:
        pass
    return False


def id_on_page(registry_form_model, section_model, cde_model):
    return mongo_key(registry_form_model.name, section_model.code, cde_model.code)


def de_camelcase(s):
    value = s[0].upper() + s[1:]
    chunks = re.findall('[A-Z][^A-Z]*', value)
    return " ".join(chunks)


class FormLink(object):

    def __init__(self, patient_id, registry, registry_form, selected=False, context_model=None):
        self.registry = registry
        self.patient_id = patient_id
        self.form = registry_form
        self.selected = selected
        self.context_model = context_model

    @property
    def url(self):
        from django.core.urlresolvers import reverse
        if self.context_model is None:
            return reverse(
                'registry_form',
                args=(
                    self.registry.code,
                    self.form.pk,
                    self.patient_id))
        else:
            return reverse(
                'registry_form',
                args=(
                    self.registry.code,
                    self.form.pk,
                    self.patient_id,
                    self.context_model.id))

    @property
    def text(self):
        return de_camelcase(self.form.name)


def get_user(username):
    from registry.groups.models import CustomUser
    try:
        return CustomUser.objects.get(username=username)
    except CustomUser.DoesNotExist:
        return None


def get_users(usernames):
    return [x for x in [get_user(username) for username in usernames] if x is not None]


def get_full_link(request, partial_link, login_link=False):
    if login_link:
        # return a redirect login    https://rdrf.ccgapps.com.au/ophg/login?next=/ophg/admin/
        login_url = "/login?next=" + partial_link
        return get_site_url(request, login_url)
    else:
        return get_site_url(request, partial_link)


def get_site_url(request, path="/"):
    # https://rdrf.ccgapps.com.au/ophg/admin/patients/patient/3/
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # this part !
    return request.build_absolute_uri(path)


def location_name(registry_form, current_rdrf_context_model=None):
    form_display_name = de_camelcase(registry_form.name)
    context_form_group = None
    if registry_form.registry.has_feature("contexts"):
        if current_rdrf_context_model is not None:
            registry_model = registry_form.registry
            patient_model = current_rdrf_context_model.content_object
            context_form_group = current_rdrf_context_model.context_form_group
            if context_form_group is not None:
                # context type name
                if context_form_group.naming_scheme == "C":
                    context_type_name = context_form_group.get_name_from_cde(patient_model, current_rdrf_context_model)
                    if context_form_group.supports_direct_linking:
                        return form_display_name + "/" + context_type_name
                else:
                    context_type_name = context_form_group.name

            else:
                context_type_name = ""

            name = context_type_name if context_type_name else current_rdrf_context_model.display_name
            s = "%s/%s" % (name, form_display_name)
        else:
            s = form_display_name
    else:
        s = form_display_name
    return s


def cached(func):
    d = {}

    def wrapped(*args, **kwargs):
        key = str("%s %s" % (args, kwargs))
        if key in d:
            return d[key]
        else:
            d[key] = func(*args, **kwargs)
            return d[key]

    return wrapped


@cached
def get_cached_instance(klass, *args, **kwargs):
    return klass.objects.get(*args, **kwargs)


def is_multisection(code):
    try:
        from rdrf.models import Section
        section_model = Section.objects.get(code=code)
        return section_model.allow_multiple
    except Section.DoesNotExist:
        return False


def get_cde(code):
    from rdrf.models import CommonDataElement
    return CommonDataElement.objects.filter(code=code).first()


def is_file_cde(code):
    cde = get_cde(code)
    return cde and cde.datatype == 'file'


def is_multiple_file_cde(code):
    cde = get_cde(code)
    return cde and cde.datatype == 'file' and cde.allow_multiple


def is_uploaded_file(value):
    return isinstance(value, (InMemoryUploadedFile, TemporaryUploadedFile))


def make_index_map(to_remove, count):
    """
    Returns a mapping from new_index -> old_index when indices
    `to_remove' are removed from a list of length `count'.
    For example:
      to_remove([1,3], 5) -> { 0:0, 1:2, 2:4 }
    """
    to_remove = set(to_remove)
    cut = [i for i in range(count) if i not in to_remove]
    return dict(list(zip(list(range(count)), cut)))


def create_permission(app_label, model, code_name, name):
    content_type = ContentType.objects.get(app_label=app_label, model=model)

    try:
        with transaction.atomic():
            Permission.objects.create(codename=code_name, name=name, content_type=content_type)
    except IntegrityError:
        pass


def get_form_links(user, patient_id, registry_model, context_model=None, current_form_name=""):
    if user is not None:
        if context_model and context_model.context_form_group:
            # show links to forms restricted to this config object
            container_model = context_model.context_form_group
        else:
            container_model = registry_model

        return [
            FormLink(
                patient_id,
                registry_model,
                form,
                selected=(
                    form.name == current_form_name),
                context_model=context_model) for form in container_model.forms
            if not form.is_questionnaire and user.can_view(form)]
    else:
        return []


def forms_and_sections_containing_cde(registry_model, cde_model_to_find):
    results = []
    for form_model in registry_model.forms:
        for section_model in form_model.section_models:
            for cde_model in section_model.cde_models:
                if cde_model.code == cde_model_to_find.code:
                    results.append((form_model, section_model))
    return results


def consent_status_for_patient(registry_code, patient):
    from registry.patients.models import ConsentValue
    from .models import ConsentSection, ConsentQuestion

    consent_sections = ConsentSection.objects.filter(registry__code=registry_code)
    answers = {}
    valid = []
    for consent_section in consent_sections:
        if consent_section.applicable_to(patient):
            questions = ConsentQuestion.objects.filter(section=consent_section)
            for question in questions:
                try:
                    cv = ConsentValue.objects.get(patient=patient, consent_question=question)
                    answers[cv.consent_question.code] = cv.answer
                except ConsentValue.DoesNotExist:
                    pass
            valid.append(consent_section.is_valid(answers))
    return all(valid)


def get_error_messages(forms):
    from rdrf.utils import de_camelcase

    messages = []

    def display(form_or_formset, field, error):
        form_name = form_or_formset.__class__.__name__.replace("Form", "").replace("Set", "")
        return "%s %s: %s" % (de_camelcase(form_name), field.replace("_", " "), error)

    for i, form in enumerate(forms):
        if isinstance(form._errors, list):
            for error_dict in form._errors:
                for field in error_dict:
                    messages.append(display(form, field, error_dict[field]))
        else:
            if form._errors is None:
                continue
            else:
                for field in form._errors:
                    for error in form._errors[field]:
                        if "This field is required" in error:
                            # these errors are indicated next to the field
                            continue
                        messages.append(display(form, field, error))
    results = list(map(strip_tags, messages))
    return results


def timed(func):
    logger = logging.getLogger(__name__)

    def wrapper(*args, **kwargs):
        a = datetime.datetime.now()
        result = func(*args, **kwargs)
        b = datetime.datetime.now()
        c = b - a
        func_name = func.__name__
        logger.debug("%s time = %s secs" % (func_name, c))
        return result
    return wrapper


def get_cde_value(form_model, section_model, cde_model, patient_record):
    # should refactor code everywhere to use this func
    if patient_record is None:
        return None
    for form_dict in patient_record["forms"]:
        if form_dict["name"] == form_model.name:
            for section_dict in form_dict["sections"]:
                if section_dict["code"] == section_model.code:
                    if not section_dict["allow_multiple"]:
                        for cde_dict in section_dict["cdes"]:
                            if cde_dict["code"] == cde_model.code:
                                return cde_dict["value"]
                    else:
                        values = []
                        items = section_dict["cdes"]
                        for item in items:
                            for cde_dict in item:
                                if cde_dict['code'] == cde_model.code:
                                    values.append(cde_dict["value"])
                        return values


def report_function(func):
    """
    decorator to mark a function as available in the reporting interface
    ( for safety and also to allow us later to discover these functions and
      present in a menu )
    """
    func.report_function = True
    return func


def check_calculation(calculation):
    """
    Run a calculation javascript fragment through ADsafe to see
    whether it's suitable for running in users' browsers.
    Returns the empty string on success, otherwise an error message.
    """
    script = os.path.join(os.path.dirname(__file__),
                          "scripts", "check-calculation.js")
    try:
        p = subprocess.Popen([script], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        output, _ = p.communicate(smart_bytes(calculation))
        if p.returncode != 0:
            return output.decode("utf-8", errors="replace")
    except OSError as e:
        logger.exception("Can't execute check-calculation.js")
        return "Couldn't execute %s: %s" % (script, e)
    return ""


def format_date(value):
    """
    Formats a date in Australian order, separated by hyphens, without
    leading zeroes.
    """
    return "{d.day}-{d.month}-{d.year}".format(d=value)

def parse_iso_date(s):
    "Opposite of datetime.datetime.isoformat()"
    return datetime.datetime.strptime(s, "%Y-%m-%d").date() if s else None

def parse_iso_datetime(s):
    "Opposite of datetime.date.isoformat()"
    return dateutil.parser.parse(s) if s else None

def wrap_uploaded_files(registry_code, post_files_data):
    from django.core.files.uploadedfile import UploadedFile
    from rdrf.file_upload import FileUpload

    def wrap(key, value):
        logger.debug("checking key %s" % key)
        if isinstance(value, UploadedFile):
            logger.debug("Is an UploadedFile ...")
            return FileUpload(registry_code, key, {"file_name": value.name, "django_file_id": 0})
        else:
            return value

    return { key: wrap(key, value) for key, value in list(post_files_data.items()) }


class Message():
    def __init__(self, text, tags=None):
        self.text = text
        self.tags = tags

    @staticmethod
    def success(text):
        return Message(text, tags='success')

    @staticmethod
    def info(text):
        return Message(text, tags='info')

    @staticmethod
    def warning(text):
        return Message(text, tags='warning')

    @staticmethod
    def danger(text):
        return Message(text, tags='danger')

    @staticmethod
    def error(text):
        return Message(text, tags='danger')

    def __repr__(self):
        return self.text



class TimeStripper(object):
    """
    This class exists to fix an error we introduced in the migration
    moving from Mongo to pure Django models with JSON fields ( "Modjgo" objects.)
    CDE date values were converted  into iso strings including a time T substring.
    This was done recursively for the cdes and history collections 
    """
    
    def __init__(self, dataset):
        self.dataset = dataset # queryset live , lists of data records for testing
        # following fields used for testing
        self.test_mode = False
        self.converted_date_cdes = []
        self.date_cde_codes = []
        self.num_updates = 0 # actual conversions performed
        

    def forward(self):
        for thing in self.dataset:
            print("Checking Modjgo object pk %s" % thing.pk)
            
            self.update(thing)
        print("Finished: Updated %s Modjgo objects" % self.num_updates)

    def get_id(self, m):
        pk = m.pk
        
        if m.data:
            if "django_id" in m.data:
                django_id = m.data["django_id"]
            else:
                django_id = None

            if "django_model" in m.data:
                django_model = m.data["django_model"]
            else:
                django_model = None
            return "Modjgo pk %s Django Model %s Django id %s" % (pk,
                                                                  django_model,
                                                                  django_id)
        else:
            return "Modjgo pk %s" % pk
        

            

    def munge_timestamp(self, datestring):
        if datestring is None:
            return datestring
        
        if "T" in datestring:
            t_index = datestring.index("T")
            return datestring[:t_index]
        else:
            return datestring

    def is_date_cde(self, cde_dict):
        code = cde_dict["code"]
        if self.test_mode:
            return code in self.date_cde_codes
        else:
            # not test mode
            from rdrf.models import CommonDataElement
            try:
                cde_model = CommonDataElement.objects.get(code=code)
                value = cde_model.datatype == "date"
                if value:
                    return value

            except CommonDataElement.DoesNotExist:
                print("Missing CDE Model! Data has code %s which does not exist on the site" % code)

    def update_cde(self, cde):
        code = cde.get("code", None)
        if not code:
            print("No code in cde dict?? - not updating")
            return
        old_datestring = cde["value"]
        new_datestring = self.munge_timestamp(old_datestring)
        if new_datestring != old_datestring:
            cde["value"] = new_datestring
            if self.test_mode:
                self.converted_date_cdes.append(cde["value"])
            print("Date CDE %s %s --> %s" % (code,
                                             old_datestring,
                                             new_datestring))

            return True

    def update(self, m):
        updated = False
        ident = self.get_id(m)
        if m.data:
            data_copy = deepcopy(m.data)
            updated = self.munge_data(m.data)
            if updated:
                try:
                    m.save()
                    print("%s saved OK" % ident)
                    self.num_updates += 1
                except Exception as ex:
                    print("Error saving Modjgo object %s after updating: %s" % (ident,
                                                                                ex))
                    raise   # rollback
                    
    def munge_data(self, data):
        updated = 0
        if "forms" in data:
            for form in data["forms"]:
                if "sections" in form:
                    for section in form["sections"]:
                        if not section["allow_multiple"]:
                            if "cdes" in section:
                                for cde in section["cdes"]:
                                    if self.is_date_cde(cde):
                                        if self.update_cde(cde):
                                            updated += 1
                        else:
                            items = section["cdes"]
                            for item in items:
                                for cde in item:
                                    if self.is_date_cde(cde):
                                        if self.update_cde(cde):
                                            updated += 1
                                            
        return updated > 0
                    

class HistoryTimeStripper(TimeStripper):
    def munge_data(self, data):
        # History embeds the full forms dictionary in the record key
        return super().munge_data(data["record"])



# Python 3.5 doesn't raises run time error when lists which contain None values are sorted
# see stackover flow http://stackoverflow.com/questions/12971631/sorting-list-by-an-attribute-that-can-be-none
@total_ordering
class MinType(object):
    def __le__(self, other):
        return True

    def __eq__(self, other):
        return (self is other)

def process_embedded_html(html, translate=True):

    from html.parser import HTMLParser
    from django.utils.translation import ugettext as _

    class Parser(HTMLParser):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.texts = []
            self.all_strings = []
            self.translate = translate
            

        def handle_starttag(self, tag, atts):
            prefix = "<%s " % tag
            if atts:
                rest = " ".join(['%s="%s"' % (pair[0], pair[1]) for pair in atts])
            else:
                rest = ""
                
            html = prefix + rest + ">"
            self.all_strings.append(html)

        def handle_endtag(self, tag):
            html = "</%s>" % tag
            self.all_strings.append(html)
            
        def handle_data(self, data):
            if self.translate:
                translated = _(data)
                self.texts.append(translated)
                self.all_strings.append(translated)
            else:
                self.texts.append(data)
                self.all_strings.append(data)


        def get_html(self):
            return "".join(self.all_strings)


    parser = Parser()
    parser.feed(html)
    if translate:
        # this finds the corresponding text in the translation file
        # and reconstructs the HTML
        return parser.get_html()
    else:
        # this just returns a list of extracted text strings
        # Used in the create_translation_file management command
        return parser.texts
    
    
        

            
    


