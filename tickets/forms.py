from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import Ticket

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "priority", "assigned_to"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "needs-validation"
        self.helper.label_class = "fw-bold"
        self.helper.field_class = "mb-3"
        self.helper.layout = Layout(
            Row(
                Column("title", css_class="col-md-6"),
                Column("priority", css_class="col-md-6"),
            ),
            "description",
            "assigned_to",
            Submit("submit", "Submit Ticket", css_class="btn btn-primary w-100 mt-3"),
        )