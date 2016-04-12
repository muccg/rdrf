from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from django.conf import settings
from django.db import IntegrityError
from django.db import transaction
from django.utils.html import strip_tags
from django.core.urlresolvers import reverse

import logging
import re
import functools

logger = logging.getLogger("registry_log")


class BadKeyError(Exception):
    pass


def mongo_db_name(registry):
    return settings.MONGO_DB_PREFIX + registry


def mongo_db_name_reg_id(registry_id):
    from models import Registry
    reg = Registry.objects.get(id=registry_id)
    return settings.MONGO_DB_PREFIX + reg.code


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
    return filter(lambda x: x is not None, [get_user(username) for username in usernames])


def has_feature(feature_name):
    if settings.FEATURES == "*":
        return True
    return feature_name in settings.FEATURES  # e.g. [ 'email_notification', 'adjudication' ]


def requires_feature(feature_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if has_feature(feature_name):
                return func(*args, **kwargs)
            else:
                logger.info(
                    "%s will not be run with args %s kwargs %s as the site lacks feature %s" %
                    (func.__name__, args, kwargs, feature_name))
        return wrapper
    return decorator


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
    if registry_form.registry.has_feature("contexts"):
            if current_rdrf_context_model is not None:
                registry_model = registry_form.registry
                patient_model = current_rdrf_context_model.content_object
                edit_link = reverse("context_edit", args=(registry_model.code,
                                                          patient_model.pk,
                                                          current_rdrf_context_model.pk))
                context_link = """<a href="%s">%s</a>""" % (edit_link, current_rdrf_context_model.display_name)
                s = "%s ( in %s)" % (form_display_name, context_link)
            else:
                s = form_display_name
    else:
        s = form_display_name
    logger.debug("location_name = %s" % s)
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


def is_file_cde(code):
    from rdrf.models import CommonDataElement
    try:
        cde = CommonDataElement.objects.get(code=code)
        if cde.datatype == 'file':
            return True
    except Exception:
        pass
    return False


def is_uploaded_file(value):
    from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
    return isinstance(value, InMemoryUploadedFile) or isinstance(value, TemporaryUploadedFile)


def make_index_map(index_actions_list):
    # index_actions_list looks like [1,0,1,0,1]
    # 1 means that this item in the list was not deleted
    # 0 means that item in the list was deleted
    # we return a map mapping the positions of the 1s ( kept items)
    # to original indices - this allows us to retriebve data from an item
    # depsite re-ordering\
    # index map in example is {0: 0, 1: 2, 2: 4}

    m = {}
    new_index = 0
    for original_index, i in enumerate(index_actions_list):
        if i == 1:
            m[new_index] = original_index
            new_index += 1
    return m


def is_gridfs_file_wrapper(value):
    return isinstance(value, dict) and "griffs_file_id" in value


def create_permission(app_label, model, code_name, name):
    content_type = ContentType.objects.get(app_label=app_label, model=model)
    
    try:
        with transaction.atomic():
            Permission.objects.create(codename=code_name, name=name, content_type=content_type)
    except IntegrityError:
        pass


def get_form_links(user, patient_id, registry_model, context_model=None):
    if user is not None:
        return [
            FormLink(
                patient_id,
                registry_model,
                form,
                selected=(
                    form.name == ""),
                context_model=context_model) for form in registry_model.forms
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
    from models import ConsentSection, ConsentQuestion

    consent_sections = ConsentSection.objects.filter(registry__code=registry_code)
    answers = []
    for consent_section in consent_sections:
        if consent_section.applicable_to(patient):
            questions = ConsentQuestion.objects.filter(section=consent_section)
            for question in questions:
                try:
                    cv = ConsentValue.objects.get(patient=patient, consent_question = question)
                    answers.append(cv.answer)
                except ConsentValue.DoesNotExist:
                    answers.append(False)
    return all(answers)


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
    results = map(strip_tags, messages)
    return results


def timed(func):
    from logging import getLogger
    from datetime import datetime
    logger = logging.getLogger("registry_log")
    def wrapper(*args, **kwargs):
        a = datetime.now()
        result = func(*args, **kwargs)
        b = datetime.now()
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


class FieldExpressionError(Exception):
    pass

def evaluate_consent(registry_model, patient_model, consent_expression):
    # used in GFE below
    # e.g. Consents/SomeSectionCode/SomeConsentCode/answer
    from rdrf.models import ConsentSection, ConsentQuestion
    
    _, consent_section_code, consent_code, consent_field = consent_expression.split("/")
    
    try:
        consent_section_model = ConsentSection.objects.get(code=consent_section_code,
                                                           registry=registry_model)
    except ConsentSection.DoesNotExist:
        raise FieldExpressionError("consent section does not exist")
    
    try:
        consent_question_model = ConsentQuestion.objects.get(code=consent_code,
                                                             section=consent_section_model)
    except ConsentQuestion.DoesNotExist:
        raise FieldExpressionError("consent question does not exist")

    if consent_expression.lower().endswith("/answer"):
        return patient_model.get_consent(consent_question_model, "answer")
    if consent_expression.lower().endswith("/last_update"):
        return str(patient_model.get_consent(consent_question_model, "last_update"))
    elif consent_expression.endswith("/first_save"):
        return str(patient_model.get_consent(consent_question_model, "first_save"))
    else:
        raise FieldExpressionError("Unknown consent field: %s" % consent_expression)


def evaluate_address(patient_model, address_expression):
    """
    maybe this expression language should expressed in pyparsing later or some equiv

    gets first by default

    Demographics/Address/Home/Address
    Demographics/Address/Home/Suburb
    Demographics/Address/Home/State
    Demographics/Address/Home/State
    Demographics/Address/Home/Country
    Demographics/Address/Postal/Address
    Demographics/Address/Postal/Suburb
    Demographics/Address/Postal/State
    Demographics/Address/Postal/State
    Demographics/Address/Postal/Country
    """
    from registry.patients.models import PatientAddress, AddressType
    try:
        _, _, address_type, field = address_expression.split("/")
        if address_type not in ["Home","Postal"]:
            raise FieldExpressionError("Unknown address type: %s" % address_type)
        if field not in ["Address", "Suburb", "State","Country","Postcode"]:
            raise FieldExpressionError("Unknown address field: %s" % field)

        try:
            address_type_model = AddressType.objects.get(type=address_type)
        except AddressType.DoesNotExist:
            raise FieldExpressionError("Address type does not exist: %s" % address_type)
        
        try: 
            address_model = PatientAddress.objects.get(patient=patient_model,
                                                       address_type=address_type_model)
        except PatientAddress.DoesNotExist:
            return None

        return getattr(address_model, field.lower())
    except Exception, ex:
        raise FieldExpressionError("Error in address expression %s: %s" % (address_expression,
                                                                           ex))
            
        
    
    

def evaluate_generalised_field_expression(registry_model, patient_model, patient_fields, field_expression, nested_patient_record):
    # field expression looks like:
    # "clinical form name/sectioncode/cdecode" gets that value
    # "given_names" gets directly from patient model
    # "@function_name" applies report field function function_name to patient_model
    # "Consents/<ConsentSectionCode>/<ConsentQuestionCode>/[answer|last_update|first_save]

    from registry.patients.models import Patient
    try:
        if field_expression in patient_fields:
            return getattr(patient_model, field_expression)
        elif "/" in field_expression:
            if field_expression.startswith("Consents/"):
                return evaluate_consent(registry_model, patient_model, field_expression)
            if field_expression.startswith("Demographics/Address/"):
                return evaluate_address(patient_model, field_expression)
            if nested_patient_record is None:
                return None
            from rdrf.models import RegistryForm, Section, CommonDataElement
            form_name, section_code, cde_code = field_expression.split("/")
            form_model = RegistryForm.objects.get(name=form_name, registry=registry_model)
            section_model = Section.objects.get(code=section_code)
            cde_model = CommonDataElement.objects.get(code=cde_code)

            try:
                return get_cde_value(form_model, section_model, cde_model, nested_patient_record)
            except Exception, ex:
                raise FieldExpressionError("get_cde_value error - %s" % ex)

        elif field_expression.startswith("@"):
            # find denotation of custom function ?
            from rdrf import report_field_functions
            try:
                func = getattr(report_field_functions, field_expression[1:])
                if callable(func) and hasattr(func, "report_function") and func.report_function:
                    return func(patient_model)
            except Exception, ex:
                raise FieldExpressionError("Error evaluating report function %s: %s" % (field_expression, ex))
        else:
            raise FieldExpressionError("Unknown field expression: %s" % field_expression)

    except FieldExpressionError, fee:
        logger.error("Field Expression Error for patient id %s: %s" % (patient_model.pk,
                                                                       fee))
        return "??ERROR??"


    
        
        
