from django.shortcuts import render_to_response, RequestContext, redirect
from django.views.generic.base import View
from django.core.urlresolvers import reverse

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from explorer.models import Query


class LoginRequiredMixin(object):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class ReportView(LoginRequiredMixin, View):
    
    def get(self, request):
        user = request.user
        
        reports = None
        
        if user.is_superuser:
            reports = Query.objects.all()
        elif user.is_curator:
            reports = Query.objects.filter(registry__in = [reg.id for reg in user.get_registries()]).filter(access_group__in = [g.id for g in user.get_groups()])
        
        context = {}
        context['reports'] = reports
        context["location"] = 'Reports'
    
        return render_to_response('rdrf_cdes/reports.html', context, context_instance=RequestContext(request))
