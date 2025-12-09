from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils.translation import gettext_lazy as _

from apps.partners.services import PartnerService
from apps.sales.models import Sale, SaleItem
from apps.sales.services.sale_service import SaleService


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ["date", "partner", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate partners from service to respect soft-delete rules if needed,
        # though ModelChoiceField naturally respects the default manager
        # (usually non-deleted). Ensuring we order them nicely.
        self.fields["partner"].queryset = PartnerService.get_partners()


class SaleItemForm(forms.ModelForm):
    # Specialized field for selecting Cattle
    # In a full Generic implementation, this would be more complex.
    # We assume 'cattle' for now.
    # Polymorphic fields
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(model__in=["cattle"]),  # Whitelist
        label=_("Item Type"),
        required=True,
    )
    # object_id is technically a UUIDField in model, but here it acts as the selection
    # We will use a ChoiceField/CharField that gets populated dynamically,
    # but initially empty or with the bound value.
    object_id = forms.UUIDField(
        widget=forms.HiddenInput(), required=True  # Or Select, will be handled by JS
    )

    # helper for UI to show initial name if bound
    item_name = forms.CharField(
        required=False, widget=forms.TextInput(attrs={"readonly": "readonly"})
    )

    # We remove the direct 'cattle' field.

    class Meta:
        model = SaleItem
        fields = ["content_type", "object_id", "quantity", "unit_price"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If bound or instance exists, set initial ContentType and ObjectId
        # Use content_type_id check to avoid RelatedObjectDoesNotExist
        # on unsaved/partial instances
        if self.instance.pk and self.instance.content_type_id:
            self.fields["content_type"].initial = self.instance.content_type
            self.fields["object_id"].initial = self.instance.object_id
            if self.instance.content_object:
                self.fields["item_name"].initial = str(self.instance.content_object)

    def clean(self):
        cleaned_data = super().clean()
        ct = cleaned_data.get("content_type")
        obj_id = cleaned_data.get("object_id")

        if ct and obj_id:
            # Verify existence
            model = ct.model_class()
            try:
                obj = model.objects.get(pk=obj_id)
                self.instance.content_object = obj

                # Verify Safety Valve
                SaleService.validate_item_for_sale(obj)

            except model.DoesNotExist:
                self.add_error("object_id", _("Selected item does not exist."))
            except ValidationError as e:
                # Catch service validation errors (like withdrawal block)
                # and display them on the form
                self.add_error("object_id", e.message)
                # Also raise regular ValidationError to stop processing if needed by Django
                raise forms.ValidationError(e.message)

        return cleaned_data

    # Save is standard because we set content_object in clean or via fields mapping
    # Actually, form save handles normal fields. GenericForeignKey is virtual.
    # Save is standard because we set content_object in clean or via fields mapping
    # Actually, form save handles normal fields. GenericForeignKey is virtual.
    # We need to explicitly set content_type and object_id on the instance
    # if they are fields in Meta.
    # Luckily they ARE in Meta, so form.save() should handle them if cleaned_data has them.
    # But clean() explicitly setting content_object ensures consistency.


class BaseSaleItemFormSet(BaseInlineFormSet):
    def clean(self):
        pass
        # super().clean()
        # Custom validation for the whole set if needed


SaleItemFormSet = inlineformset_factory(
    Sale,
    SaleItem,
    form=SaleItemForm,
    formset=BaseSaleItemFormSet,
    extra=1,
    can_delete=True,
)
