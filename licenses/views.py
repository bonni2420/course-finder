from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import os
from typing import Any

from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import DeviceSession, License, ValidateLog

_HMAC_SECRET: str = os.environ.get("LICENSE_HMAC_SECRET", "cf-hmac-default-dev")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _sign(status: str, expires_at: str, device_token: str) -> str:
    payload = f"{status}|{expires_at}|{device_token}"
    return _hmac.new(_HMAC_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _ok_response(device_token: str, expires_at) -> JsonResponse:
    exp_str = expires_at.strftime("%Y-%m-%dT%H:%M:%S")
    return JsonResponse({
        "status": "ok",
        "expires_at": exp_str,
        "device_token": str(device_token),
        "sig": _sign("ok", exp_str, str(device_token)),
    })


def _parse_body(request) -> dict[str, Any] | None:
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _rate_check(ip: str, action: str, limit: int = 10, window: int = 60) -> bool:
    """Return True if allowed, False if rate-limited."""
    key = f"rl:{action}:{ip}"
    count = cache.get(key, 0)
    if count >= limit:
        return False
    cache.set(key, count + 1, window)
    return True


def _log(result: str, ip, license=None, device_token: str = "", hwid: str = "") -> None:
    ValidateLog.objects.create(
        license=license,
        device_token=device_token,
        hwid=hwid,
        ip_address=ip,
        result=result,
    )


# ---------------------------------------------------------------------------
# POST /licenses/activate/
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def activate(request):
    ip = _get_ip(request)

    if not _rate_check(ip or "unknown", "activate", limit=5, window=60):
        _log("rate_limited", ip)
        return JsonResponse({"status": "rate_limited"}, status=429)

    body = _parse_body(request)
    if not body:
        return JsonResponse({"status": "invalid_request"}, status=400)

    key = str(body.get("key") or "").strip().upper()
    hwid = str(body.get("hwid") or "").strip()
    if not key or not hwid:
        return JsonResponse({"status": "invalid_request"}, status=400)

    try:
        lic = License.objects.get(key=key)
    except License.DoesNotExist:
        _log("not_found", ip, hwid=hwid)
        return JsonResponse({"status": "not_found"}, status=404)

    if not lic.is_active:
        _log("revoked", ip, license=lic, hwid=hwid)
        return JsonResponse({"status": "revoked"}, status=403)

    if lic.is_expired:
        _log("expired", ip, license=lic, hwid=hwid)
        return JsonResponse({"status": "expired"}, status=403)

    existing = lic.sessions.filter(is_active=True).first()
    if existing:
        if existing.hwid == hwid:
            existing.last_seen_at = timezone.now()
            existing.ip_address = ip
            existing.save(update_fields=["last_seen_at", "ip_address"])
            _log("ok", ip, license=lic, device_token=str(existing.device_token), hwid=hwid)
            return _ok_response(existing.device_token, lic.expires_at)
        _log("device_mismatch", ip, license=lic, hwid=hwid)
        return JsonResponse({"status": "device_mismatch"}, status=403)

    session = DeviceSession.objects.create(license=lic, hwid=hwid, ip_address=ip)
    _log("ok", ip, license=lic, device_token=str(session.device_token), hwid=hwid)
    return _ok_response(session.device_token, lic.expires_at)


# ---------------------------------------------------------------------------
# POST /licenses/validate/
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def validate(request):
    ip = _get_ip(request)

    if not _rate_check(ip or "unknown", "validate", limit=30, window=60):
        _log("rate_limited", ip)
        return JsonResponse({"status": "rate_limited"}, status=429)

    body = _parse_body(request)
    if not body:
        return JsonResponse({"status": "invalid_request"}, status=400)

    device_token = str(body.get("device_token") or "").strip()
    hwid = str(body.get("hwid") or "").strip()
    if not device_token or not hwid:
        return JsonResponse({"status": "invalid_request"}, status=400)

    try:
        session = DeviceSession.objects.select_related("license").get(
            device_token=device_token
        )
    except (DeviceSession.DoesNotExist, ValueError):
        _log("not_found", ip, device_token=device_token, hwid=hwid)
        return JsonResponse({"status": "not_found"}, status=404)

    if session.hwid != hwid:
        _log("device_mismatch", ip, license=session.license, device_token=device_token, hwid=hwid)
        return JsonResponse({"status": "device_mismatch"}, status=403)

    if not session.is_active:
        _log("revoked", ip, license=session.license, device_token=device_token, hwid=hwid)
        return JsonResponse({"status": "revoked"}, status=403)

    lic = session.license
    if not lic.is_active:
        _log("revoked", ip, license=lic, device_token=device_token, hwid=hwid)
        return JsonResponse({"status": "revoked"}, status=403)

    if lic.is_expired:
        _log("expired", ip, license=lic, device_token=device_token, hwid=hwid)
        return JsonResponse({"status": "expired"}, status=403)

    session.last_seen_at = timezone.now()
    session.ip_address = ip
    session.save(update_fields=["last_seen_at", "ip_address"])
    _log("ok", ip, license=lic, device_token=device_token, hwid=hwid)
    return _ok_response(device_token, lic.expires_at)


