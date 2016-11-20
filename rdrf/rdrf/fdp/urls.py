from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'catalog/(?P<registry_code>\w+)/?$', views.FDPCatalogView.as_view(), name='catalog'),
    url(r'dataset/(?P<registry_code>\w+)/?$', views.FDPDatasetView.as_view(), name='dataset'),
    url(r'distribution/(?P<registry_code>\w+)/?$', views.FDPDistributionView.as_view(), name='distribution'),
    url(r'patients/(?P<registry_code>\w+)/?$', views.FDPPatientView.as_view(), name='patient'),
    url(r'', views.FDPRootView.as_view(), name='fdp'),
]
