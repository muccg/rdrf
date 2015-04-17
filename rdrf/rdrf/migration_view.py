from django.views.generic.base import View
from django.shortcuts import render_to_response, RequestContext

from django.db import connections

class MigrationView(View):

    def get(self, request):
        cursor = connections['legacydb'].cursor()
        cursor.execute("SELECT * FROM groups_workinggroup")
        context = {
            "legacy": cursor.fetchall(),
        }
        
        return render_to_response('rdrf_cdes/migration.html', context, context_instance=RequestContext(request))
        
