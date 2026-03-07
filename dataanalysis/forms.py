from django import forms
from .models import Datasets, DatasetFile, ManualRecord, Variables


class DatasetForm(forms.ModelForm):
    class Meta:
        model = Datasets
        fields = ("name", "description")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Bore Diameter Run 1"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Optional description"}),
        }


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = DatasetFile
        fields = ("file", "file_type")
        widgets = {
            "file": forms.FileInput(attrs={"class": "form-control", "accept": ".csv,.xlsx,.xls"}),
            "file_type": forms.Select(attrs={"class": "form-select"}),
        }


class ManualRecordForm(forms.Form):
    """Dynamic form built from dataset variables."""

    def __init__(self, dataset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for var in dataset.variables.all().order_by("id"):
            if var.data_type == "numeric":
                self.fields[f"var_{var.id}"] = forms.FloatField(
                    label=var.name, required=False, widget=forms.NumberInput(attrs={"class": "form-control", "step": "any"})
                )
            else:
                self.fields[f"var_{var.id}"] = forms.CharField(
                    label=var.name, required=False, max_length=500, widget=forms.TextInput(attrs={"class": "form-control"})
                )
            self.fields[f"var_{var.id}"].variable = var

    def get_values(self):
        """Return dict of variable name -> value for ManualRecord.values."""
        return {
            self.fields[k].variable.name: v
            for k, v in self.cleaned_data.items()
            if k.startswith("var_") and v is not None and v != ""
        }


class AnalyticsForm(forms.Form):
    ANALYSIS_CHOICES = [
        ("descriptive", "Descriptive Statistics"),
        ("xbar_r", "X-bar & R Chart"),
        ("xbar_s", "X-bar & S Chart"),
        ("i_mr", "I-MR Chart (Individuals)"),
        ("capability", "Process Capability (Cp/Cpk)"),
        ("one_sample_t", "One-Sample t-test"),
        ("two_sample_t", "Two-Sample t-test"),
        ("paired_t", "Paired t-test"),
        ("anova", "One-Way ANOVA"),
        ("regression", "Simple Linear Regression"),
    ]
    analysis = forms.ChoiceField(choices=ANALYSIS_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))
    variable = forms.CharField(required=False, widget=forms.HiddenInput())
    variable2 = forms.CharField(required=False, widget=forms.HiddenInput())
    subgroup_size = forms.IntegerField(required=False, min_value=2, max_value=25, initial=5, widget=forms.NumberInput(attrs={"class": "form-control"}))
    usl = forms.FloatField(required=False, widget=forms.NumberInput(attrs={"class": "form-control", "step": "any", "placeholder": "Upper spec"}))
    lsl = forms.FloatField(required=False, widget=forms.NumberInput(attrs={"class": "form-control", "step": "any", "placeholder": "Lower spec"}))
    mu0 = forms.FloatField(required=False, widget=forms.NumberInput(attrs={"class": "form-control", "step": "any", "placeholder": "Target mean (μ₀)"}))
