from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from models import WorkingGroup
from rdrf.models import Registry


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = get_user_model()
        fields = ('email',)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    request = None
    model = get_user_model()

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(UserChangeForm, self).__init__(*args, **kwargs)
        #self.fields['working_groups'].queryset = WorkingGroup.objects.filter(registry__in = self.request.user.working_groups.all())
        #self.fields['registry'].queryset = Registry.objects.filter(code__in = [reg.code for reg in self.request.user.registry.all()])


    password = ReadOnlyPasswordHashField(help_text=("Raw passwords are not stored, so there is no way to see "
                    "this user's password, but you can change the password "
                    "using <a href=\"password/\">this form</a>."))

    class Meta:
        model = get_user_model()


    def clean_password(self):
        return self.initial["password"]