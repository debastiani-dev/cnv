from typing import Optional

from django.db.models import DecimalField, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce

from apps.partners.models import Partner


class PartnerService:
    @staticmethod
    def get_partners(search_query: Optional[str] = None) -> QuerySet[Partner]:
        """
        Returns a queryset of partners, optionally filtered by a search query.
        Annotated with total_sales and total_purchases.
        """
        queryset = Partner.objects.annotate(
            total_sales=Coalesce(
                Sum("sales__total_amount"), Value(0), output_field=DecimalField()
            ),
            total_purchases=Coalesce(
                Sum("purchases__total_amount"), Value(0), output_field=DecimalField()
            ),
        ).order_by("name")

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(tax_id__icontains=search_query)
                | Q(email__icontains=search_query)
            )

        return queryset

    @staticmethod
    def create_partner(data: dict) -> Partner:
        """
        Creates a new partner.
        Data should be a dictionary of validated fields.
        """
        return Partner.objects.create(**data)

    @staticmethod
    def update_partner(partner: Partner, data: dict) -> Partner:
        """
        Updates an existing partner.
        """
        for key, value in data.items():
            setattr(partner, key, value)
        partner.save()
        return partner

    @staticmethod
    def delete_partner(partner: Partner) -> None:
        """
        Soft deletes a partner.
        """
        partner.delete()

    @staticmethod
    def get_deleted_partners() -> QuerySet[Partner]:
        """
        Returns a queryset of soft-deleted partners.
        """
        return Partner.all_objects.filter(is_deleted=True).order_by("name")

    @staticmethod
    def restore_partner(partner: Partner) -> None:
        """
        Restores a soft-deleted partner.
        """
        partner.restore()

    @staticmethod
    def hard_delete_partner(partner: Partner) -> None:
        """
        Permanently deletes a partner.
        """
        partner.delete(destroy=True)
