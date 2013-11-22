from django import forms
from django.contrib.auth.models import Group
from models import User, WorkingGroup

from rdrf.models import Registry


class ChangePasswordForm(forms.Form):
    password = forms.CharField(max_length=100, widget=forms.PasswordInput)
    confirm_password = forms.CharField(max_length=100, widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = self.cleaned_data
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password != confirm:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data


class UserChangeForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    email_address = forms.EmailField(label="E-mail address")
    title = forms.CharField(max_length=50, label="Position")
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all())
    working_group = forms.ModelMultipleChoiceField(queryset=WorkingGroup.objects.all())
    registry = forms.ModelMultipleChoiceField(queryset=Registry.objects.all())

    def __init__(self, user, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        self.user = user
        if not self.user.is_superuser:
            working_group = User.objects.get(user=self.user).working_groups.all()
            if working_group:
                self.fields["working_group"] = forms.ModelMultipleChoiceField(queryset=User.objects.get(user=self.user).working_groups.all())

    def clean_working_group(self):
        if not self.user.is_superuser:
            user = User.objects.get(user=self.user)

#            if self.cleaned_data["working_group"] != user.working_group:
#                raise forms.ValidationError("Cannot add a user to another working group.")

        return self.cleaned_data["working_group"]


class UserNewForm(UserChangeForm):
    username = forms.CharField(max_length=100)
    password = forms.CharField(max_length=100, widget=forms.PasswordInput)
    confirm_password = forms.CharField(max_length=100, widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        super(UserNewForm, self).__init__(user, *args, **kwargs)
        self.fields.keyOrder = [
            "username",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "email_address",
            "title",
            "groups",
            "working_group",
            "registry"
        ]

    def clean(self):
        cleaned_data = self.cleaned_data
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password != confirm:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data
