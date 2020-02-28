import logging
import pycountry
from django import forms
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorDict

from .models import (
    Patient,
    PatientAddress,
    PatientConsent,
    Registry,
    PatientRelative,
    ParentGuardian,
    PatientDoctor)
from rdrf.db.dynamic_data import DynamicDataWrapper
from rdrf.models.definition.models import ConsentQuestion, ConsentSection, DemographicFields
from rdrf.forms.widgets.widgets import CountryWidget, StateWidget, ConsentFileInput
from registry.groups.models import CustomUser, WorkingGroup
from registry.patients.patient_widgets import PatientRelativeLinkWidget
from django.utils.translation import ugettext as _

logger = logging.getLogger(__name__)


class PatientDoctorForm(forms.ModelForm):
    OPTIONS = (
        (None, "---"),
        (1, _("GP (Primary Care)")),
        (2, _("Specialist (Lipid)")),
        (3, _("Primary Care")),
        (4, _("Paediatric Neurologist")),
        (5, _("Neurologist")),
        (6, _("Geneticist")),
        (7, _("Specialist - Other")),
        (8, _("Cardiologist")),
        (9, _("Nurse Practitioner")),
        (10, _("Paediatrician")),
    )

    # Sorting of options
    OPTIONS = tuple(sorted(OPTIONS, key=lambda item: item[1]))

    relationship = forms.ChoiceField(label=_("Type of Medical Professional"), choices=OPTIONS)

    class Meta:
        fields = "__all__"
        model = PatientDoctor


class PatientRelativeForm(forms.ModelForm):
    class Meta:
        model = PatientRelative
        fields = "__all__"  # Added after upgrading to Django 1.8
        # Added after upgrading to Django 1.8  - uniqueness check was failing
        # otherwise (RDR-1039)
        exclude = ['id']
        widgets = {
            'relative_patient': PatientRelativeLinkWidget,
        }

    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}, format='%d-%m-%Y'),
        help_text=_("DD-MM-YYYY"),
        input_formats=['%d-%m-%Y'])

    def __init__(self, *args, **kwargs):
        self.create_patient_data = None
        super(PatientRelativeForm, self).__init__(*args, **kwargs)
        self.create_patient_flag = False
        self.tag = None  # used to locate this form

    def _clean_fields(self):
        self._errors = ErrorDict()
        num_errors = 0
        if not self.is_bound:  # Stop further processing.
            return
        self.cleaned_data = {}
        # check for 'on' checkbox value for patient relative checkbox ( which means create patient )\
        # this 'on' value from widget is replaced by the pk of the created patient
        for name, field in list(self.fields.items()):
            try:
                value = field.widget.value_from_datadict(self.data, self.files, self.add_prefix(name))
                if name == "relative_patient":
                    if value == "on":
                        self.cleaned_data[name] = None
                        self.create_patient_flag = True
                    else:
                        self.cleaned_data[name] = value

                elif name == 'date_of_birth':
                    try:
                        self.cleaned_data[name] = self._set_date_of_birth(value)
                    except Exception:
                        raise ValidationError("Date of Birth must be dd-mm-yyyy")

                elif name == 'patient':
                    continue  # this was causing error in post clean - we set this ourselves
                else:
                    self.cleaned_data[name] = value

            except ValidationError as e:
                num_errors += 1
                self._errors[name] = self.error_class(e.messages)
                if name in self.cleaned_data:
                    del self.cleaned_data[name]

        self.tag = self.cleaned_data["given_names"] + self.cleaned_data["family_name"]

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

    country = forms.ChoiceField(required=True,
                                widget=CountryWidget(attrs={'onChange': 'select_country(this);'}))
    state = forms.ChoiceField(required=True,
                              widget=StateWidget())
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))

    def clean_state(self):
        if "state" in self.cleaned_data:
            state = self.cleaned_data["state"]
            if state != ' ':
                return state
            else:
                if "country" in self.cleaned_data:
                    country_code = self.cleaned_data["country"]
                    states = pycountry.subdivisions.get(country_code=country_code)
                    if len(states):
                        raise forms.ValidationError("This field is required")
                    else:
                        return state


