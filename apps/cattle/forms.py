from django import forms
from django.utils.translation import gettext as _

from apps.cattle.models import Cattle


class CattleForm(forms.ModelForm):
    class Meta:
        model = Cattle
        fields = ["tag", "name", "birth_date", "weight_kg", "breed", "status", "image"]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_tag(self):
        tag = self.cleaned_data["tag"]
        # Check if an active (non-deleted) cattle exists with this tag
        # We need to exclude the current instance if we are updating
        qs = Cattle.objects.filter(tag=tag)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                _("Cattle with tag '%(tag)s' already exists.") % {"tag": tag}
            )

        return tag
