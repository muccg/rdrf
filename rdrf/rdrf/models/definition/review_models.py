from django.db import models
from django.utils.translation import ugettext as _

from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import RDRFContext
from rdrf.helpers.utils import generate_token
from rdrf.helpers.utils import check_models
from rdrf.helpers.utils import models_from_mongo_key
from rdrf.helpers.utils import mongo_key_from_models
from rdrf.helpers.utils import get_normal_fields

from django.core.exceptions import ValidationError

from registry.groups.models import CustomUser
from registry.patients.models import Patient
from registry.patients.models import ParentGuardian

import logging

logger = logging.getLogger(__name__)


def get_field_value(patient_model,
                    registry_model,
                    context_model,
                    form_model,
                    section_model,
                    cde_model,
                    data,
                    raw):
    raw_value = patient_model.get_form_value(registry_model.code,
                                             form_model.name,
                                             section_model.code,
                                             cde_model.code,
                                             False,
                                             context_model.pk,
                                             data)
    if raw:
        return raw_value
    else:
        return cde_model.get_display_value(raw_value)


class InvalidItemType(Exception):
    pass


class Missing:
    DISPLAY_VALUE = "Not entered"
    VALUE = None


REVIEW_TYPE_CHOICES = (("R", "Caregiver Review"),
                       ("V", "Clinician Verification"))


ADDRESS_FIELD_MAP = {"address_type": "Demographics____PatientDataAddressSection____AddressType",
                     "address": "Demographics____PatientDataAddressSection____Address",
                     "suburb": "Demographics____PatientDataAddressSection____SuburbTown",
                     "state": "Demographics____PatientDataAddressSection____State",
                     "postcode": "Demographics____PatientDataAddressSection____postcode",
                     "country": "Demographics____PatientDataAddressSection____Country"}

ADDRESS_VALUE_MAP = {"Home": "AddressTypeHome",
                     "Postal": "AddressTypePostal"}


def get_state(state_code):
    s = state_code.upper()
    if s.startswith("AU-"):
        return s.split("-")[1]


def generate_reviews(registry_model):
    reviews_dict = registry_model.metadata.get("reviews", {})
    for review_name, review_sections in reviews_dict.items():
        r = Review(registry=registry_model,
                   name=review_name)
        r.save()


class Review(models.Model):
    registry = models.ForeignKey(Registry, related_name="reviews", on_delete=models.CASCADE)
    name = models.CharField(max_length=80)  # e.g. annual review , biannual review
    code = models.CharField(max_length=80)  # used for url
    review_type = models.CharField(max_length=1,
                                   choices=REVIEW_TYPE_CHOICES,
                                   default="R")

    def __str__(self):
        return self.code

    def create_for_patient(self, patient, context_model=None):
        if context_model is None:
            context_model = patient.default_context(self.registry)
        pr = PatientReview(review=self,
                           patient=patient,
                           context=context_model)
        pr.save()
        return pr

    def create_for_parent(self, parent):
        for child in parent.children:
            pr = self.create_for_patient(child)
            pr.parent = parent
            pr.save()

    @property
    def view_name(self):
        return self.registry.code + "_review_" + self.code


class ReviewItemTypes:
    CONSENT_FIELD = "CF"        # continue to consent
    DEMOGRAPHICS_FIELD = "DF"   # update some data
    SECTION_CHANGE = "SC"      # monitor change in a given section
    MULTISECTION_ITEM = "MI"    # add to a list of items  ( e.g. new therapies since last review)
    MULTISECTION_UPDATE = "MU"  # replace / update a set of items  ( necessary?)
    VERIFICATION = "V"
    CLINICIAN_ACCESS = "CA"     # need specific flag to indicate we want to show the current clinician
    MULTI_TARGET = "MT"         # a collection of fields referred to by form.section.cde codes


ITEM_CHOICES = ((ReviewItemTypes.CONSENT_FIELD, _("Consent Item")),
                (ReviewItemTypes.DEMOGRAPHICS_FIELD, _("Demographics Field")),
                (ReviewItemTypes.CLINICIAN_ACCESS, _("Clinician Access")),
                (ReviewItemTypes.MULTI_TARGET, _("Multi Target")),
                (ReviewItemTypes.SECTION_CHANGE, _("Section Monitor")),
                (ReviewItemTypes.MULTISECTION_ITEM, _("Add to Section")),
                (ReviewItemTypes.MULTISECTION_UPDATE, _("Update Section")),
                (ReviewItemTypes.VERIFICATION, _("Verification Section")))


