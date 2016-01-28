from django.shortcuts import render_to_response, RequestContext
from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect
from django.http import Http404

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
            reports = Query.objects.filter(
                registry__in=[
                    reg.id for reg in user.get_registries()]).filter(
                access_group__in=[
                    g.id for g in user.get_groups()])

        context = {}
        context['reports'] = reports
        context["location"] = 'Reports'
        return render_to_response(
            'rdrf_cdes/reports.html',
            context,
            context_instance=RequestContext(request))


class ReportDataTableView(LoginRequiredMixin, View):
    def get(self, request, query_model_id):
        user = request.user
        try:
            query_model = Query.objects.get(pk=query_model_id)
        except Query.DoesNotExist:
            raise Http404("Report %s does not exist" % query_model_id)

        if not self._sanity_check(query_model, user):
            return HttpResponseRedirect("/")

        table_name = "report_%s_%s" % (query_model_id, user.pk)
        context = {}
        context["location"] = 'Reports'
        context["columns"] = []
        return render_to_response(
            'rdrf_cdes/report_table_view.html',
            context,
            context_instance=RequestContext(request))

    def sanity_check(self, query_model, user):
        #todo sanity check
        return True


    def post(self, request):
        pass




