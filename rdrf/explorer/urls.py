from django.conf.urls import patterns, url
from explorer.views import MainView
from explorer.views import QueryView, NewQueryView
from explorer.views import DeleteQueryView, DownloadQueryView
from explorer.views import SqlQueryView

urlpatterns = patterns(
    '',
    url(r'^query/(?P<query_id>\w+)/?$',
        QueryView.as_view(), name='explorer_query'),
    url(r'^query/download/(?P<query_id>\w+)/?$',
        DownloadQueryView.as_view(), name='explorer_query_download'),
    url(r'^query/delete/(?P<query_id>\w+)/?$',
        DeleteQueryView.as_view(), name='explorer_query_delete'),

    url(r'^sql$',
        SqlQueryView.as_view(), name='explorer_sql_query'),

    url(r'^new$', NewQueryView.as_view(), name='explorer_new'),

    url(r'$', MainView.as_view(), name='explorer_main'),
)
