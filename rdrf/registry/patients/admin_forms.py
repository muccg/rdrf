import logging
import pycountry
from django import forms
from django.contrib.admin.widgets import AdminFileWidget
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList, ErrorDict

from models import *
from rdrf.dynamic_data import DynamicDataWrapper
from rdrf.hooking import run_hooks
from rdrf.models import ConsentQuestion, ConsentSection, DemographicFields
from rdrf.widgets import CountryWidget, StateWidget, DateWidget, ReadOnlySelect
from registry.groups.models import CustomUser, WorkingGroup
from registry.patients.models import Patient, PatientRelative
from registry.patients.patient_widgets import PatientRelativeLinkWidget

logger = logging.getLogger(__name__)


class PatientDoctorForm(forms.ModelForm):
    OPTIONS = (
        (None, "---"),
        (1, "GP (Primary Care)"),
        (2, "Specialist (Lipid)"),
        (3, "Primary Care"),
        (4, "Paediatric Neurologist"),
        (5, "Neurologist"),
        (6, "Geneticist"),
        (7, "Specialist - Other"),
        (8, "Cardiologist"),
        (9, "Nurse Practitioner"),
        (10, "Paediatrician"),
    )

    # Sorting of options
    OPTIONS = tuple(sorted(OPTIONS, key=lambda item: item[1]))

    relationship = forms.ChoiceField(label="Type of Medical Professional", choices=OPTIONS)

    class Meta:
        fields = "__all__"
        model = PatientDoctor


class PatientRelativeForm(forms.ModelForm):

    class Meta:
        model = PatientRelative
        fields = "__all__"  # Added after upgrading to Django 1.8
        exclude = ['id']    # Added after upgrading to Django 1.8  - uniqueness check was failing otherwise (RDR-1039)
        widgets = {
            'relative_patient': PatientRelativeLinkWidget,

        }

    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'class': 'datepicker'},
            format='%d-%m-%Y'),
        help_text="DD-MM-YYYY",
        input_formats=['%d-%m-%Y'])

    def __init__(self, *args, **kwargs):
        self.create_patient_data = None
        super(PatientRelativeForm, self).__init__(*args, **kwargs)
        #self.fields['date_of_birth'].input_formats = ['%d-%m-%Y']
        self.create_patient_flag = False
        self.tag = None    # used to locate this form

    def _clean_fields(self):
        logger.debug("in PatientRelatives clean fields")
        self._errors = ErrorDict()
        num_errors = 0
        if not self.is_bound:  # Stop further processing.
            return
        self.cleaned_data = {}
        keys_to_update = []
        # check for 'on' checkbox value for patient relative checkbox ( which means create patient )\
        # this 'on' value from widget is replaced by the pk of the created patient
        for name, field in self.fields.items():
            try:
                value = field.widget.value_from_datadict(
                    self.data, self.files, self.add_prefix(name))
                logger.debug("field %s = %s" % (name, value))
                if name == "relative_patient":
                    if value == "on":
                        logger.debug("on set for create patient - setting to None")
                        self.cleaned_data[name] = None
                        self.create_patient_flag = True
                    else:
                        self.cleaned_data[name] = value

                elif name == 'date_of_birth':
                    try:
                        self.cleaned_data[name] = self._set_date_of_birth(value)
                        logger.debug("cleaned patient relative date of birth = %s" % value)
                    except Exception as ex:
                        logger.debug("Exception cleaning date of birth: %s" % ex)
                        raise ValidationError("Date of Birth must be dd-mm-yyyy")

                elif name == 'patient':
                    continue   # this was causing error in post clean - we set this ourselves
                else:
                    self.cleaned_data[name] = value

                logger.debug("cleaned %s = %s" % (name, self.cleaned_data[name]))

            except ValidationError as e:
                num_errors += 1
                logger.debug("Patient Relative Validation Error name = %s field = %s error = %s" % (name, field, e))
                self._errors[name] = self.error_class(e.messages)
                if name in self.cleaned_data:
                    del self.cleaned_data[name]

        logger.debug("PR clean fields final error count = %s" % num_errors)
        self.tag = self.cleaned_data["given_names"] + self.cleaned_data["family_name"]
        logger.debug("after clean fields errors = %s" % self._errors)

    def _set_date_of_birth(self, dob):
        # todo figure  out why the correct input format is not being respected -
        # the field for dob on PatientRelative is in aus format already
        parts = dob.split("-")
        return "-".join([parts[2], parts[1], parts[0]])

    def _get_patient_relative_data(self, index):
        data = {}
        for k in self.data:
            if k.startswith("relatives-%s-" % index):
                data[k] = self.data[k]
        return data