class PatientConsentFileForm(forms.ModelForm):
    class Meta:
        model = PatientConsent
        fields = ["form"]
        exclude = ["filename"]

    form = forms.FileField(widget=ConsentFileInput, required=False)

    def save(self, commit=True):
        # remember the filename of the uploaded file
        if self.cleaned_data.get("form"):
            self.instance.filename = self.cleaned_data["form"].name
        return super(PatientConsentFileForm, self).save(commit)


class PatientForm(forms.ModelForm):

    ADDRESS_ATTRS = {
        "rows": 3,
        "cols": 30,
    }

    next_of_kin_country = forms.ChoiceField(required=False,
                                            widget=CountryWidget(attrs={'onChange': 'select_country(this);'}))
    next_of_kin_state = forms.ChoiceField(required=False, widget=StateWidget())
    country_of_birth = forms.ChoiceField(required=False, widget=CountryWidget())

    def __init__(self, *args, **kwargs):
        clinicians = CustomUser.objects.all()
        instance = None

        if 'registry_model' in kwargs:
            self.registry_model = kwargs['registry_model']
            del kwargs['registry_model']
        else:
            self.registry_model = None

        if 'instance' in kwargs and kwargs['instance'] is not None:
            instance = kwargs['instance']
            registry_specific_data = self._get_registry_specific_data(instance)
            wrapped_data = self._wrap_file_cdes(registry_specific_data)
            initial_data = kwargs.get('initial', {})
            for reg_code in wrapped_data:
                initial_data.update(wrapped_data[reg_code])

            self._update_initial_consent_data(instance, initial_data)

            kwargs['initial'] = initial_data

            clinicians = CustomUser.objects.filter(registry__in=kwargs['instance'].rdrf_registry.all())

        if "user" in kwargs:
            self.user = kwargs.pop("user")

        super(PatientForm, self).__init__(*args, **kwargs)  # NB I have moved the constructor

        clinicians_filtered = [c.id for c in clinicians if c.is_clinician]
        self.fields["clinician"].queryset = CustomUser.objects.filter(id__in=clinicians_filtered)

        # clinicians field should only be visible for registries which
        # support linking of patient to an "owning" clinician
        if self.registry_model:
            if not self.registry_model.has_feature("clinicians_have_patients"):
                self.fields["clinician"].widget = forms.HiddenInput()

        registries = Registry.objects.all()
        if self.registry_model:
            registries = registries.filter(id=self.registry_model.id)
        self.fields["rdrf_registry"].queryset = registries

        if hasattr(self, 'user'):
            user = self.user
            # working groups shown should be only related to the groups avail to the
            # user in the registry being edited
            if not user.is_superuser:
                if self._is_parent_editing_child(instance):
                    # see FKRP #472
                    self.fields["working_groups"].widget = forms.SelectMultiple(attrs={'readonly': 'readonly'})
                    self.fields["working_groups"].queryset = instance.working_groups.all()
                else:
                    self.fields["working_groups"].queryset = WorkingGroup.objects.filter(
                        registry=self.registry_model, id__in=[wg.pk for wg in self.user.working_groups.all()])
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
                            field_config = DemographicFields.objects.get(registry=registry, group=wg, field=field)
                            hidden = hidden or field_config.hidden
                            readonly = readonly or field_config.readonly
                        except DemographicFields.DoesNotExist:
                            pass

                    if hidden:
                        if field in ["date_of_birth", "date_of_death", "date_of_migration"]:
                            self.fields[field].widget = forms.DateInput(attrs={'class': 'datepicker', 'style': 'display:none;'}, format='%d-%m-%Y')
                            self.fields[field].label = ""
                            self.fields[field].help_text = ""
                        else:
                            self.fields[field].widget = forms.HiddenInput()
                            self.fields[field].label = ""

                    if readonly and not hidden:
                        if field in ["date_of_birth", "date_of_death", "date_of_migration"]:
                            self.fields[field].widget = forms.DateInput(attrs={'readonly': 'readonly', 'datepicker': 'true'}, format='%d-%m-%Y')
                        else:
                            self.fields[field].widget = forms.TextInput(attrs={'readonly': 'readonly'})

        if self._is_adding_patient(kwargs):
            self._setup_add_form()

    def _is_parent_editing_child(self, patient_model):
        # see FKRP #472
        if patient_model is not None and hasattr(self, "user"):
            try:
                parent_guardian = ParentGuardian.objects.get(user=self.user)
                return patient_model in parent_guardian.children
            except ParentGuardian.DoesNotExist:
                pass

    def _get_registry_specific_data(self, patient_model):
        if patient_model is None:
            return {}
        mongo_wrapper = DynamicDataWrapper(patient_model)
        return mongo_wrapper.load_registry_specific_data(self.registry_model)

    def _wrap_file_cdes(self, registry_specific_data):
        from rdrf.forms.file_upload import FileUpload
        from rdrf.forms.file_upload import is_filestorage_dict
        from rdrf.helpers.utils import is_file_cde

        def wrap_file_cde_dict(registry_code, cde_code, filestorage_dict):
            return FileUpload(registry_code, cde_code, filestorage_dict)

        def wrap(registry_code, cde_code, value):
            if is_file_cde(cde_code) and is_filestorage_dict(value):
                return wrap_file_cde_dict(registry_code, cde_code, value)
            else:
                return value

        wrapped_dict = {}

        for reg_code in registry_specific_data:
            reg_data = registry_specific_data[reg_code]
            wrapped_data = {key: wrap(reg_code, key, value) for key, value in reg_data.items()}
            wrapped_dict[reg_code] = wrapped_data

        return wrapped_dict

    def _update_initial_consent_data(self, patient_model, initial_data):
        if patient_model is None:
            return
        data = patient_model.consent_questions_data
        for consent_field_key in data:
            initial_data[consent_field_key] = data[consent_field_key]

    def _is_adding_patient(self, kwargs):
        return 'instance' in kwargs and kwargs['instance'] is None

    def _setup_add_form(self):
        if hasattr(self, "user"):
            user = self.user
        else:
            user = None

        if not user.is_superuser:
            initial_working_groups = user.working_groups.filter(registry=self.registry_model)
            self.fields['working_groups'].queryset = initial_working_groups
        else:
            self.fields['working_groups'].queryset = WorkingGroup.objects.filter(registry=self.registry_model)

    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}, format='%d-%m-%Y'),
        help_text=_("DD-MM-YYYY"),
        input_formats=['%d-%m-%Y'])

    date_of_death = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}, format='%d-%m-%Y'),
        help_text=_("DD-MM-YYYY"),
        input_formats=['%d-%m-%Y'],
        required=False)

    date_of_migration = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}, format='%d-%m-%Y'),
        help_text=_("DD-MM-YYYY"),
        required=False,
        input_formats=['%d-%m-%Y'])

    class Meta:
        model = Patient
        widgets = {
            'next_of_kin_address': forms.Textarea(attrs={
                "rows": 3,
                "cols": 30
            }),
            'inactive_reason': forms.Textarea(attrs={
                "rows": 3,
                "cols": 30
            }),
            'user': forms.HiddenInput()
        }
        exclude = ['doctors']

    # Added to ensure unique (familyname, givennames, workinggroup)
    # Does not need a unique constraint on the DB

    def clean(self):
        self.custom_consents = {}
        cleaneddata = self.cleaned_data

        for k in cleaneddata:
            if k.startswith("customconsent_"):
                self.custom_consents[k] = cleaneddata[k]

        for k in self.custom_consents:
            del cleaneddata[k]

        if "working_groups" not in cleaneddata:
            raise forms.ValidationError("Patient must be assigned to a working group")
        if not cleaneddata["working_groups"]:
            raise forms.ValidationError("Patient must be assigned to a working group")

        self._check_working_groups(cleaneddata)

        self._validate_custom_consents()

        return super(PatientForm, self).clean()

    def _validate_custom_consents(self):
        data = {}
        for field_key in self.custom_consents:
            parts = field_key.split("_")
            reg_pk = int(parts[1])
            registry_model = Registry.objects.get(id=reg_pk)
            if registry_model not in data:
                data[registry_model] = {}

            consent_section_pk = int(parts[2])
            consent_section_model = ConsentSection.objects.get(id=int(consent_section_pk))

            if consent_section_model not in data[registry_model]:
                data[registry_model][consent_section_model] = {}

            consent_question_pk = int(parts[3])
            consent_question_model = ConsentQuestion.objects.get(id=consent_question_pk)
            answer = self.custom_consents[field_key]
            data[registry_model][consent_section_model][consent_question_model.code] = answer

        validation_errors = []

        for registry_model in data:
            for consent_section_model in data[registry_model]:

                answer_dict = data[registry_model][consent_section_model]
                if not consent_section_model.is_valid(answer_dict):
                    error_message = "Consent Section '%s %s' is not valid" % (registry_model.code.upper(),
                                                                              consent_section_model.section_label)
                    validation_errors.append(error_message)

        if len(validation_errors) > 0:
            raise forms.ValidationError("Consent Error(s): %s" % ",".join(validation_errors))

    def save(self, commit=True):
        patient_model = super(PatientForm, self).save(commit=False)
        patient_model.active = True
        try:
            patient_registries = [r for r in patient_model.rdrf_registry.all()]
        except ValueError:
            # If patient just created line above was erroring
            patient_registries = []

        if "user" in self.cleaned_data:
            patient_model.user = self.cleaned_data["user"]

        if commit:
            patient_model.save()
            patient_model.working_groups.set(self.cleaned_data["working_groups"])
            # for wg in self.cleaned_data["working_groups"]:
            #    patient_model.working_groups.add(wg)

            for reg in self.cleaned_data["rdrf_registry"]:
                patient_model.rdrf_registry.add(reg)

            patient_model.save()

        patient_model.clinician = self.cleaned_data["clinician"]

        for consent_field in self.custom_consents:
            registry_model, consent_section_model, consent_question_model = self._get_consent_field_models(
                consent_field)

            if registry_model in patient_registries:
                # are we still applicable?! - maybe some field on patient changed which
                # means not so any longer?
                if consent_section_model.applicable_to(patient_model):
                    patient_model.set_consent(consent_question_model, self.custom_consents[consent_field], commit)
            if not patient_registries:
                closure = self._make_consent_closure(registry_model, consent_section_model, consent_question_model,
                                                     consent_field)
                if hasattr(patient_model, 'add_registry_closures'):
                    patient_model.add_registry_closures.append(closure)
                else:
                    setattr(patient_model, 'add_registry_closures', [closure])

        return patient_model

    def _make_consent_closure(self, registry_model, consent_section_model, consent_question_model, consent_field):
        def closure(patient_model, registry_ids):
            if registry_model.id in registry_ids:
                if consent_section_model.applicable_to(patient_model):
                    patient_model.set_consent(consent_question_model, self.custom_consents[consent_field])
            else:
                pass

        return closure

    def _check_working_groups(self, cleaned_data):
        def multiple_working_groups_allowed(reg_code):
            try:
                registry_model = Registry.objects.get(code=reg_code)
                return registry_model.has_feature("patients_multiple_working_groups")
            except Registry.DoesNotExist:
                return False

        working_group_data = {}
        for working_group in cleaned_data["working_groups"]:
            if working_group.registry:
                if working_group.registry.code not in working_group_data:
                    working_group_data[working_group.registry.code] = [working_group]
                else:
                    working_group_data[working_group.registry.code].append(working_group)

        bad = []
        for reg_code in working_group_data:
            if len(working_group_data[reg_code]) > 1 and not multiple_working_groups_allowed(reg_code):
                bad.append(reg_code)

        if bad:
            bad_regs = [Registry.objects.get(code=reg_code).name for reg_code in bad]
            raise forms.ValidationError(
                "Patient can only belong to one working group per registry. Patient is assigned to more than one working for %s"
                % ",".join(bad_regs))


class ParentGuardianForm(forms.ModelForm):
    class Meta:
        model = ParentGuardian
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'address', 'country', 'state', 'suburb', 'postcode',
            'phone'
        ]
        exclude = ['user', 'patient', 'place_of_birth', 'date_of_migration']

        widgets = {'state': StateWidget(), 'country': CountryWidget()}
