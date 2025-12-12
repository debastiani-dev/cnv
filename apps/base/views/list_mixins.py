from django.db.models import QuerySet
from django.http import HttpRequest


class StandardizedListMixin:
    """
    Mixin to standardize search and filtering logic for ListViews.
    """

    request: HttpRequest

    def filter_by_date(self, queryset: QuerySet, field_name: str = "date") -> QuerySet:
        """
        Filters the queryset by a date range using 'date_after' and 'date_before' GET params.
        """
        date_after = self.request.GET.get("date_after")
        date_before = self.request.GET.get("date_before")

        if date_after:
            filter_kwargs = {f"{field_name}__gte": date_after}
            queryset = queryset.filter(**filter_kwargs)
        if date_before:
            filter_kwargs = {f"{field_name}__lte": date_before}
            queryset = queryset.filter(**filter_kwargs)

        return queryset

    def get_context_data(self, **kwargs):
        """
        Injects standard filter parameters into the context.
        """
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["date_after"] = self.request.GET.get("date_after", "")
        context["date_before"] = self.request.GET.get("date_before", "")
        return context
