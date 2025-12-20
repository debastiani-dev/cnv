from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils.translation import gettext_lazy as _

from apps.partners.services import PartnerService
from apps.transactions.models.transaction import Transaction
from apps.transactions.models.transaction_item import TransactionItem


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["date", "type", "partner", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["partner"].queryset = PartnerService.get_partners()


class TransactionItemForm(forms.ModelForm):
    # Specialized field for selecting Content Type
    # We restrict to models that make sense to trade
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(
            model__in=["cattle", "feedingredient", "medicine"]
        ),
        label=_("Item Type"),
        required=True,
    )

    # object_id acts as the selection (UUID)
    object_id = forms.UUIDField(widget=forms.HiddenInput(), required=True)

    # helper for UI to show initial name if bound
    item_name = forms.CharField(
        required=False, widget=forms.TextInput(attrs={"readonly": "readonly"})
    )

    class Meta:
        model = TransactionItem
        fields = ["content_type", "object_id", "quantity", "unit_price"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If bound or instance exists, set initial ContentType and ObjectId
        if self.instance.pk and self.instance.content_type_id:
            self.fields["content_type"].initial = self.instance.content_type
            self.fields["object_id"].initial = self.instance.object_id
            if self.instance.content_object:
                self.fields["item_name"].initial = str(self.instance.content_object)

    def clean(self):
        cleaned_data = super().clean()
        ct = cleaned_data.get("content_type")
        obj_id = cleaned_data.get("object_id")

        # Access parent form to know if it is Sale or Purchase?
        # Formsets don't easily give access to parent form data in clean() without passing it.
        # But we can validate general existence here.
        # Specific Sale/Purchase logic might need to happen in Service or if we pass context.
        # For now, we reuse validate_item_for_sale logic IF we knew it was a sale.
        # Let's verify existence mainly.

        if ct and obj_id:
            # Verify existence
            model = ct.model_class()
            try:
                obj = model.objects.get(pk=obj_id)
                self.instance.content_object = obj

                # If we knew it was a sale, we would call validate_item_for_sale(obj)
                # We will defer that to service save or view validation where we have the context
                # OR we try to guess from prefix? No.
                # Ideally we pass 'transaction_type' to form kwargs.

            except model.DoesNotExist:
                self.add_error("object_id", _("Selected item does not exist."))
            except ValidationError as e:
                self.add_error("object_id", e.message)
                raise forms.ValidationError(e.message)

        return cleaned_data


class BaseTransactionItemFormSet(BaseInlineFormSet):
    pass


TransactionItemFormSet = inlineformset_factory(
    Transaction,
    TransactionItem,
    form=TransactionItemForm,
    formset=BaseTransactionItemFormSet,
    extra=1,
    can_delete=True,
)
