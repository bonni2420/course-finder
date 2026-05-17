# AGENT.md

This file is the working memory for coding agents and developers in this project.
Update it whenever code changes meaningfully so the next session understands the latest source state.

## Project Overview

Course Finder is a Django project for managing learning resources in Django admin and exposing them through a Telegram bot webhook.

Main apps:

- `course_finder`: Django project settings and root URLs.
- `resources`: course categories and resources.
- `telegram`: Telegram webhook, command handling, and Bot API client.
- `core`: static files and management commands.
- `analytics`: currently present as an app folder, not yet wired into active flows.

## Current Source State

- Django uses `.env` through `python-dotenv`.
- `ALLOWED_HOSTS` is read from `.env`.
- `CSRF_TRUSTED_ORIGINS` is read from `.env`; needed for ngrok POST requests.
- Media uploads are enabled with:
  - `MEDIA_URL = "/media/"`
  - `MEDIA_ROOT = BASE_DIR / "media"`
  - `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` in `course_finder/urls.py` when `DEBUG=True`.
- Django admin uses `django-jazzmin` for the admin theme.
- `Resource.thumbnail_url` is an `ImageField`, despite the historical field name.
  - Upload path: `media/resource_thumbnails/`
  - DB stores the uploaded file path/name, not an external URL.
  - Old thumbnail files are deleted automatically when the resource thumbnail is replaced.
  - Thumbnail files are deleted automatically when the resource is deleted.
- `Pillow` is required for image uploads and is listed in `requirements.txt`.
- Migration `resources.0002_alter_resource_thumbnail_url` changes `thumbnail_url` from `URLField` to `ImageField`.

## Models

`resources.models.Category`

- `name`
- `description`
- ordered by `name`

`resources.models.Resource`

- `title`
- `thumbnail_url`: `ImageField(upload_to="resource_thumbnails/", blank=True)`
- `description`
- `course_link`
- `category`
- `created_at`
- `updated_at`
- ordered by newest first

Note: `thumbnail_url` is kept as the field name to avoid wider code churn, but it now stores an uploaded file path.

## Admin

`resources.admin.ResourceAdmin`

- Shows resource list with a larger thumbnail preview.
- Allows uploading `thumbnail_url` through Django admin.
- Uses `autocomplete_fields = ("category",)`.

Jazzmin admin theme settings live in:

- `course_finder.settings.JAZZMIN_SETTINGS`
- `course_finder.settings.JAZZMIN_UI_TWEAKS`
- The Jazzmin header menu includes `Data backup`, linking to `/admin/data-backup/`.

## Data Backup

Superusers can export and import system data from the admin header link.

- Page URL: `/admin/data-backup/`
- Export downloads a ZIP file named like `course-finder-system-backup-YYYYMMDD-HHMMSS.zip`.
- The ZIP contains:
  - `course_finder_system_data.json`: Django fixture data for all Django model-backed tables.
  - `backup_manifest.json`: every database table name and row count, including empty tables and technical tables such as `django_migrations`.
  - `media/...`: uploaded media files.
  - `database/db.sqlite3`: a raw SQLite database copy when the current database is SQLite and the DB file is available.
- Backed-up fixture data includes framework and project model rows, including:
  - `admin.LogEntry`
  - `auth.Group`
  - `auth.Permission`
  - `auth.User`
  - `contenttypes.ContentType`
  - `sessions.Session`
  - project app models, including `Category` and `Resource`
- `django_migrations` is not a Django model-backed table, so it is listed in the manifest and included in the raw SQLite copy, but it is not imported from the fixture. Run migrations before importing on a new server.
- Import accepts ZIP backups exported from this page.
- Import is a replace/restore operation:
  - It deletes existing Django model-backed rows.
  - It loads the fixture from the ZIP.
  - It restores media files afterward, so thumbnail cleanup signals do not delete restored files during import.
- The view requires a superuser. Staff users can access regular admin but receive permission denied for system backup.

Relevant files:

- `core.forms.SystemDataImportForm`
- `core.services.system_backup_service`
- `core.admin_views.system_data_backup_view`
- `core/templates/admin/system_data_backup.html`
- `course_finder.urls`

## File Cleanup

`resources.signals` handles thumbnail file cleanup:

- `pre_save` deletes the previous thumbnail file when `Resource.thumbnail_url` changes.
- `post_delete` deletes the current thumbnail file when a `Resource` is deleted.
- Cleanup skips deletion when another `Resource` still references the same file name.

`resources.apps.ResourcesConfig.ready()` imports `resources.signals`, so keep the signals import there.

## Telegram Flow

Webhook URL path:

```text
/telegram/webhook/
```

`telegram.views.telegram_webhook`

- Accepts only `POST`.
- Is `csrf_exempt` because Telegram webhook requests do not send Django CSRF tokens.
- Reads `message.text` and `message.chat.id`.
- Dispatches resource commands directly.
- Falls back to `telegram.services.message_handler.build_reply`.

Supported simple commands:

- `/start`
- `/categories`
- `/danhmuc`
- `/resources`
- `/latest`
- `/khoahoc`

Resource commands send up to 5 latest resources:

- If a resource has `thumbnail_url`, Telegram sends it via `sendPhoto` with a caption.
- If it has no thumbnail, Telegram sends a text message.
- Photo URLs are generated from the incoming webhook request with `request.build_absolute_uri(resource.thumbnail_url.url)`.

Important ngrok note:

- Every time ngrok URL changes, update Telegram webhook with the new URL.
- The webhook should point to:

```text
https://<current-ngrok-domain>/telegram/webhook/
```

## Common Commands

Use the project virtual environment:

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py test
.\venv\Scripts\python.exe manage.py runserver
```

Install dependencies:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Check Telegram webhook:

```powershell
$lines = @(Get-Content .env | Where-Object { $_ -match '^TELEGRAM_BOT_TOKEN=' })
$token = ($lines[0] -replace '^TELEGRAM_BOT_TOKEN=', '').Trim()
Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getWebhookInfo"
```

Set Telegram webhook:

```powershell
$lines = @(Get-Content .env | Where-Object { $_ -match '^TELEGRAM_BOT_TOKEN=' })
$token = ($lines[0] -replace '^TELEGRAM_BOT_TOKEN=', '').Trim()
$webhookUrl = 'https://<current-ngrok-domain>/telegram/webhook/'
$body = @{ url = $webhookUrl; allowed_updates = @('message') } | ConvertTo-Json
Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/setWebhook" -Method Post -ContentType 'application/json' -Body $body
```

## Environment Notes

Expected `.env` keys:

```env
SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,.ngrok-free.app
CSRF_TRUSTED_ORIGINS=https://*.ngrok-free.app
TIME_ZONE=Asia/Ho_Chi_Minh
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Do not commit real secrets if this project becomes public.

## Verification Status

Last verified after thumbnail upload and Telegram resource updates:

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test
```

Result:

- Migrations applied successfully.
- Django system check passed.
- Test command passed.
- Resource thumbnail cleanup tests cover replacing and deleting uploaded files.
- System backup tests cover exporting full model-backed ZIP backups and importing users, groups, permissions/contenttypes, resources, and media restore.

## Maintenance Rule

When changing code, update this file if any of these change:

- Models or migrations.
- Telegram commands or webhook behavior.
- Environment variables.
- Setup or verification commands.
- Admin behavior.
- Media/static file handling.
- Known project status or limitations.
