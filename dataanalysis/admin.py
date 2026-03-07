from django.contrib import admin
from .models import Datasets, Variables, DatasetFile, ManualRecord
from django.db.models.signals import post_save
from django.dispatch import receiver
from .services.data_import import process_uploaded_file

admin.site.register(Datasets)
admin.site.register(Variables)
admin.site.register(DatasetFile)
admin.site.register(ManualRecord)

@receiver(post_save, sender=DatasetFile)
def process_file_after_upload(sender, instance, created, **kwargs):
    if created and instance.file_type in ("csv", "xlsx"):
        process_uploaded_file(instance)