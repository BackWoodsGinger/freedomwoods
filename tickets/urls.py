from django.urls import path
from . import views

app_name = "tickets"  # this MUST be here

urlpatterns = [
    path('', views.ticket_list, name='ticket_list'),          # Shows all tickets
    path('<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('create/', views.ticket_create, name='ticket_create'),
    path('<int:pk>/claim/', views.ticket_claim, name='ticket_claim'),
    path('<int:pk>/escalate/', views.ticket_escalate, name='ticket_escalate'),
    path('<int:pk>/close/', views.ticket_close, name='ticket_close'),
]