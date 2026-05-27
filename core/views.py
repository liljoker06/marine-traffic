from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render

from .models import Port


def index(request):
    return render(request, 'core/index.html')

def map_view(request):
    return render(request, "core/map.html")

# liste des ports avec pagination, recherche et filtrage par pays ou par nom
def ports_list(request):
    qs = Port.objects.all()

    search = request.GET.get("search", "").strip()
    country = request.GET.get("country", "").strip()

    if search:
        qs = qs.filter(name__icontains=search)
    if country:
        qs = qs.filter(country__iexact=country)

    countries = (
        Port.objects.values_list("country", flat=True)
        .distinct()
        .order_by("country")
    )
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "core/ports.html",
        {
            "page_obj": page_obj,
            "countries": countries,
            "search": search,
            "selected_country": country,
            "total": Port.objects.count(),
        },
    )


def ports_api(request):
    ports = list(
        Port.objects.values("id", "name", "country", "region", "latitude", "longitude")
    )
    return JsonResponse({"ports": ports})
