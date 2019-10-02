import logging

from django import forms

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.forms import ValidationError
from django.utils.translation import ugettext as _
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from useraudit import models as uam
from useraudit.middleware import get_request

from rdrf.auth import can_user_self_unlock


logger = logging.getLogger(__name__)


_login_failure_limit = getattr(settings, 'LOGIN_FAILURE_LIMIT', 0)

_msg_default = 'Please enter a correct %(username)s and password (case-sensitive).'
_msg_limit = ('For security reasons, accounts are temporarily locked after '
              '%(login_failure_limit)d incorrect attempts.' %
              {'login_failure_limit': _login_failure_limit})

# Making sure both text are available for translators indepenedent on the
# current LOGIN_FAILURE_LIMIT setting
_MSG_NO_LIMIT = _(_msg_default)
_MSG_WITH_LIMIT = _(_msg_default + ' ' + _msg_limit)


# Same as django.contrib.auth.forms.PasswordResetForm but also allows password reset functionality
# for inactive users if the Unlock Account feature is enabled and the user isn't explicitly prevented
# to unlock their account
class RDRFPasswordResetForm(PasswordResetForm):

    def get_users(self, email):
        if getattr(settings, 'ACCOUNT_SELF_UNLOCK_ENABLED', False):
            users = get_user_model()._default_manager.filter(
                prevent_self_unlock=False,
                email__iexact=email)
        else:
            users = get_user_model()._default_manager.filter(
                email__iexact=email, is_active=True)

        return (u for u in users if u.has_usable_password())


# Similar to django.contrib.auth.forms.PasswordResetForm but sends account unlock email link to the user.
# Also, sends a different email if the user tried to unlock their account
# but the account isn't locked.
class RDRFLoginAssistanceForm(PasswordResetForm):

    def get_users(self, email):
        return get_user_model()._default_manager.filter(email__iexact=email)

    def _common_context(
            self,
            domain_override=None,
            request=None,
            use_https=False,
            extra_email_context=None):
        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override
        context = {
            'domain': domain,
            'site_name': site_name,
            'protocol': 'https' if use_https else 'http',
        }
        if extra_email_context is not None:
            context.update(extra_email_context)
        return context

    def save(
            self,
            domain_override=None,
            subject_template_name='registration/login_assistance_subject.txt',
            email_template_name='registration/login_assistance_email.html',
            account_unlocked_email_template_name='registration/login_assistance_account_not_locked_email.html',
            can_not_self_unlock_email_template_name='registration/login_assistance_can_not_self_unlock_email.html',
            use_https=False,
            token_generator=default_token_generator,
            from_email=None,
            request=None,
            html_email_template_name=None,
            extra_email_context=None):

        email = self.cleaned_data["email"]
        context = self._common_context(
            request=request,
            domain_override=domain_override,
            use_https=use_https,
            extra_email_context=extra_email_context)

        def _choose_template(user):
            if user.is_active:
                return subject_template_name, account_unlocked_email_template_name
            if not can_user_self_unlock(user):
                return subject_template_name, can_not_self_unlock_email_template_name

            return subject_template_name, email_template_name

        for user in self.get_users(email):
            context.update({
                'email': user.email,
                'user': user,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': token_generator.make_token(user),
            })

            subject_template_name, template_name = _choose_template(user)
            self.send_mail(
                subject_template_name,
                template_name,
                context,
                from_email,
                user.email)


# Same as django.contrib.auth.forms.SetPasswordForm but also reactivates the user if it is inactive
# end ACCOUNT_SELF_UNLOCK_ENABLED is True
class RDRFSetPasswordForm(SetPasswordForm):

    def save(self, commit=True):
        super().save(commit=False)
        if not self.user.is_active:
            if getattr(settings, 'ACCOUNT_SELF_UNLOCK_ENABLED', False):
                if not self.user.prevent_self_unlock:
                    self.user.is_active = True
            else:
                logger.warning(
                    'User "%s" resetted their password but their account is inactive '
                    'and settings.ACCOUNT_SELF_UNLOCK_ENABLED is NOT set.', self.user.username)
            if not self.user.is_active:
                request = get_request()
                if request:
                    messages.add_message(
                        request, messages.ERROR, _(
                            'Your password has been changed, but your account is locked. '
                            'Please contact your registry owner for further information.'))
        if commit:
            self.user.save()
        return self.user


class UserVerificationForm(forms.Form):
    first_name = forms.CharField(label=_('First Name'), max_length=254)
    last_name = forms.CharField(label=_('Surname'), max_length=254)
    date_of_birth = forms.DateField(label=_("Date of Birth"), input_formats=['%Y-%m-%d'])

    def __init__(self, user_data, *args, **kwargs):
        self.user_data = user_data
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        date_of_birth = cleaned_data.get('date_of_birth')

        if first_name and last_name and date_of_birth:
            if not self.matches_data(first_name, last_name, date_of_birth):
                raise ValidationError(_("The data you've entered is incorrect"))

    def matches_data(self, first_name, last_name, date_of_birth):

        def laid_back_eql(s1, s2):
            return s1.strip().lower() == s2.strip().lower()

        return \
            laid_back_eql(first_name, self.user_data['first_name']) and \
            laid_back_eql(last_name, self.user_data['last_name']) and \
            (date_of_birth == self.user_data['date_of_birth'])


class ReactivateAccountForm(SetPasswordForm):

    def __init__(self, request, user, is_password_change_required, *args, **kwargs):
        self.request = request
        self.is_password_change_required = is_password_change_required
        super().__init__(user, *args, **kwargs)

    def clean(self):
        if self.is_password_change_required and not self.cleaned_data.get('new_password1'):
            raise ValidationError(_('You are required to change your password.'))

    def is_valid(self):
        is_valid = super().is_valid()
        if not self.is_password_change_required and \
                not self.request.POST.get('new_password1') and \
                not self.request.POST.get('new_password2'):
            return True
        return is_valid

    def save(self, commit=True):
        if self.cleaned_data.get('new_password1'):
            super().save(commit=False)
        self.user.is_active = True
        if commit:
            self.user.save()
        return self.user


def extract_ip_address(request):
    ll = uam.LoginLogger()
    ip, _ = ll.extract_ip_address(request)
    return ip
