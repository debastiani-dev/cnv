from django import forms
from django.contrib.contenttypes.models import ContentType

from apps.tasks.models import Task


class TaskForm(forms.ModelForm):
    # Field to select the ContentType (e.g. 'cattle')
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(
            model__in=["cattle", "location", "partner"]
        ),
        required=False,
        label="Link to Object Type",
    )
    # Hidden field to store the object's ID (UUID)
    object_id = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "due_date",
            "priority",
            "status",
            "assigned_to",
            "content_type",
            "object_id",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_object_id(self):
        # Convert empty string to None for NULLable UUIDField
        data = self.cleaned_data["object_id"]
        if not data:
            return None
        return data
