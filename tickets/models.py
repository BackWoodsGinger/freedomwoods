from django.db import models
from django.contrib.auth.models import User

# Ticket priority choices
PRIORITY_CHOICES = [
    ('Low', 'Low'),
    ('Medium', 'Medium'),
    ('High', 'High'),
]

# Ticket status choices
STATUS_CHOICES = [
    ('New', 'New'),          # Unclaimed
    ('Pending', 'Pending'),  # Claimed, in progress
    ('Resolved', 'Resolved') # Closed
]

# Ticket escalation levels
LEVEL_CHOICES = [
    ('1', 'Level 1'),
    ('2', 'Level 2'),
    ('3', 'Level 3'),
]

class Ticket(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets_created')
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='tickets_assigned')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='New')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    level = models.CharField(max_length=1, choices=LEVEL_CHOICES, default='1')
    escalation_level = models.IntegerField(default=1)  # Tracks if escalated to Level 2 or 3
    resolution = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.status})"