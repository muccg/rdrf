from django.urls import re_path
from explorer.views import MainView
from explorer.views import QueryView, NewQueryView
from explorer.views import DeleteQueryView, DownloadQueryView
from explorer.views import SqlQueryView

app_name = 'rdrf'

urlpatterns = [
    re_path(r'^query/(?P<query_id>\w+)/?$',
            QueryView.as_view(), name='explorer_query'),
    re_path(r'^query/download/(?P<query_id>\w+)?/(?P<action>\w+)?/?$',
            DownloadQueryView.as_view(), name='explorer_query_download'),
    re_path(r'^query/delete/(?P<query_id>\w+)/?$',
            DeleteQueryView.as_view(), name='explorer_query_delete'),

    re_path(r'^sql$',
            SqlQueryView.as_view(), name='explorer_sql_query'),

    re_path(r'^new$', NewQueryView.as_view(), name='explorer_new'),

    re_path(r'$', MainView.as_view(), name='explorer_main'),
]
