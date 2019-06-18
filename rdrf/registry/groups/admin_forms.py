from django.contrib.auth.password_validation import validate_password
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.forms import ChoiceField
from .models import WorkingGroup
from rdrf.models.definition.models import Registry
from rdrf.helpers.utils import get_supported_languages
from django.core.exceptions import ValidationError
import logging


logger = logging.getLogger(__name__)


class UserValidationMixin(object):

    def clean(self):
        # When the registry and/or working groups are selected, validate the selection is consistent.
        # We will prevent having a user who:
        # a) has been assigned a registry but not assigned to a working group of that registry
        # b) has been assigned to a working group but not assigned to the owning registry
        #    of that working group.
        registry_models = self.cleaned_data.get("registry", [])
        working_group_models = self.cleaned_data.get("working_groups", [])

        if len(registry_models) == 0 and len(working_group_models) == 0:
            # Registries and working groups not selected. Don't check for consistency.
            return self.cleaned_data

        for working_group_model in working_group_models:
            if working_group_model.registry not in registry_models:
                msg = "Working Group '%s' not in any of the assigned registries" % working_group_model.display_name
                raise ValidationError(msg)

        for registry_model in registry_models:
            if registry_model not in [
                    working_group_model.registry for working_group_model in working_group_models]:
                msg = "You have added the user into registry %s but not assigned the user " \
                      "to working group of that registry" % registry_model
                raise ValidationError(msg)

        if not registry_models:
            raise ValidationError("Please choose a registry")

        if not working_group_models:
            raise ValidationError("Please choose a working group")

        return self.cleaned_data


class RDRFUserCreationForm(UserValidationMixin, forms.ModelForm):
    # set by admin class - used to restrict registry and workign group choices
    CREATING_USER = None
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Password confirmation', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super(RDRFUserCreationForm, self).__init__(*args, **kwargs)
        if self.CREATING_USER:
            self._restrict_registry_and_working_groups_choices(
                self.CREATING_USER)

    class Meta:
        model = get_user_model()
        fields = ('email',)

    def clean_password2(self):
        password2 = self.cleaned_data.get("password2")

        validate_password(password2)
        return password2

    def clean_username(self):
        if "username" in self.cleaned_data:
            username = self.cleaned_data["username"]
            if not username:
                raise forms.ValidationError("username cannot be blank")
            try:
                get_user_model().objects.get(username=username)
                raise forms.ValidationError(
                    'There is already a user with that username!')
            except get_user_model().DoesNotExist:
                return username
        else:
            raise forms.ValidationError("username cannot be blank")

    def save(self, commit=True):
        user = super(RDRFUserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

    def _restrict_registry_and_working_groups_choices(self, creating_user):
        if not creating_user.is_superuser:
            self.fields['working_groups'].queryset = \
                WorkingGroup.objects.filter(
                    id__in=[wg.id for wg in creating_user.working_groups.all()])
            self.fields['registry'].queryset = \
                Registry.objects.filter(
                    code__in=[reg.code for reg in creating_user.registry.all()])


class UserChangeForm(UserValidationMixin, forms.ModelForm):
    model = get_user_model()

    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        if not self.user.is_superuser:
            self.fields['working_groups'].queryset = WorkingGroup.objects.filter(
                id__in=[wg.id for wg in self.user.working_groups.all()])
            self.fields['registry'].queryset = Registry.objects.filter(
                code__in=[reg.code for reg in self.user.registry.all()])
        password = self.fields.get('password')
        if password:
            password.help_text = password.help_text.format('../password/')

    from django.contrib.auth.forms import UserChangeForm as OldUserChangeForm
    password = ReadOnlyPasswordHashField(
        help_text=(OldUserChangeForm.base_fields['password'].help_text))

    preferred_language = ChoiceField(choices=get_supported_languages())

    class Meta:
        fields = "__all__"
        model = get_user_model()

    def clean_password(self):
        return self.initial["password"]
