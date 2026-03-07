from django.db import models
from django.contrib.auth.models import User

class Datasets(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Variables(models.Model):
    DATA_TYPES = [
        ("numeric", "Numeric"),
        ("categorical", "Categorical"),
        ("ordinal", "Ordinal"),
        ("date", "Date"),
        ("text", "Text"),
    ]

    dataset = models.ForeignKey(Datasets, on_delete=models.CASCADE, related_name="variables")
    name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)

    def __str__(self):
        return f"{self.dataset.name} - {self.name}"
    
class DatasetFile(models.Model):
    FILE_TYPES = [
        ("csv", "CSV"),
        ("xlsx", "Excel"),
        ("parquet", "Parquet"),
    ]

    dataset = models.ForeignKey(Datasets, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="datasets/")
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    row_count = models.IntegerField(null=True, blank=True)
    column_count = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.dataset.name} file"


class ManualRecord(models.Model):
    """Single row of manually entered data for a dataset (variable name -> value)."""
    dataset = models.ForeignKey(Datasets, on_delete=models.CASCADE, related_name="manual_records")
    values = models.JSONField(default=dict)  # e.g. {"Diameter": 10.2, "Batch": "A"}
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Record {self.id} in {self.dataset.name}"