class TargetUpdater:
    def __init__(self, review_item, field_id):
        self.review_item = review_item
        self.field_id = field_id
        self.metadata = self.review_item.load_metadata()

    def update(self, patient_model, context_model, answer):
        for field_dict in self.metadata:
            target_dict = field_dict["target"]
            if "form" in target_dict:
                # update an arbritary cde

                form_name = target_dict["form"]
                section_code = target_dict["section"]
                cde_code = target_dict["cde"]
                registry_model = self.review_item.review.registry
                form_model = RegistryForm.objects.get(name=form_name,
                                                      registry=registry_model)
                section_model = Section.objects.get(code=section_code)
                cde_model = CommonDataElement.objects.get(code=cde_code)

                check_models(registry_model, form_model, section_model, cde_model)

                patient_model.set_form_value(registry_model.code,
                                             form_model.name,
                                             section_model.code,
                                             cde_model.code,
                                             answer,
                                             context_model=context_model)


def parse_appearance_condition(condition):
    # formname.sectioncode.cdecode == value
    if not condition:
        return None
    if "==" not in condition:
        return None
    spec, value = condition.strip().split("==")
    if "." not in spec:
        return None
    form_name, section_code, cde_code = spec.strip().split(".")
    form_model = RegistryForm.objects.get(name=form_name)
    section_model = Section.objects.get(code=section_code)
    cde_model = CommonDataElement.objects.get(code=cde_code)
    value = value.strip()
    datatype = cde_model.datatype.lower().strip()
    if datatype == "integer":
        value = int(value)
    elif datatype in ['float', 'decimal']:
        value = float(value)
    else:
        # leave as string
        pass

    def checker(patient_review_model):
        patient = patient_review_model.patient
        registry_model = patient_review_model.registry
        form_value = patient.get_form_value(registry_model.code,
                                            form_model.name,
                                            section_model.code,
                                            cde_model.code)
        return value == form_value

    return checker


