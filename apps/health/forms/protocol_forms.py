from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from apps.authentication.models.user import User
from apps.health.forms.constants import (
    CHECKBOX_ATTRS,
    DATE_INPUT_ATTRS,
    SELECT_ATTRS,
    TEXT_INPUT_ATTRS,
    TEXTAREA_ATTRS,
)
from apps.health.models import HealthProtocol, ProtocolItem


class HealthProtocolForm(forms.ModelForm):
    class Meta:
        model = HealthProtocol
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs=TEXT_INPUT_ATTRS),
            "description": forms.Textarea(attrs=TEXTAREA_ATTRS),
            "is_active": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
        }


class ProtocolItemForm(forms.ModelForm):
    class Meta:
        model = ProtocolItem
        fields = ["medication", "default_dosage", "notes"]
        widgets = {
            "medication": forms.Select(attrs=SELECT_ATTRS),
            "default_dosage": forms.TextInput(attrs=TEXT_INPUT_ATTRS),
            "notes": forms.TextInput(attrs=TEXT_INPUT_ATTRS),
        }


ProtocolItemFormSet = inlineformset_factory(
    HealthProtocol,
    ProtocolItem,
    form=ProtocolItemForm,
    extra=1,
    can_delete=True,
)


class ProtocolApplicationForm(forms.Form):
    protocol = forms.ModelChoiceField(
        queryset=HealthProtocol.objects.filter(is_active=True, is_deleted=False),
        label=_("Select Protocol"),
        widget=forms.Select(attrs=SELECT_ATTRS),
    )
    date = forms.DateField(
        label=_("Date of Application"),
        widget=forms.DateInput(attrs=DATE_INPUT_ATTRS),
    )
    performed_by = forms.ModelChoiceField(
        queryset=None,  # Populated in __init__
        label=_("Performed By"),
        required=False,
        widget=forms.Select(attrs=SELECT_ATTRS),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["performed_by"].queryset = User.objects.all()
            self.fields["performed_by"].initial = user
