from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from resources.models import Category, Resource


def home(request):
    search_query = request.GET.get("q", "").strip()
    selected_category_id = None
    selected_category = request.GET.get("category", "").strip()
    if selected_category.isdigit():
        selected_category_id = int(selected_category)

    categories = list(Category.objects.order_by("name"))
    resources = Resource.objects.select_related("category").order_by("-created_at")

    if search_query:
        resources = resources.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    if selected_category_id:
        resources = resources.filter(category_id=selected_category_id)

    paginator = Paginator(resources, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "categories": categories,
        "page_obj": page_obj,
        "resources": page_obj.object_list,
        "search_query": search_query,
        "selected_category_id": selected_category_id,
        "resource_count": page_obj.paginator.count,
        "category_count": len(categories),
    }
    return render(request, "core/home.html", context)