class ReviewItem(models.Model):
    """
    A unit of a review
    """
    code = models.CharField(max_length=80)
    appearance_condition = models.TextField(blank=True, null=True)
    position = models.IntegerField(default=0)
    review = models.ForeignKey(Review, related_name="items", on_delete=models.CASCADE)
    item_type = models.CharField(max_length=2,
                                 choices=ITEM_CHOICES)

    category = models.CharField(max_length=80, blank=True, null=True)
    name = models.CharField(max_length=80, blank=True, null=True)
    fields = models.TextField(blank=True)  # used for demographics
    summary = models.TextField(blank=True)
    # the form or section models
    form = models.ForeignKey(RegistryForm, blank=True, null=True, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, blank=True, null=True, on_delete=models.CASCADE)
    target_code = models.CharField(max_length=80, blank=True, null=True)  # the cde or section code or consent code
    target_metadata = models.TextField(blank=True, null=True)  # form,section, cde json??

    def __str__(self):
        return self.code

    def load_metadata(self):
        import json
        if not self.target_metadata:
            return []
        else:
            return json.loads(self.target_metadata)

    def update_data(self, patient_model, parent_model, context_model, form_data, user):
        if self.item_type == ReviewItemTypes.CONSENT_FIELD:
            self._update_consent_data(patient_model, form_data, user)
        elif self.item_type == ReviewItemTypes.DEMOGRAPHICS_FIELD:
            self._update_demographics_data(patient_model, form_data, user)
        elif self.item_type == ReviewItemTypes.SECTION_CHANGE:
            self._update_section_data(patient_model, context_model, form_data, user)
        elif self.item_type == ReviewItemTypes.MULTISECTION_ITEM:
            self._add_multisection_data(patient_model, context_model, form_data, user)
        elif self.item_type == ReviewItemTypes.VERIFICATION:
            self._update_verification(patient_model, context_model, form_data, user)
        elif self.item_type == ReviewItemTypes.CLINICIAN_ACCESS:
            self._update_clinician_access(patient_model, context_model, form_data, user)
        elif self.item_type == ReviewItemTypes.MULTI_TARGET:
            self._update_multitargets(patient_model, context_model, form_data, user)
        else:
            raise InvalidItemType(self.item_type)

    def _update_consent_data(self, patient_model, form_data, user):
        from rdrf.models.definition.models import ConsentQuestion
        for field_key in form_data:
            if field_key.startswith("customconsent"):
                answer = form_data[field_key]
                key_parts = field_key.split("_")
                question_pk = int(key_parts[3])
                consent_question_model = ConsentQuestion.objects.get(id=question_pk)
                patient_model.set_consent(consent_question_model, answer)

    def _update_multitargets(self, patient_model, context_model, form_data, user):
        for field_id in form_data:
            answer = form_data[field_id]
            updater = TargetUpdater(field_id)
            updater.update(patient_model, context_model, answer)

    def _update_section_data(self, patient_model, context_model, form_data, user):
        registry_model = self.review.registry
        if not registry_model.has_feature("contexts"):
            # set_form_value requires this
            # default context is determined in method..
            context_to_use = None
        else:
            context_to_use = context_model

        registry_code = registry_model.code
        form_model = self.form
        form_name = form_model.name
        section_model = self.section
        section_code = section_model.code
        codes = [cde.code for cde in get_normal_fields(section_model)]
        error_msg = "Bad field in %s" % self.code
        for field_id in form_data:
            if field_id.startswith("metadata_"):
                # bookkeeping field not part of section
                continue
            field_form_model, field_section_model, field_cde_model = models_from_mongo_key(registry_model,
                                                                                           field_id)
            if field_form_model.name != form_model.name:
                raise ValidationError(error_msg)
            if field_section_model.code != section_model.code:
                raise ValidationError(error_msg)
            if field_cde_model.code not in codes:
                raise ValidationError(error_msg)

            cde_code = field_cde_model.code
            answer = form_data[field_id]
            patient_model.set_form_value(registry_code,
                                         form_name,
                                         section_code,
                                         cde_code,
                                         answer,
                                         context_to_use,
                                         save_snapshot=True,
                                         user=user)

    def _update_demographics_data(self, patient_model, form_data, user):
        from registry.patients.models import AddressType, PatientAddress
        # {'metadata_condition_changed': '1',
        # 'Demographics____PatientDataAddressSection____AddressType': 'AddressTypeHome',
        # 'Demographics____PatientDataAddressSection____Address': '1 Test Street',
        # 'Demographics____PatientDataAddressSection____Country': 'AU',
        # 'Demographics____PatientDataAddressSection____State': 'SA',
        # 'Demographics____PatientDataAddressSection____SuburbTown': 'Armadale',
        # 'Demographics____PatientDataAddressSection____postcode': '6112'}
        address_type = None
        address_map = {}
        delim = "____"

        def get_country(country_code):
            import pycountry
            for country in pycountry.countries:
                if country.alpha_2 == country_code:
                    return country.name
            return ""

        for field_id in form_data:
            if field_id.startswith("Demographics"):
                parts = field_id.split(delim)
                field = parts[-1]
                address_map[field] = form_data[field_id]
        address_type = address_map.get("AddressType", "AddressTypeHome")
        if address_type == "AddressTypeHome":
            address_type_obj, created = AddressType.objects.get_or_create(type="Home")
            if created:
                address_type_obj.description = "Home"
                address_type_obj.save()
        else:
            address_type_obj, created = AddressType.objects.get_or_create(type="Postal")
            if created:
                address_type_obj.description = "Postal"
                address_type_obj.save()

        patient_address, created = PatientAddress.objects.get_or_create(patient=patient_model,
                                                                        address_type=address_type_obj)
        patient_address.address = address_map.get("Address", "")
        patient_address.suburb = address_map.get("SuburbTown", "")
        # Country is country code  e.g. AU
        patient_address.country = address_map.get("Country", "")
        patient_address.state = patient_address.country + "-" + address_map.get("State", "")
        patient_address.postcode = address_map.get("postcode", "")
        patient_address.save()

    # TODO: do we still need this function? It is called by update_data().
    def _add_multisection_data(self, patient_model, context_model, form_data, user):
        pass

    def get_data(self, patient_model, context_model, raw=False):
        # get previous responses so they can be displayed

        if self.item_type == ReviewItemTypes.CONSENT_FIELD:
            return self._get_consent_data(patient_model, raw=raw)
        elif self.item_type == ReviewItemTypes.DEMOGRAPHICS_FIELD:
            return self._get_demographics_data(patient_model, raw=raw)
        elif self.item_type == ReviewItemTypes.SECTION_CHANGE:
            return self._get_section_data(patient_model, context_model, raw=raw)
        elif self.item_type == ReviewItemTypes.MULTI_TARGET:
            return self._get_multitarget_data(patient_model, context_model, raw=raw)
        elif self.item_type == ReviewItemTypes.VERIFICATION:
            return self._get_verification_data(patient_model, context_model, raw=raw)

        raise Exception("Unknown Review Type: %s" % self.item_type)

    def _get_verification_data(self, patient_model, context_model, raw):
        if raw:
            if self.fields:
                use_fields = True
            else:
                use_fields = False

            if not self.form and not self.section:
                return []
            return self._get_section_data(patient_model,
                                          context_model,
                                          raw,
                                          use_fields=use_fields)
        else:
            return []

    def _get_consent_data(self, patient_model, raw=False):
        from rdrf.models.definition.models import ConsentSection
        from rdrf.models.definition.models import ConsentQuestion
        from registry.patients.models import ConsentValue
        consent_section_code, consent_question_code = self.target_code.split("/")
        consent_section_model = ConsentSection.objects.get(code=consent_section_code,
                                                           registry=self.review.registry)

        consent_question_model = ConsentQuestion.objects.get(code=consent_question_code,
                                                             section=consent_section_model)

        field_label = consent_question_model.question_label

        try:
            consent_value = ConsentValue.objects.get(consent_question=consent_question_model,
                                                     patient_id=patient_model.pk)
            answer = consent_value.answer

        except ConsentValue.DoesNotExist:

            answer = False

        return [(field_label, answer)]

    def _get_demographics_data(self, patient_model, raw=False):
        is_address = self.fields.lower().strip() in ["postal_address", "home_address", "address"]
        if is_address:
            return self._get_address_data(patient_model, raw)
        else:
            return self._get_demographics_fields(patient_model, raw)

    def _get_address_data(self, patient_model, raw=False):
        from registry.patients.models import PatientAddress
        from registry.patients.models import AddressType
        pairs = []
        field = self.fields.lower().strip()
        if field == "postal_address":
            address_type = AddressType.objects.get(type="Postal")
        elif field == 'home_address':
            address_type = AddressType.objects.get(type="Home")
        else:
            address_type = ''

        try:
            address = PatientAddress.objects.get(patient=patient_model,
                                                 address_type=address_type)
        except PatientAddress.DoesNotExist:
            if raw:
                return {}
            return []

        if raw:
            m = ADDRESS_FIELD_MAP
            raw_map = {m["address_type"]: ADDRESS_VALUE_MAP.get(address_type.type, ""),
                       m["suburb"]: address.suburb,
                       m["address"]: address.address,
                       m["country"]: address.country,
                       m["postcode"]: address.postcode,
                       m["state"]: get_state(address.state)}
            return raw_map

        pairs.append(("Address Type", address_type.description))
        pairs.append(("Address", address.address))
        pairs.append(("Suburb", address.suburb))
        pairs.append(("Country", address.country))
        pairs.append(("State", address.state))
        pairs.append(("Postcode", address.postcode))
        return pairs

    def _get_demographics_fields(self, patient_model, raw):
        return []

    def _get_section_data(self, patient_model, context_model, raw=False, use_fields=False):
        # we need raw values for initial data
        # display values for the read only
        if self.section:
            assert not self.section.allow_multiple

        pairs = []
        data = patient_model.get_dynamic_data(self.review.registry,
                                              collection="cdes",
                                              context_id=context_model.pk,
                                              flattened=True)
        if raw:
            if use_fields:
                allowed_cde_codes = [x.strip() for x in self.fields.strip().split(",")]

                def get_fields_iterator():
                    for cde_model in self.section.cde_models:
                        if cde_model.code in allowed_cde_codes:
                            yield cde_model

                def get_fields_from_anywhere():
                    for section_model in self.form.section_models:
                        if not section_model.allow_multiple:
                            for cde_model in section_model.cde_models:
                                if cde_model.code in allowed_cde_codes:
                                    yield self.form, section_model, cde_model

                if self.section:
                    cde_iterator = get_fields_iterator
                else:
                    cde_iterator = get_fields_from_anywhere
            else:
                def section_iterator():
                    for cde_model in get_normal_fields(self.section):
                        yield cde_model

                cde_iterator = section_iterator

            # return a dictionary
            d = {}
            for thing in cde_iterator():
                if type(thing) is tuple:
                    form_model, section_model, cde_model = thing
                else:
                    form_model = self.form
                    section_model = self.section
                    cde_model = thing

                delimited_key = mongo_key_from_models(form_model,
                                                      section_model,
                                                      cde_model)
                try:
                    raw_value = get_field_value(patient_model,
                                                self.review.registry,
                                                context_model,
                                                form_model,
                                                section_model,
                                                cde_model,
                                                data,
                                                raw)
                    d[delimited_key] = raw_value
                except KeyError:
                    pass

            return d

        # if not raw return a list of pairs of display values

        for cde_model in get_normal_fields(self.section):
            if raw:
                field = cde_model.code
            else:
                field = cde_model.name
            try:
                value = get_field_value(patient_model,
                                        self.review.registry,
                                        context_model,
                                        self.form,
                                        self.section,
                                        cde_model,
                                        data,
                                        raw)
            except KeyError:
                if raw:
                    value = Missing.VALUE
                else:
                    value = Missing.DISPLAY_VALUE

            pairs.append((field, value))

        return pairs

    def _get_multitarget_data(self, patient_model, context_model, raw=False):
        pairs = []
        data = patient_model.get_dynamic_data(self.review.registry,
                                              collection="cdes",
                                              context_id=context_model.pk,
                                              flattened=True)

        for form_model, section_model, cde_model in self.multitargets:
            try:
                if raw:
                    field = cde_model.code
                else:
                    field = cde_model.name

                raw_value = patient_model.get_form_value(self.review.registry.code,
                                                         form_model.name,
                                                         section_model.code,
                                                         cde_model.code,
                                                         False,
                                                         context_model.pk,
                                                         data)
                if raw:
                    value = raw_value
                else:
                    value = cde_model.get_display_value(raw_value)

            except KeyError:
                if raw:
                    value = Missing.Value
                else:
                    value = Missing.DISPLAY_VALUE

            pairs.append((field, value))
        return pairs

    @property
    def multitargets(self):
        # only applicable to multitargets
        if not self.item_type == ReviewItemTypes.MULTI_TARGET:
            raise Exception("Cannot get multitargets of non-multitarget ReviewItem")
        metadata = self.load_metadata()
        if not metadata:
            return []

        def get_models(field_dict):
            registry_model = self.review.registry
            target_dict = field_dict["target"]
            form_model = RegistryForm.objects.get(registry=registry_model,
                                                  name=target_dict["form"])
            section_model = Section.objects.get(code=target_dict["section"])
            cde_model = CommonDataElement.objects.get(code=target_dict["cde"])
            return form_model, section_model, cde_model

        for field_dict in metadata:
            yield get_models(field_dict)

    def is_applicable_to(self, patient_review):
        if not self.appearance_condition:
            return True
        else:
            appearance_check = parse_appearance_condition(self.appearance_condition)
            if appearance_check is None:
                return True
            elif callable(appearance_check):
                return appearance_check(patient_review)
            else:
                raise Exception("Error checking appeaance condition")

    @property
    def verification_triples(self):
        if self.form:
            if self.section:
                if self.fields:
                    codes = [x.strip() for x in self.fields.split(",")]
                    cde_models = [cde_model for cde_model in get_normal_fields(self.section) if cde_model.code in codes]
                else:
                    cde_models = get_normal_fields(self.section.cde_models)

                for cde_model in cde_models:
                    yield self.form, self.section, cde_model
            else:
                for section_model in self.form.section_models:
                    for cde_model in get_normal_fields(section_model):
                        yield self.form, section_model, cde_model
        else:
            return []  # ??


