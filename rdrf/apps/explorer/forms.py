from django.forms import ModelForm
from .models import Query


class QueryForm(ModelForm):

    class Meta:
        model = Query
        fields = [
            'id',
            'title',
            'description',
            'registry',
            'access_group',
            'collection',
            'criteria',
            'projection',
            'aggregation',
            'mongo_search_type',
            'sql_query',
            'max_items',
            'created_by'
        ]
