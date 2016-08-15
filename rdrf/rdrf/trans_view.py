import os

from django.shortcuts import render_to_response, RequestContext, redirect
from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import translation
from django.utils.translation import trans_real, get_language

import polib

import logging
logger = logging.getLogger("registry_log")


class TranslationViewReload(View):

    @method_decorator(login_required)
    def get(self, request, country_code):
        return redirect(reverse("translate", kwargs={'country_code': country_code}))


class TranslationView(View):

    @method_decorator(login_required)
    def get(self, request, country_code):
        context = dict()

        po = polib.pofile(self._get_po_file_path(country_code, "django.po"))

        translations = []

        for entry in po:
            translations.append({
                "msgid": entry.msgid,
                "msgstr": entry.msgstr
            })

        context["translations"] = translations
        context["country_code"] = country_code

        return render_to_response(
            "rdrf_cdes/translation.html",
            context,
            context_instance=RequestContext(request)
        )

    @method_decorator(login_required)
    def post(self, request, country_code):
        po = polib.pofile(self._get_po_file_path(country_code, "django.po"))

        for entry in po:
            for trans_msgid, trans_msgstr in request.POST.iteritems():
                if trans_msgid in entry.msgid:
                    entry.msgstr = trans_msgstr

        po.save(self._get_po_file_path(country_code, "django.po"))
        po.save_as_mofile(self._get_po_file_path(country_code, "django.mo"))

        trans_real._translations = {}
        trans_real._default = None
        translation.activate(get_language())

        return redirect(reverse("translate", kwargs={'country_code': country_code}))

    def _get_po_file_path(self, country_code, file_name):
        path = settings.LOCALE_PATHS[0]
        return os.path.join(path, country_code, "LC_MESSAGES", file_name)
