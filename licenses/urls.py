from django.urls import path

from . import views

urlpatterns = [
    path("activate/", views.activate, name="license_activate"),
    path("validate/", views.validate, name="license_validate"),
]
