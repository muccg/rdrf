import logging

from django.contrib import messages
from django.contrib.auth import get_user_model

from django.contrib.auth.decorators import login_required
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.forms import SetPasswordForm

from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ObjectDoesNotExist
from django.dispatch import receiver
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from two_factor import views as tfv
from two_factor.utils import default_device

from useraudit.models import UserDeactivation
from useraudit.password_expiry import is_password_expired

from registry.patients.models import Patient, ParentGuardian

from . import can_user_self_unlock, is_user_privileged
from .forms import UserVerificationForm, RDRFSetPasswordForm, ReactivateAccountForm


logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def user_login_callback(sender, request=None, user=None, **kwargs):
    if is_user_privileged(
            user) and not user.require_2_fact_auth and default_device(user) is None:
        link = ('<a href="%(url)s" class="alert-link">' + _('click here') +
                '</a>') % {'url': reverse('two_factor:setup')}
        msg = mark_safe(
            _('We strongly recommend that you protect your account with Two-Factor authentication. '
              'Please %(link)s to set it up.') % {'link': link})

        if msg not in [m.message for m in messages.get_messages(request)]:
            messages.info(request, msg)


# Customised Two Factor views


@tfv.utils.class_view_decorator(never_cache)
@tfv.utils.class_view_decorator(login_required)
class QRGeneratorView(tfv.core.QRGeneratorView):
    session_key_name = 'two_fact_auth_key'


@tfv.utils.class_view_decorator(never_cache)
@tfv.utils.class_view_decorator(login_required)
class SetupView(tfv.core.SetupView):
    session_key_name = 'two_fact_auth_key'


# Doesn't need csrf_protect since no-one can guess the URL
@sensitive_post_parameters()
@never_cache
def login_assistance_confirm(request, uidb64=None, token=None):

    UserModel = get_user_model()
    assert uidb64 is not None and token is not None  # checked by URLconf
    try:
        # urlsafe_base64_decode() decodes to bytestring on Python 3
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = UserModel._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
        user = None

    form = None
    template_name = 'registration/login_assistance_verify_user.html'
    validlink = user is not None and default_token_generator.check_token(user, token)

    error_context = {
        'title': _('Login self assistance confirmation unsuccessful'),
        'hideVerification': True,
    }

    # There are multiple steps, all handled by this view:

    # Step 1
    # First the user is following the link they've received in the email.
    # If the link expired, is wrong we will just display an error.
    if not validlink:
        messages.error(
            request,
            _('The link is invalid, possibly because it has already been used. Please try requesting a new link.'))
        return TemplateResponse(request, template_name, error_context)

    if not can_user_self_unlock(user):
        messages.warning(
            request,
            _("Unfortunately the system can't verify your identity. Please contact the registry owners for further information."))
        return TemplateResponse(request, template_name, error_context)

    # If the link is correct and the user hasn't been verified yet
    # we will verify the user's identity by asking them for information like
    # Name and Date of Birth

    def user_needs_verification():
        verification = request.session.get('user_verified', {})
        return not (verification.get('uidb64') == uidb64 and verification.get('token') == token)

    if user_needs_verification():
        user_data = _get_users_verification_data(user)

        def verification_page(form=None):
            context = {
                'title': _('Verify User'),
                'form': form,
            }
            return TemplateResponse(
                request, 'registration/login_assistance_verify_user.html', context)

        if request.method != 'POST':
            if user_data is None:
                messages.warning(
                    request,
                    _("Unfortunately we don't have the required information to verify your identity. Please contact the registry owners for assistance."))
                return TemplateResponse(request, template_name, error_context)
            return verification_page()

        else:
            # Verify the data POSTed by the user
            # In case the verification succeeds we save the token in the session, so that the user can progress to
            # the next phase by just revisiting the same page
            form = UserVerificationForm(user_data, request.POST)
            if form.is_valid():
                request.session['user_verified'] = {
                    'uidb64': uidb64,
                    'token': token,
                }
                # Redirect to the same page for the next phase
                return HttpResponseRedirect(reverse('login_assistance_confirm',
                                                    kwargs={'uidb64': uidb64, 'token': token}))
            else:
                # User verification failed, display same page with errors
                return verification_page(form)

    # The user has been verified now.
    # We will display the reason why they have been locked out and require them to set a new password if
    # their password expired, or allow them to optionally set a new password in all other cases.

    deactivation = UserDeactivation.objects.filter(username=user.username).first()
    deactivation_reason = deactivation.reason if deactivation is not None else None

    DEFAULT_REASON_TEXT = _('Your account is currently locked.')
    REASON_TEXTS = {
        UserDeactivation.ACCOUNT_EXPIRED:
            _('Your account is suspended because your account was inactive for too long.'),
        UserDeactivation.PASSWORD_EXPIRED:
            _('Your account is suspended because your password expired.'),
        UserDeactivation.TOO_MANY_FAILED_LOGINS:
            _('Your account is suspended because you (or someone else) entered an incorrect password too many times.')
    }
    reason = REASON_TEXTS.get(deactivation_reason, DEFAULT_REASON_TEXT)

    def is_password_change_required(user):
        # If the password has expired always make them change their password or they will
        # be locked out when they try to log in next time.
        return deactivation_reason == UserDeactivation.PASSWORD_EXPIRED or is_password_expired(
            user)

    def user_is_verified_page(form=None):
        context = {
            'title': _('Reactivate account'),
            'form': form,
            'reason': reason,
            'password_change_required': is_password_change_required(user),
        }
        return TemplateResponse(
            request,
            'registration/login_assistance_user_verified.html',
            context)

    if request.method != 'POST':
        # Display deactivation reason and allow/require them to change password
        return user_is_verified_page()
    else:
        # Validate the new password the user POSTed (if supplied) and activate the user
        form = ReactivateAccountForm(
            request,
            user,
            is_password_change_required(user),
            request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('login_assistance_complete'))
        else:
            return user_is_verified_page(form)


def _get_users_dob(user):
    try:
        parent = ParentGuardian.objects.get(user=user)
        return parent.date_of_birth
    except ParentGuardian.DoesNotExist:
        pass
    try:
        patient = Patient.objects.get(user=user)
        return patient.date_of_birth
    except Patient.DoesNotExist:
        pass
    return None


def _get_users_verification_data(user):
    dob = _get_users_dob(user)
    if dob is None:
        return None
    return {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'date_of_birth': dob,
    }
