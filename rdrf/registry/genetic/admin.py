import json

from django.conf.urls import url
from django.contrib import admin
from django.db.models import Q
from django.http import HttpResponse

from .models import (
    Gene,
    Laboratory)


class GeneAdmin(admin.ModelAdmin):
    list_display = ["symbol", "name", "status", "chromosome"]
    search_fields = ["symbol", "name"]

    def get_urls(self):
        search_url = url(r"search/(.*)$", self.admin_site.admin_view(self.search),
                         name="gene_search")
        return [search_url] + super(GeneAdmin, self).get_urls()

    def search(self, request, term):
        genes = Gene.objects.filter(
            Q(name__icontains=term) | Q(symbol__icontains=term)).order_by("symbol")
        response = [[gene.id, gene.symbol, gene.name] for gene in genes]

        return HttpResponse(json.dumps(response), content_type="application/json")


class LaboratoryAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "contact_name",
                    "contact_email", "contact_phone")
    fieldsets = ((None, {"fields": ("name", "address")}),
                 ("Contact", {"fields": ("contact_name",
                                         "contact_email",
                                         "contact_phone")}))

    def get_urls(self):
        search_url = url(r"search/(.*)$", self.admin_site.admin_view(self.search),
                         name="laboratory_search")
        return [search_url] + super(LaboratoryAdmin, self).get_urls()

    def get_queryset(self, request):
        return Laboratory.objects.all()

    def search(self, request, term):
        queryset = self.queryset(request)

        queryset = queryset.filter(
            Q(name__icontains=term) | Q(address__icontains=term) | Q(contact_name__icontains=term))
        queryset = queryset.order_by("name")
        response = [[str(lab)] for lab in queryset]

        return HttpResponse(json.dumps(response), content_type="application/json")


admin.site.register(Gene, GeneAdmin)
admin.site.register(Laboratory, LaboratoryAdmin)
