import django_filters
from django.db.models import Q

from apps.cattle.models import Cattle
from apps.locations.models import Location


class CattleFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_search", label="Search")
    location = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.all(), label="Location"
    )
    status = django_filters.MultipleChoiceFilter(
        choices=Cattle.STATUS_CHOICES, label="Status"
    )
    reproduction_status = django_filters.MultipleChoiceFilter(
        choices=Cattle.REP_STATUS_CHOICES, label="Reproduction Status"
    )
    weight_min = django_filters.NumberFilter(
        field_name="current_weight", lookup_expr="gte", label="Min Weight (kg)"
    )
    weight_max = django_filters.NumberFilter(
        field_name="current_weight", lookup_expr="lte", label="Max Weight (kg)"
    )

    class Meta:
        model = Cattle
        fields = ["location", "status", "reproduction_status"]

    def filter_search(self, queryset, _name, value):

        return queryset.filter(
            Q(tag__icontains=value)
            | Q(name__icontains=value)
            | Q(sire__name__icontains=value)
            | Q(dam__name__icontains=value)
            | Q(electronic_id__icontains=value)
        )
