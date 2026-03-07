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
            "name": "Data Analytics",
            "description": "Upload Excel/CSV or enter data manually; run analytics and export reports (SPC, capability, t-tests, regression, and more).",
            "url_name": "dataanalysis:dataset_list",
            "status": "available"
        },
    ]
    return render(request, "pages/index.html", {"apps": apps})