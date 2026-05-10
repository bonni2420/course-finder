from typing import List

from resources.models import Category


def list_category_names() -> List[str]:
    return list(Category.objects.values_list("name", flat=True))


def render_categories_message() -> str:
    categories = list_category_names()
    if not categories:
        return "Hiện chưa có danh mục nào. Vui lòng thử lại sau."

    lines = ["Danh mục khóa học hiện có:"]
    for idx, name in enumerate(categories, start=1):
        lines.append(f"{idx}. {name}")
    return "\n".join(lines)
