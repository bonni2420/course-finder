from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Resource


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "thumbnail_preview", "course_link", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("title", "description", "course_link")
    autocomplete_fields = ("category",)
    readonly_fields = ("thumbnail_preview",)

    @admin.display(description="Thumbnail")
    def thumbnail_preview(self, obj: Resource) -> str:
        if not obj.thumbnail_url:
            return "-"
        return format_html(
            '<img src="{}" alt="{}" style="width: 160px; height: 100px; object-fit: cover; border-radius: 6px;" />',
            obj.thumbnail_url.url,
            obj.title,
        )
