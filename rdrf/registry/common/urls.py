from django.conf.urls import patterns, url
import views

urlpatterns = patterns("",
    url(r"^test404/", views.test404),
    url(r"^test500/", views.test500),
)
