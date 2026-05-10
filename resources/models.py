from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name


class Resource(models.Model):
    title = models.CharField(max_length=255)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    course_link = models.URLField(max_length=500)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="resources",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
