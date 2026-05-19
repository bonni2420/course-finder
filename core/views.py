from xml.sax.saxutils import escape as xml_escape

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from core.seo import (
    DEFAULT_DESCRIPTION,
    absolute_url,
    base_seo_context,
    clean_text,
    image_url,
    safe_json_ld,
)
from resources.models import Category, Resource


def home(request, category_pk: int | None = None, category_slug: str | None = None):
    search_query = request.GET.get("q", "").strip()
    selected_category_id = None
    if category_pk is not None:
        selected_category_id = category_pk
    else:
        selected_category = request.GET.get("category", "").strip()
        if selected_category.isdigit():
            selected_category_id = int(selected_category)

    categories = list(Category.objects.order_by("name"))
    selected_category_obj = next(
        (category for category in categories if category.id == selected_category_id),
        None,
    )
    if category_pk is not None:
        if selected_category_obj is None:
            raise Http404("Category not found")
        expected_slug = slugify(selected_category_obj.name) or "danh-muc"
        if category_slug != expected_slug:
            return redirect(selected_category_obj.get_absolute_url(), permanent=True)

    resources = Resource.objects.select_related("category").order_by("-created_at")

    if search_query:
        resources = resources.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    if selected_category_id and selected_category_obj:
        resources = resources.filter(category_id=selected_category_id)
    elif selected_category_id:
        selected_category_id = None

    paginator = Paginator(resources, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    resources_on_page = list(page_obj.object_list)

    if search_query:
        seo_title = f'Tìm "{search_query}" trong kho khóa học | Course Finder'
        seo_description = f'Kết quả tìm kiếm khóa học miễn phí cho "{search_query}" trên Course Finder.'
        seo_robots = "noindex,follow"
        canonical_path = reverse("core:home")
    elif selected_category_obj:
        seo_title = f"Khóa học {selected_category_obj.name} miễn phí | Course Finder"
        seo_description = (
            selected_category_obj.description
            or f"Tổng hợp khóa học {selected_category_obj.name} miễn phí, được phân loại để bạn tìm nhanh và học ngay."
        )
        seo_robots = None
        canonical_path = selected_category_obj.get_absolute_url()
    else:
        seo_title = "Course Finder - Khóa học miễn phí chọn lọc"
        seo_description = DEFAULT_DESCRIPTION
        seo_robots = None
        canonical_path = reverse("core:home")

    first_image = next((resource.thumbnail_url for resource in resources_on_page if resource.thumbnail_url), None)
    item_list = [
        {
            "@type": "ListItem",
            "position": page_obj.start_index() + index,
            "url": absolute_url(request, resource.get_absolute_url()),
            "name": resource.title,
        }
        for index, resource in enumerate(resources_on_page)
    ]
    structured_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": f"{absolute_url(request, reverse('core:home'))}#website",
                "name": "Course Finder",
                "url": absolute_url(request, reverse("core:home")),
                "inLanguage": "vi-VN",
                "description": DEFAULT_DESCRIPTION,
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": f"{absolute_url(request, reverse('core:home'))}?q={{search_term_string}}",
                    "query-input": "required name=search_term_string",
                },
            },
            {
                "@type": "ItemList",
                "@id": f"{absolute_url(request, canonical_path)}#courses",
                "name": seo_title.replace(" | Course Finder", ""),
                "numberOfItems": page_obj.paginator.count,
                "itemListElement": item_list,
            },
        ],
    }

    context = {
        "categories": categories,
        "page_obj": page_obj,
        "resources": resources_on_page,
        "search_query": search_query,
        "selected_category_id": selected_category_id,
        "selected_category": selected_category_obj,
        "resource_count": page_obj.paginator.count,
        "category_count": len(categories),
        "structured_data": safe_json_ld(structured_data),
    }
    context.update(
        base_seo_context(
            request,
            title=seo_title,
            description=seo_description,
            canonical_path=canonical_path,
            robots=seo_robots or None,
            og_image=image_url(request, first_image),
        )
    )
    return render(request, "core/home.html", context)