class ReviewStates:
    CREATED = "C"         # created , patient hasn't filled out yet
    DATA_COLLECTED = "D"  # data collected from review and stored in patient review items
    FINISHED = "F"        # data fanned out without error from review items
    ERROR = "E"           # if an error stops the fan out


class VerificationStatus:
    VERIFIED = "V"
    NOT_VERIFIED = "N"
    UNKNOWN = "U"
    CORRECTED = "C"


class HasChangedStates:
    YES = "1"
    NO = "2"
    UNKNOWN = "3"


class ConditionStates:
    CURRENTLY_EXPERIENCING = "1"
    INTERMITTENTLY_EXPERIENCING = "2"
    RESOLVED = "3"
    UNKNOWN = "4"


class PatientReviewItemStates:
    CREATED = "C"               # model instance created , waiting for data
    DATA_COLLECTED = "D"        # data collected
    FINISHED = "F"


class PatientReview(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    # the user who will fill out the review
    user = models.ForeignKey(CustomUser, blank=True, null=True, on_delete=models.SET_NULL)
    parent = models.ForeignKey(ParentGuardian, blank=True, null=True, on_delete=models.CASCADE)
    context = models.ForeignKey(RDRFContext, on_delete=models.CASCADE)
    token = models.CharField(max_length=80, unique=True, default=generate_token)
    created_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    state = models.CharField(max_length=1, default=ReviewStates.CREATED)

    @property
    def moniker(self):
        return "%s for %s" % (self.review.code,
                              self.patient)

    def email_link(self):
        pass

    def create_review_items(self):
        for item in self.review.items.all():
            pri = PatientReviewItem(patient_review=self,
                                    review_item=item)
            pri.save()

    def reset(self):
        self.state = ReviewStates.CREATED
        self.completed_date = None
        self.save()
        for item in self.items.all():
            item.state = PatientReviewItemStates.CREATED
            item.has_changed = None
            item.current_status = None
            item.verification_status = None
            item.data = None
            item.save()

    def create_wizard_view(self, initialise=False, review_user=None):
        from rdrf.views.wizard_views import ReviewWizardGenerator
        generator = ReviewWizardGenerator(self, review_user)
        wizard_class = generator.create_wizard_class()
        if initialise:
            initial_data = self._get_initial_data()
            wizard_class.initial_dict = initial_data
            return wizard_class.as_view()
        else:
            return wizard_class.as_view()

    def _get_initial_data(self):
        d = {}
        for item_index, review_item in enumerate(self.review.items.all().order_by("id")):
            d[str(item_index)] = self._get_initial_data_for_review_item(review_item)
        return d

    def _get_initial_data_for_review_item(self, review_item):
        d = {}
        d["metadata_condition_changed"] = ConditionStates.UNKNOWN
        if review_item.item_type in [ReviewItemTypes.SECTION_CHANGE]:
            d["metadata_current_status"] = ConditionStates.UNKNOWN

        # get initial filled in data from rdrf form
        self._load_initial_form_data_for_review_item(review_item, d)
        return d

    def _load_initial_form_data_for_review_item(self, review_item, data_dict):
        # update data_dict
        patient_model = self.patient
        context_model = self.context
        review_item_data = review_item.get_data(patient_model, context_model, raw=True)
        data_dict.update(review_item_data)


class PatientReviewItem(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    patient_review = models.ForeignKey(PatientReview, related_name="items", on_delete=models.CASCADE)
    state = models.CharField(max_length=1, default=PatientReviewItemStates.CREATED)
    review_item = models.ForeignKey(ReviewItem, on_delete=models.CASCADE)
    has_changed = models.CharField(max_length=1,
                                   blank=True,
                                   null=True)

    current_status = models.CharField(max_length=1,
                                      blank=True,
                                      null=True)
    verification_status = models.CharField(max_length=1,
                                           blank=True,
                                           null=True)
    data = models.TextField(blank=True, null=True)  # json data

    def update_data(self, cleaned_data, user):
        self.data = self._encode_data(cleaned_data)
        self.state = PatientReviewItemStates.DATA_COLLECTED
        self.save()
        # fan out the review data from a patient to the correct place
        # the model knows how to update the data
        self.has_changed = cleaned_data.get("metadata_condition_changed", None)
        self.current_status = cleaned_data.get("metadata_current_status", None)
        if self.has_changed == HasChangedStates.YES:
            self.review_item.update_data(self.patient_review.patient,
                                         self.patient_review.parent,
                                         self.patient_review.context,
                                         cleaned_data,
                                         user)
        else:
            if self.review_item.review.review_type == "V":
                self._update_verifications(cleaned_data, user)

        self.state = PatientReviewItemStates.FINISHED
        self.save()

    def _update_verifications(self, form_data, user):
        from rdrf.models.definition.verification_models import Verification
        patient_model = self.patient_review.patient
        context_model = self.patient_review.context
        registry_model = self.patient_review.review.registry
        pri = self
        if user is not None:
            username = user.username
        else:
            username = ""

        for form_model, section_model, cde_model in self.review_item.verification_triples:
            value_key = "%s____%s____%s" % (form_model.name,
                                            section_model.code,
                                            cde_model.code)
            ver_key = "ver/%s" % value_key
            if ver_key in form_data:
                status = form_data[ver_key]
                value = form_data[value_key]

                verification_model = Verification(patient=patient_model,
                                                  patient_review_item=pri,
                                                  registry=registry_model,
                                                  context=context_model,
                                                  form_name=form_model.name,
                                                  section_code=section_model.code,
                                                  cde_code=cde_model.code,
                                                  status=status,
                                                  data=str(value),
                                                  username=username)

                verification_model.create_summary()
                verification_model.save()

    def _encode_data(self, data):
        import json
        return json.dumps(data)
