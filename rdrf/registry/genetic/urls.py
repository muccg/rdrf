from django.conf.urls import patterns, url
import views

urlpatterns = patterns("",
    url(r"^variation/", views.entry, name="entry"),
)