def resource_detail(request, pk: int, slug: str):
    resource = get_object_or_404(Resource.objects.select_related("category"), pk=pk)
    expected_slug = slugify(resource.title) or "khoa-hoc"
    if slug != expected_slug:
        return redirect(resource.get_absolute_url(), permanent=True)

    related_resources = list(
        Resource.objects.select_related("category")
        .filter(category=resource.category)
        .exclude(pk=resource.pk)
        .order_by("-created_at")[:4]
    )
    description = clean_text(
        resource.description
        or f"Khóa học {resource.title} thuộc danh mục {resource.category.name}, được tuyển chọn trên Course Finder."
    )
    canonical_path = resource.get_absolute_url()
    canonical_url = absolute_url(request, canonical_path)
    thumbnail_url = image_url(request, resource.thumbnail_url)
    structured_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{canonical_url}#webpage",
                "url": canonical_url,
                "name": resource.title,
                "description": description,
                "inLanguage": "vi-VN",
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Course Finder",
                        "item": absolute_url(request, reverse("core:home")),
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": resource.category.name,
                        "item": absolute_url(request, resource.category.get_absolute_url()),
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": resource.title,
                        "item": canonical_url,
                    },
                ],
            },
            {
                "@type": "Course",
                "@id": f"{canonical_url}#course",
                "name": resource.title,
                "description": description,
                "url": canonical_url,
                "sameAs": resource.course_link,
                "inLanguage": "vi-VN",
                "provider": {
                    "@type": "Organization",
                    "name": "Course Finder",
                    "url": absolute_url(request, reverse("core:home")),
                },
                "offers": {
                    "@type": "Offer",
                    "price": "0",
                    "priceCurrency": "VND",
                    "availability": "https://schema.org/InStock",
                    "url": resource.course_link,
                },
            },
        ],
    }
    if thumbnail_url:
        structured_data["@graph"][0]["image"] = thumbnail_url
        structured_data["@graph"][2]["image"] = thumbnail_url

    context = {
        "resource": resource,
        "related_resources": related_resources,
        "structured_data": safe_json_ld(structured_data),
    }
    context.update(
        base_seo_context(
            request,
            title=f"{resource.title} | Khóa học miễn phí",
            description=description,
            canonical_path=canonical_path,
            og_type="article",
            og_image=thumbnail_url,
        )
    )
    return render(request, "core/resource_detail.html", context)


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /telegram/",
        "Allow: /",
        "",
        f"Sitemap: {absolute_url(request, reverse('core:sitemap_xml'))}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    latest_update = Resource.objects.order_by("-updated_at").values_list("updated_at", flat=True).first()
    home_lastmod = latest_update or timezone.now()
    entries = [
        {
            "loc": absolute_url(request, reverse("core:home")),
            "lastmod": home_lastmod,
            "changefreq": "daily",
            "priority": "1.0",
        }
    ]

    for category in Category.objects.order_by("name"):
        entries.append(
            {
                "loc": absolute_url(request, category.get_absolute_url()),
                "lastmod": home_lastmod,
                "changefreq": "weekly",
                "priority": "0.7",
            }
        )

    for resource in Resource.objects.only("id", "title", "updated_at").order_by("-updated_at"):
        entries.append(
            {
                "loc": absolute_url(request, resource.get_absolute_url()),
                "lastmod": resource.updated_at,
                "changefreq": "monthly",
                "priority": "0.8",
            }
        )

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for entry in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{xml_escape(entry['loc'])}</loc>")
        lines.append(f"    <lastmod>{entry['lastmod'].date().isoformat()}</lastmod>")
        lines.append(f"    <changefreq>{entry['changefreq']}</changefreq>")
        lines.append(f"    <priority>{entry['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return HttpResponse("\n".join(lines), content_type="application/xml; charset=utf-8")
