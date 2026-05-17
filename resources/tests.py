import os
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from resources.models import Category, Resource


class ResourceThumbnailCleanupTests(TestCase):
    def setUp(self) -> None:
        self.media_root = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_root.name)
        self.override.enable()
        self.category = Category.objects.create(name="Python")

    def tearDown(self) -> None:
        self.override.disable()
        self.media_root.cleanup()

    def test_replacing_thumbnail_deletes_old_file(self) -> None:
        resource = Resource.objects.create(
            title="Django Basics",
            thumbnail_url=SimpleUploadedFile("first.jpg", b"first image"),
            description="",
            course_link="https://example.com/django",
            category=self.category,
        )
        old_file_path = resource.thumbnail_url.path

        resource.thumbnail_url = SimpleUploadedFile("second.jpg", b"second image")
        resource.save()

        self.assertFalse(os.path.exists(old_file_path))
        self.assertTrue(os.path.exists(resource.thumbnail_url.path))

    def test_deleting_resource_deletes_thumbnail_file(self) -> None:
        resource = Resource.objects.create(
            title="Django Advanced",
            thumbnail_url=SimpleUploadedFile("advanced.jpg", b"advanced image"),
            description="",
            course_link="https://example.com/advanced",
            category=self.category,
        )
        thumbnail_path = resource.thumbnail_url.path

        resource.delete()

        self.assertFalse(os.path.exists(thumbnail_path))
