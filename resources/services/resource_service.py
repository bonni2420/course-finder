from html import escape
from typing import Dict, List

from django.http import HttpRequest

from resources.models import Resource


def render_resource_caption(resource: Resource) -> str:
    lines = [
        f"<b>{escape(resource.title)}</b>",
        f"Danh mục: {escape(resource.category.name)}",
    ]

    if resource.description:
        lines.append(escape(resource.description[:450]))

    lines.append(f"Link khóa học: {escape(resource.course_link)}")
    return "\n".join(lines)


def render_latest_resource_messages(
    request: HttpRequest,
    limit: int = 5,
) -> List[Dict[str, str]]:
    resources = Resource.objects.select_related("category").order_by("-created_at")[:limit]

    messages = []
    for resource in resources:
        photo_url = ""
        if resource.thumbnail_url:
            photo_url = request.build_absolute_uri(resource.thumbnail_url.url)

        messages.append(
            {
                "caption": render_resource_caption(resource),
                "photo_url": photo_url,
            }
        )

    return messages
