import json

from django.conf import settings
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator


SITE_NAME = getattr(settings, "SITE_NAME", "Course Finder")
DEFAULT_DESCRIPTION = getattr(
    settings,
    "SITE_DESCRIPTION",
    "Course Finder tuyển chọn khóa học miễn phí, tài liệu học tập và lộ trình kỹ năng để bạn tìm nhanh, học ngay.",
)
DEFAULT_ROBOTS = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"


def clean_text(value: str, limit: int = 160) -> str:
    text = " ".join(strip_tags(value or "").split())
    return Truncator(text).chars(limit)


def safe_json_ld(data: dict) -> str:
    return (
        json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def absolute_url(request, path: str = "/") -> str:
    configured_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if path.startswith(("http://", "https://")):
        return path
    if configured_url:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{configured_url}{path}"
    return request.build_absolute_uri(path)


def image_url(request, image_field) -> str:
    if not image_field:
        return ""
    try:
        return absolute_url(request, image_field.url)
    except ValueError:
        return ""


def base_seo_context(request, *, title: str, description: str, canonical_path: str, **overrides) -> dict:
    canonical_url = absolute_url(request, canonical_path)
    robots = overrides.pop("robots", DEFAULT_ROBOTS) or DEFAULT_ROBOTS
    context = {
        "site_name": SITE_NAME,
        "seo_title": title,
        "seo_description": clean_text(description or DEFAULT_DESCRIPTION),
        "seo_robots": robots,
        "canonical_url": canonical_url,
        "og_type": overrides.pop("og_type", "website"),
        "og_image": overrides.pop("og_image", ""),
        "sitemap_url": absolute_url(request, reverse("core:sitemap_xml")),
        "home_url": absolute_url(request, reverse("core:home")),
    }
    context.update(overrides)
    return context
