from django.shortcuts import render
from .context_processors import nav_apps


def index(request):
    """Homepage with project cards; uses same app list as nav dropdown."""
    return render(request, "pages/index.html", {"apps": nav_apps(request)["nav_apps"]})


def about(request):
    """Professional about / developer platform page."""
    return render(request, "pages/about.html")