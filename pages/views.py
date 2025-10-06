from django.shortcuts import render

def index(request):
    # List of apps/projects to show on homepage
    apps = [
        {
            "name": "Help Desk Ticketing System",
            "description": "Submit and track IT issues with our ticket workflow.",
            "url_name": "tickets:ticket_list",  # include namespace
            "status": "available"
        },
        {
            "name": "TimeClock System",
            "description": "Track employee hours and attendance.",
            "url_name": None,  # Coming soon
            "status": "coming"
        },
    ]
    return render(request, "pages/index.html", {"apps": apps})