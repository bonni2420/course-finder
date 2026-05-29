from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class License(models.Model):
    key = models.CharField(max_length=20, primary_key=True, verbose_name="License Key")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    expires_at = models.DateTimeField(verbose_name="Expires At")
    note = models.CharField(max_length=200, blank=True, verbose_name="Note (tên/SĐT khách)")
    created_at = models.DateTimeField(auto_now_add=True)
    hwid_reset_count = models.IntegerField(default=0, verbose_name="HWID Reset Count")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "License"
        verbose_name_plural = "Licenses"

    def __str__(self) -> str:
        status = "✓" if self.is_active and not self.is_expired else "✗"
        return f"{status} {self.key}  {self.note}"

    @property
    def is_expired(self) -> bool:
        return self.expires_at < timezone.now()

    @property
    def active_session(self) -> DeviceSession | None:
        return self.sessions.filter(is_active=True).first()


class DeviceSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(
        License, on_delete=models.CASCADE, related_name="sessions"
    )
    device_token = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name="Device Token")
    hwid = models.CharField(max_length=64, verbose_name="HWID")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Address")
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(default=timezone.now, verbose_name="Last Seen")
    is_active = models.BooleanField(default=True, verbose_name="Active")

    class Meta:
        ordering = ["-last_seen_at"]
        verbose_name = "Device Session"
        verbose_name_plural = "Device Sessions"

    def __str__(self) -> str:
        return f"{self.license.key} — {self.hwid[:12]}… ({self.ip_address})"


class ValidateLog(models.Model):
    RESULT_CHOICES = [
        ("ok", "OK"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
        ("device_mismatch", "Device Mismatch"),
        ("not_found", "Not Found"),
        ("invalid_request", "Invalid Request"),
        ("rate_limited", "Rate Limited"),
    ]

    license = models.ForeignKey(
        License,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    device_token = models.CharField(max_length=36, blank=True)
    hwid = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Validate Log"
        verbose_name_plural = "Validate Logs"

    def __str__(self) -> str:
        return f"{self.result} — {self.ip_address} — {self.created_at:%Y-%m-%d %H:%M}"


