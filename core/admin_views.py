from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from core.forms import SystemDataImportForm
from core.services.system_backup_service import build_system_backup_zip, import_system_backup


def system_data_backup_view(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        raise PermissionDenied

    if request.method == "GET" and request.GET.get("export"):
        file_name, backup_bytes = build_system_backup_zip()
        response = HttpResponse(backup_bytes, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response

    if request.method == "POST":
        form = SystemDataImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                result = import_system_backup(form.cleaned_data["backup_file"])
            except Exception as exc:
                messages.error(request, f"Import failed: {exc}")
            else:
                messages.success(
                    request,
                    (
                        "System import completed: "
                        f"{result.object_count} objects and {result.media_file_count} media files."
                    ),
                )
                return redirect(reverse("admin:index"))
    else:
        form = SystemDataImportForm()

    context = {
        **admin.site.each_context(request),
        "title": "System data backup",
        "form": form,
    }
    return TemplateResponse(request, "admin/system_data_backup.html", context)
