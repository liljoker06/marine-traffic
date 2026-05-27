from django.urls import path

from . import views

urlpatterns = [
    path("ports/", views.ports_list, name="ports_list"),
    path("api/ports/", views.ports_api, name="ports_api"),
]
