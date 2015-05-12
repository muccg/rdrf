from django.views.generic.edit import FormView
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render_to_response
from django.template import RequestContext

from admin_forms import UserChangeForm
from models import CustomUser

class CustomUserView(FormView):
    model = CustomUser
    form_class = UserChangeForm
    template_name = "admin/change_form.html"
   
    def get_form_kwargs(self, **kwargs):
        kwargs = super(CustomUserView, self).get_form_kwargs(**kwargs)
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(CustomUserView, self).get_context_data(**kwargs)
        context['opts'] = self.model._meta
        context['app_label'] = self.model._meta.app_label
        context['change'] = True
        context['is_popup'] = False
        context['save_as'] = True
        context['has_delete_permission'] = True
        context['has_add_permission'] = True
        context['has_change_permission'] = True
        context['add'] = False
        return context
