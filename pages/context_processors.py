"""
Context processors for global template data (e.g. nav apps list).
"""
from django.conf import settings


def nav_apps(request):
    """Provide the list of app/project links for the navbar dropdown."""
    apps = [
        {
            "name": "Help Desk Ticketing System",
            "description": "Submit and track IT issues with our ticket workflow.",
            "url_name": "tickets:ticket_list",
            "status": "available",
        },
        {
            "name": "Data Analytics",
            "description": "Upload Excel/CSV or enter data manually; run analytics and export reports.",
            "url_name": "dataanalysis:dataset_list",
            "status": "available",
        },
    ]
    return {"nav_apps": apps}


def static_version(request):
    """Expose STATIC_VERSION for cache-busting static URLs."""
    return {"STATIC_VERSION": getattr(settings, "STATIC_VERSION", "1")}
