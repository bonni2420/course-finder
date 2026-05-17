from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path, PurePosixPath
from typing import Iterable
from zipfile import ZIP_DEFLATED, ZipFile, is_zipfile

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.files.uploadedfile import UploadedFile
from django.core.management import call_command
from django.db import connection, models, transaction
from django.utils import timezone

FIXTURE_NAME = "course_finder_system_data.json"
MANIFEST_NAME = "backup_manifest.json"
MEDIA_PREFIX = "media/"
SQLITE_DATABASE_NAME = "database/db.sqlite3"


@dataclass(frozen=True)
class SystemBackupImportResult:
    object_count: int
    media_file_count: int


def iter_backup_models() -> list[type[models.Model]]:
    backup_models = []
    for model in apps.get_models():
        if model._meta.proxy or model._meta.auto_created:
            continue
        backup_models.append(model)

    return backup_models


def build_system_fixture_json() -> str:
    output = StringIO()
    call_command(
        "dumpdata",
        format="json",
        indent=2,
        use_natural_foreign_keys=True,
        use_natural_primary_keys=True,
        use_base_manager=True,
        stdout=output,
    )
    return output.getvalue()


def build_system_backup_zip() -> tuple[str, bytes]:
    timestamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    file_name = f"course-finder-system-backup-{timestamp}.zip"

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr(FIXTURE_NAME, build_system_fixture_json())
        zip_file.writestr(MANIFEST_NAME, build_backup_manifest_json())
        write_sqlite_database_copy(zip_file)
        for media_path in iter_media_files():
            archive_name = MEDIA_PREFIX + media_path.relative_to(settings.MEDIA_ROOT).as_posix()
            zip_file.write(media_path, archive_name)

    return file_name, buffer.getvalue()


def build_backup_manifest_json() -> str:
    return json.dumps(
        {
            "created_at": timezone.localtime().isoformat(),
            "fixture": FIXTURE_NAME,
            "models": build_model_manifest(),
            "database_tables": build_database_table_manifest(),
            "notes": [
                "The JSON fixture contains rows for all Django model-backed tables.",
                "Empty tables appear in this manifest with row_count 0.",
                "django_migrations is listed in database_tables but is not imported from the fixture; run migrations before importing.",
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


def build_model_manifest() -> list[dict[str, str | int]]:
    manifest = []
    for model in iter_backup_models():
        manifest.append(
            {
                "model": model._meta.label_lower,
                "table": model._meta.db_table,
                "row_count": model._base_manager.count(),
            }
        )
    return manifest


def build_database_table_manifest() -> list[dict[str, str | int]]:
    tables = []
    existing_tables = connection.introspection.table_names()
    with connection.cursor() as cursor:
        for table_name in sorted(existing_tables):
            cursor.execute(f"SELECT COUNT(*) FROM {connection.ops.quote_name(table_name)}")
            row_count = cursor.fetchone()[0]
            tables.append({"table": table_name, "row_count": row_count})
    return tables


def write_sqlite_database_copy(zip_file: ZipFile) -> None:
    if connection.vendor != "sqlite":
        return

    db_name = settings.DATABASES["default"].get("NAME")
    if not db_name:
        return

    db_path = Path(db_name)
    if db_path.exists() and db_path.is_file():
        zip_file.write(db_path, SQLITE_DATABASE_NAME)


def iter_media_files() -> Iterable[Path]:
    media_root = Path(settings.MEDIA_ROOT)
    if not media_root.exists():
        return

    for path in media_root.rglob("*"):
        if path.is_file():
            yield path


def import_system_backup(uploaded_file: UploadedFile) -> SystemBackupImportResult:
    uploaded_bytes = b"".join(uploaded_file.chunks())
    if not is_zipfile(BytesIO(uploaded_bytes)):
        raise ValueError("Backup file must be a ZIP exported from the system data backup page.")

    fixture_json, media_file_count = read_system_backup_zip(uploaded_bytes)

    with transaction.atomic():
        clear_existing_backup_models()
        object_count = 0
        for deserialized_object in serializers.deserialize(
            "json",
            fixture_json,
            handle_forward_references=True,
        ):
            deserialized_object.save()
            object_count += 1

    extract_system_backup_media(uploaded_bytes)
    return SystemBackupImportResult(object_count=object_count, media_file_count=media_file_count)


def clear_existing_backup_models() -> None:
    for model in reversed(iter_backup_models()):
        model._default_manager.all().delete()


def read_system_backup_zip(uploaded_bytes: bytes) -> tuple[str, int]:
    media_file_count = 0
    with ZipFile(BytesIO(uploaded_bytes)) as zip_file:
        fixture_json = zip_file.read(FIXTURE_NAME).decode("utf-8")
        for member in zip_file.infolist():
            if member.is_dir() or not member.filename.startswith(MEDIA_PREFIX):
                continue
            media_file_count += 1

    return fixture_json, media_file_count


def extract_system_backup_media(uploaded_bytes: bytes) -> None:
    with ZipFile(BytesIO(uploaded_bytes)) as zip_file:
        for member in zip_file.infolist():
            if member.is_dir() or not member.filename.startswith(MEDIA_PREFIX):
                continue
            extract_media_member(zip_file, member.filename)


def extract_media_member(zip_file: ZipFile, member_name: str) -> None:
    relative_name = PurePosixPath(member_name).relative_to(MEDIA_PREFIX)
    destination = safe_media_path(relative_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(zip_file.read(member_name))


def safe_media_path(relative_name: PurePosixPath) -> Path:
    media_root = Path(settings.MEDIA_ROOT).resolve()
    destination = (media_root / Path(*relative_name.parts)).resolve()

    if media_root != destination and media_root not in destination.parents:
        raise ValueError("Unsafe media file path in backup.")

    return destination
