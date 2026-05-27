from django.shortcuts import render

def index(request):
    return render(request, 'core/index.html')

def map_view(request):
    return render(request, 'core/map.html')