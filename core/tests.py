import os
import json
import tempfile
from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings

from core.services.system_backup_service import (
    FIXTURE_NAME,
    MANIFEST_NAME,
    build_system_backup_zip,
    import_system_backup,
)
from resources.models import Category, Resource


class HomeViewTests(TestCase):
    def setUp(self) -> None:
        python = Category.objects.create(name="Python")
        design = Category.objects.create(name="Design")
        for idx in range(15):
            Resource.objects.create(
                title=f"Django Course {idx}",
                description="Backend web development",
                course_link=f"https://example.com/django-{idx}",
                category=python,
            )
        Resource.objects.create(
            title="Color Systems",
            description="Visual design foundations",
            course_link="https://example.com/design",
            category=design,
        )

    def test_home_renders_course_cards(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Course Finder")
        self.assertContains(response, "Django Course")
        self.assertContains(response, "Mở bài học")

    def test_home_search_filters_resources(self) -> None:
        response = self.client.get("/", {"q": "Color"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Color Systems")
        self.assertNotContains(response, "Django Course 0")

    def test_home_category_filter_filters_resources(self) -> None:
        design = Category.objects.get(name="Design")

        response = self.client.get("/", {"category": design.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Color Systems")
        self.assertContains(response, "Tất cả")
        self.assertNotContains(response, "Django Course 0")

    def test_home_query_count_is_stable_for_resource_grid(self) -> None:
        with self.assertNumQueries(3):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)


class SystemBackupTests(TestCase):
    def setUp(self) -> None:
        self.media_root = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_root.name)
        self.override.enable()

    def tearDown(self) -> None:
        self.override.disable()
        self.media_root.cleanup()

    def create_sample_data(self) -> None:
        group = Group.objects.create(name="Editors")
        user = User.objects.create_user(
            username="admin_sample",
            email="admin@example.com",
            password="secret",
        )
        user.groups.add(group)

        category = Category.objects.create(name="Python")
        Resource.objects.create(
            title="Django Basics",
            thumbnail_url=SimpleUploadedFile("first.jpg", b"first image"),
            description="",
            course_link="https://example.com/django",
            category=category,
        )

    def test_backup_zip_contains_system_fixture_and_media(self) -> None:
        self.create_sample_data()

        file_name, backup_bytes = build_system_backup_zip()

        self.assertTrue(file_name.endswith(".zip"))
        with ZipFile(BytesIO(backup_bytes)) as zip_file:
            self.assertIn(FIXTURE_NAME, zip_file.namelist())
            self.assertIn(MANIFEST_NAME, zip_file.namelist())
            self.assertIn("media/resource_thumbnails/first.jpg", zip_file.namelist())
            if connection.vendor == "sqlite" and os.path.exists(connection.settings_dict["NAME"]):
                self.assertIn("database/db.sqlite3", zip_file.namelist())

            fixture_json = zip_file.read(FIXTURE_NAME).decode("utf-8")
            manifest = json.loads(zip_file.read(MANIFEST_NAME).decode("utf-8"))

            self.assertIn('"model": "auth.user"', fixture_json)
            self.assertIn('"model": "auth.group"', fixture_json)
            self.assertIn('"model": "auth.permission"', fixture_json)
            self.assertIn('"model": "contenttypes.contenttype"', fixture_json)
            self.assertIn('"model": "resources.resource"', fixture_json)
            self.assertIn("django_migrations", {table["table"] for table in manifest["database_tables"]})

    def test_import_system_backup_replaces_data_and_restores_media(self) -> None:
        self.create_sample_data()
        _, backup_bytes = build_system_backup_zip()

        Category.objects.create(name="Old Category")
        User.objects.create_user(username="old_user")

        result = import_system_backup(SimpleUploadedFile("backup.zip", backup_bytes))

        resource = Resource.objects.get(title="Django Basics")
        restored_user = User.objects.get(username="admin_sample")

        self.assertEqual(result.media_file_count, 1)
        self.assertTrue(result.object_count >= 4)
        self.assertTrue(os.path.exists(resource.thumbnail_url.path))
        self.assertTrue(restored_user.groups.filter(name="Editors").exists())
        self.assertFalse(Category.objects.filter(name="Old Category").exists())
        self.assertFalse(User.objects.filter(username="old_user").exists())
