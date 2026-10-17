from django.urls import path

from . import views

urlpatterns = [
    path("agents/", views.agents, name="agents"),
    path("branches/", views.branches, name="branches"),
]
