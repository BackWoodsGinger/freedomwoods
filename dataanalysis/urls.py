from django.urls import path
from . import views

app_name = "dataanalysis"

urlpatterns = [
    path("", views.dataset_list, name="dataset_list"),
    path("create/", views.dataset_create, name="dataset_create"),
    path("<int:pk>/", views.dataset_detail, name="dataset_detail"),
    path("<int:pk>/visualize/", views.dataset_visualize, name="dataset_visualize"),
    path("<int:pk>/delete/", views.dataset_delete, name="dataset_delete"),
    path("<int:pk>/analytics/", views.run_analytics, name="run_analytics"),
    path("<int:pk>/analytics/pdf/", views.export_analytics_pdf, name="export_analytics_pdf"),
    path("<int:pk>/analytics/txt/", views.export_analytics_txt, name="export_analytics_txt"),
]