class PatientAddressForm(forms.ModelForm):

    class Meta:
        model = PatientAddress
        fields = ('address_type', 'address', 'country', 'state', 'suburb', 'postcode')

    country = forms.ComboField(required=True, widget=CountryWidget(attrs={'onChange': 'select_country(this);'}))
    state = forms.ComboField(required=True, widget=StateWidget())
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class PatientConsentFileForm(forms.ModelForm):

    class Meta:
        model = PatientConsent
        fields = "__all__"

    form = forms.FileField(widget=AdminFileWidget, required=False)


class PatientForm(forms.ModelForm):

    ADDRESS_ATTRS = {
        "rows": 3,
        "cols": 30,
    }

    next_of_kin_country = forms.ComboField(
        required=False, widget=CountryWidget(attrs={'onChange': 'select_country(this);'}))
    next_of_kin_state = forms.ComboField(required=False, widget=StateWidget())
    country_of_birth = forms.ComboField(required=False, widget=CountryWidget())

    def __init__(self, *args, **kwargs):
        clinicians = CustomUser.objects.all()

        if 'registry_model' in kwargs:
            self.registry_model = kwargs['registry_model']
            del kwargs['registry_model']
        else:
            self.registry_model = None

        if 'instance' in kwargs and kwargs['instance'] is not None:
            instance = kwargs['instance']
            registry_specific_data = self._get_registry_specific_data(instance)
            initial_data = kwargs.get('initial', {})
            for reg_code in registry_specific_data:
                initial_data.update(registry_specific_data[reg_code])

            self._update_initial_consent_data(instance, initial_data)

            kwargs['initial'] = initial_data

            clinicians = CustomUser.objects.filter(
                registry__in=kwargs['instance'].rdrf_registry.all())

        if "user" in kwargs:
            self.user = kwargs.pop("user")

        super(PatientForm, self).__init__(*args, **kwargs)   # NB I have moved the constructor

        clinicians_filtered = [c.id for c in clinicians if c.is_clinician]
        self.fields["clinician"].queryset = CustomUser.objects.filter(
            id__in=clinicians_filtered)

        self.fields["rdrf_registry"].queryset = Registry.objects.filter(
            id__in=[self.registry_model.id])

        if hasattr(self, 'user'):
            user = self.user
            # working groups shown should be only related to the groups avail to the
            # user in the registry being edited
            if not user.is_superuser:
                self.fields["working_groups"].queryset = WorkingGroup.objects.filter(
                    registry=self.registry_model, id__in=[
                        wg.pk for wg in self.user.working_groups.all()])
            else:
                self.fields["working_groups"].queryset = WorkingGroup.objects.filter(registry=self.registry_model)

            # field visibility restricted no non admins
            if not user.is_superuser:
                if not self.registry_model:
                    registry = user.registry.all()[0]
                else:
                    registry = self.registry_model
                working_groups = user.groups.all()

                for field in self.fields:
                    hidden = False
                    readonly = False
                    for wg in working_groups:
                        try:
                            field_config = DemographicFields.objects.get(
                                registry=registry, group=wg, field=field)
                            hidden = hidden or field_config.hidden
                            readonly = readonly or field_config.readonly
                        except DemographicFields.DoesNotExist:
                            pass

                    if hidden:
                        self.fields[field].widget = forms.HiddenInput()
                        self.fields[field].label = ""
                    if readonly and not hidden:
                        self.fields[field].widget = forms.TextInput(
                            attrs={'readonly': 'readonly'})

        if self._is_adding_patient(kwargs):
            self._setup_add_form()

    def _get_registry_specific_data(self, patient_model):
        if patient_model is None:
            return {}
        mongo_wrapper = DynamicDataWrapper(patient_model)
        return mongo_wrapper.load_registry_specific_data(self.registry_model)

    def _update_initial_consent_data(self, patient_model, initial_data):
        if patient_model is None:
            return
        data = patient_model.consent_questions_data
        for consent_field_key in data:
            initial_data[consent_field_key] = data[consent_field_key]
            logger.debug("set initial data for %s to %s" %
                         (consent_field_key, data[consent_field_key]))

    def _is_adding_patient(self, kwargs):
        return 'instance' in kwargs and kwargs['instance'] is None

    def _setup_add_form(self):
        logger.debug("in setup add form ...")
        if hasattr(self, "user"):
            user = self.user
        else:
            user = None
        logger.debug("user is %s" % user)
        logger.debug("form.registry_model = %s" % self.registry_model)
        if not user.is_superuser:
            initial_working_groups = user.working_groups.filter(registry=self.registry_model)
            self.fields['working_groups'].queryset = initial_working_groups
            logger.debug("restricted working groups choices to %s" %
                         [wg.pk for wg in initial_working_groups])
        else:
            self.fields['working_groups'].queryset = WorkingGroup.objects.filter(registry=self.registry_model)

    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'class': 'datepicker'},
            format='%d-%m-%Y'),
        help_text="DD-MM-YYYY",
        input_formats=['%d-%m-%Y'])

    class Meta:
        model = Patient
        widgets = {
            'next_of_kin_address': forms.Textarea(attrs={"rows": 3, "cols": 30}),
            'inactive_reason': forms.Textarea(attrs={"rows": 3, "cols": 30}),
            'user': forms.HiddenInput()
        }
        exclude = ['doctors']

    # Added to ensure unique (familyname, givennames, workinggroup)
    # Does not need a unique constraint on the DB

    def clean(self):
        logger.debug("in PatientForm clean ...")
        self.custom_consents = {}
        cleaneddata = self.cleaned_data

        for k in cleaneddata:
            logger.debug("cleaned field %s = %s" % (k, cleaneddata[k]))

        for k in cleaneddata:
            if k.startswith("customconsent_"):
                self.custom_consents[k] = cleaneddata[k]

        for k in self.custom_consents:
            del cleaneddata[k]
            logger.debug("removed custom consent %s" % k)

        family_name = stripspaces(cleaneddata.get("family_name", "") or "").upper()
        given_names = stripspaces(cleaneddata.get("given_names", "") or "")

        if "working_groups" not in cleaneddata:
            raise forms.ValidationError("Patient must be assigned to a working group")
        if not cleaneddata["working_groups"]:
            raise forms.ValidationError("Patient must be assigned to a working group")

        self._check_working_groups(cleaneddata)

        self._validate_custom_consents()

        return super(PatientForm, self).clean()

    def _validate_custom_consents(self):
        logger.debug("custom consents = %s" % self.custom_consents)
        data = {}
        for field_key in self.custom_consents:
            logger.debug("field key = %s" % field_key)
            parts = field_key.split("_")
            reg_pk = int(parts[1])
            registry_model = Registry.objects.get(id=reg_pk)
            logger.debug("reg = %s" % registry_model)
            if registry_model not in data:
                data[registry_model] = {}

            consent_section_pk = int(parts[2])
            consent_section_model = ConsentSection.objects.get(id=int(consent_section_pk))
            logger.debug("section model = %s" % consent_section_model)

            if consent_section_model not in data[registry_model]:
                data[registry_model][consent_section_model] = {}

            consent_question_pk = int(parts[3])
            consent_question_model = ConsentQuestion.objects.get(id=consent_question_pk)
            logger.debug("consent question = %s" % consent_question_model)
            answer = self.custom_consents[field_key]
            logger.debug("answer = %s" % answer)

            data[registry_model][consent_section_model][consent_question_model.code] = answer

        validation_errors = []

        for registry_model in data:
            for consent_section_model in data[registry_model]:

                answer_dict = data[registry_model][consent_section_model]
                if not consent_section_model.is_valid(answer_dict):
                    error_message = "Consent Section '%s %s' is not valid" % (
                        registry_model.code.upper(), consent_section_model.section_label)
                    validation_errors.append(error_message)
                else:
                    logger.debug("Consent section %s is valid!" %
                                 consent_section_model.section_label)

        if len(validation_errors) > 0:
            raise forms.ValidationError("Consent Error(s): %s" % ",".join(validation_errors))

    def save(self, commit=True):
        patient_model = super(PatientForm, self).save(commit=False)
        patient_model.active = True
        logger.debug("patient instance = %s" % patient_model)
        try:
            patient_registries = [r for r in patient_model.rdrf_registry.all()]
        except ValueError:
            # If patient just created line above was erroring
            patient_registries = []
        logger.debug("patient registries = %s" % patient_registries)

        logger.debug("persisting custom consents from form")
        logger.debug("There are %s custom consents" % len(self.custom_consents.keys()))

        if "user" in self.cleaned_data:
            patient_model.user = self.cleaned_data["user"]

        if commit:
            patient_model.save()
            patient_model.working_groups = [wg for wg in self.cleaned_data["working_groups"]]
            patient_model.rdrf_registry = [reg for reg in self.cleaned_data["rdrf_registry"]]
            patient_model.save()

        patient_model.clinician = self.cleaned_data["clinician"]

        for consent_field in self.custom_consents:
            logger.debug("saving consent field %s ( value to save = %s)" %
                         (consent_field, self.custom_consents[consent_field]))
            registry_model, consent_section_model, consent_question_model = self._get_consent_field_models(
                consent_field)

            if registry_model in patient_registries:
                logger.debug("saving consents for %s %s" %
                             (registry_model, consent_section_model))
                # are we still applicable?! - maybe some field on patient changed which
                # means not so any longer?
                if consent_section_model.applicable_to(patient_model):
                    logger.debug("%s is applicable to %s" %
                                 (consent_section_model, patient_model))
                    cv = patient_model.set_consent(
                        consent_question_model, self.custom_consents[consent_field], commit)
                    logger.debug("set consent value ok : cv = %s" % cv)
                else:
                    logger.debug("%s is not applicable to model %s" %
                                 (consent_section_model, patient_model))

            else:
                logger.debug("patient not in %s ?? no consents added here" % registry_model)

            if not patient_registries:
                logger.debug("No registries yet - Adding patient consent closure")
                closure = self._make_consent_closure(
                    registry_model,
                    consent_section_model,
                    consent_question_model,
                    consent_field)
                if hasattr(patient_model, 'add_registry_closures'):
                    logger.debug("appending to closure list")
                    patient_model.add_registry_closures.append(closure)
                else:
                    logger.debug("settng new closure list")
                    setattr(patient_model, 'add_registry_closures', [closure])

        return patient_model

    def _make_consent_closure(
            self,
            registry_model,
            consent_section_model,
            consent_question_model,
            consent_field):
        def closure(patient_model, registry_ids):
            logger.debug("running consent closure")
            if registry_model.id in registry_ids:
                if consent_section_model.applicable_to(patient_model):
                    logger.debug("%s is applicable to %s" %
                                 (consent_section_model, patient_model))
                    cv = patient_model.set_consent(
                        consent_question_model, self.custom_consents[consent_field])
                    logger.debug("set consent value ok : cv = %s" % cv)
                else:
                    logger.debug("%s is not applicable to model %s" %
                                 (consent_section_model, patient_model))
            else:
                pass
        return closure

    def _check_working_groups(self, cleaned_data):
        working_group_data = {}
        for working_group in cleaned_data["working_groups"]:
            if working_group.registry:
                if working_group.registry.code not in working_group_data:
                    working_group_data[working_group.registry.code] = [working_group]
                else:
                    working_group_data[working_group.registry.code].append(working_group)

        bad = []
        for reg_code in working_group_data:
            if len(working_group_data[reg_code]) > 1:
                bad.append(reg_code)

        if bad:
            bad_regs = [Registry.objects.get(code=reg_code).name for reg_code in bad]
            raise forms.ValidationError(
                "Patient can only belong to one working group per registry. Patient is assigned to more than one working for %s" %
                ",".join(bad_regs))


class ParentGuardianForm(forms.ModelForm):

    class Meta:
        model = ParentGuardian
        fields = [
            'first_name',
            'last_name',
            'date_of_birth',
            'gender',
            'address',
            'country',
            'state',
            'suburb',
            'postcode',
            'phone'
        ]
        exclude = [
            'user',
            'patient',
            'place_of_birth',
            'date_of_migration'
        ]

        widgets = {
            'state': StateWidget(),
            'country': CountryWidget()
        }
