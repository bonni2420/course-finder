from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        slug = slugify(self.name) or "danh-muc"
        return reverse("core:category_detail", kwargs={"category_pk": self.pk, "category_slug": slug})


class Resource(models.Model):
    title = models.CharField(max_length=255)
    thumbnail_url = models.ImageField(
        upload_to="resource_thumbnails/",
        blank=True,
        verbose_name="Thumbnail",
    )
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

    def get_absolute_url(self) -> str:
        slug = slugify(self.title) or "khoa-hoc"
        return reverse("core:resource_detail", kwargs={"pk": self.pk, "slug": slug})
