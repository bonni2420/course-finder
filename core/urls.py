from django.urls import path

from core.views import home, resource_detail, robots_txt, sitemap_xml

app_name = "core"

urlpatterns = [
    path("", home, name="home"),
    path("danh-muc/<int:category_pk>-<slug:category_slug>/", home, name="category_detail"),
    path("khoa-hoc/<int:pk>-<slug:slug>/", resource_detail, name="resource_detail"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
]
