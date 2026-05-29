from __future__ import annotations

import random
import string

from django.contrib import admin
from django.utils.html import format_html

from .models import DeviceSession, License, ValidateLog


def _generate_unique_key() -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        parts = ["".join(random.choices(chars, k=4)) for _ in range(3)]
        key = "CF-" + "-".join(parts)
        if not License.objects.filter(key=key).exists():
            return key


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------

class DeviceSessionInline(admin.TabularInline):
    model = DeviceSession
    extra = 0
    readonly_fields = ("id", "device_token", "hwid", "ip_address", "created_at", "last_seen_at")
    fields = ("is_active", "hwid", "ip_address", "created_at", "last_seen_at")
    can_delete = False


class ValidateLogInline(admin.TabularInline):
    model = ValidateLog
    extra = 0
    readonly_fields = ("result", "hwid", "ip_address", "device_token", "created_at")
    fields = ("result", "ip_address", "created_at")
    can_delete = False
    max_num = 0
    ordering = ("-created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-created_at")


# ---------------------------------------------------------------------------
# License admin
# ---------------------------------------------------------------------------

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ("key", "note", "is_active", "status_badge", "expires_at", "active_hwid", "hwid_reset_count", "created_at")
    list_filter = ("is_active",)
    search_fields = ("key", "note")
    readonly_fields = ("created_at", "hwid_reset_count")
    ordering = ("-created_at",)
    inlines = [DeviceSessionInline, ValidateLogInline]

    fieldsets = (
        (None, {"fields": ("key", "note", "is_active", "expires_at")}),
        ("Info", {"fields": ("created_at", "hwid_reset_count"), "classes": ("collapse",)}),
    )

    def get_changeform_initial_data(self, request):
        return {"key": _generate_unique_key()}

    def status_badge(self, obj: License) -> str:
        if not obj.is_active:
            return format_html('<span style="color:#dc2626;font-weight:700">Revoked</span>')
        if obj.is_expired:
            return format_html('<span style="color:#f59e0b;font-weight:700">Expired</span>')
        return format_html('<span style="color:#16a34a;font-weight:700">Active</span>')
    status_badge.short_description = "Status"

    def active_hwid(self, obj: License) -> str:
        session = obj.active_session
        if not session:
            return "—"
        return session.hwid[:16] + "…"
    active_hwid.short_description = "Bound HWID"

    actions = ["revoke_selected", "reset_hwid_selected"]

    @admin.action(description="Revoke selected licenses")
    def revoke_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Revoked {updated} license(s).")

    @admin.action(description="Reset HWID (allow re-activation on new machine)")
    def reset_hwid_selected(self, request, queryset):
        from django.db.models import F
        for lic in queryset:
            lic.sessions.update(is_active=False)
            lic.hwid_reset_count = F("hwid_reset_count") + 1
            lic.save(update_fields=["hwid_reset_count"])
        self.message_user(request, f"Reset HWID for {queryset.count()} license(s).")


# ---------------------------------------------------------------------------
# DeviceSession admin
# ---------------------------------------------------------------------------

@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    list_display = ("license", "hwid_short", "ip_address", "is_active", "last_seen_at", "created_at")
    list_filter = ("is_active",)
    search_fields = ("license__key", "hwid", "ip_address")
    readonly_fields = ("id", "device_token", "license", "hwid", "ip_address", "created_at", "last_seen_at")
    ordering = ("-last_seen_at",)

    def hwid_short(self, obj: DeviceSession) -> str:
        return obj.hwid[:16] + "…"
    hwid_short.short_description = "HWID"

    actions = ["revoke_selected"]

    @admin.action(description="Revoke selected sessions")
    def revoke_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Revoked {updated} session(s).")


# ---------------------------------------------------------------------------
# ValidateLog admin (read-only)
# ---------------------------------------------------------------------------

@admin.register(ValidateLog)
class ValidateLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "result", "license", "ip_address", "hwid_short")
    list_filter = ("result",)
    search_fields = ("license__key", "ip_address", "hwid")
    readonly_fields = ("license", "device_token", "hwid", "ip_address", "result", "created_at")
    ordering = ("-created_at",)

    def hwid_short(self, obj: ValidateLog) -> str:
        return obj.hwid[:16] + "…" if obj.hwid else "—"
    hwid_short.short_description = "HWID"

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


