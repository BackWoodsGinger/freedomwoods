# Generated manually for ManualRecord and Excel file type

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataanalysis', '0002_datasetfile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetfile',
            name='file_type',
            field=models.CharField(choices=[('csv', 'CSV'), ('xlsx', 'Excel'), ('parquet', 'Parquet')], max_length=10),
        ),
        migrations.CreateModel(
            name='ManualRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('values', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manual_records', to='dataanalysis.datasets')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
