from django.contrib import admin

from .models import Category, Resource


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "course_link", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("title", "description", "course_link")
    autocomplete_fields = ("category",)
