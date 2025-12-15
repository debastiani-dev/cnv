from datetime import timedelta
from typing import Dict, List, Union

from django.db.models import Avg
from django.db.models.functions import TruncWeek
from django.utils import timezone

from apps.cattle.models import Cattle
from apps.weight.models import WeightRecord


def get_global_adg_metrics(days: int = 90) -> Dict[str, Union[float, str, List[float]]]:
    """
    Calculates the average performance of the herd in the last X days.
    """
    cutoff_date = timezone.now() - timedelta(days=days)

    # Get the latest ADG recorded for each active animal in the period
    recent_entries = WeightRecord.objects.filter(
        session__date__gte=cutoff_date,
        animal__status=Cattle.STATUS_AVAILABLE,
        adg__isnull=False,
    )

    # Aggregate
    stats = recent_entries.aggregate(avg_gain=Avg("adg"))
    current_adg = float(stats["avg_gain"] or 0.0)

    # Get History for Sparkline (Weekly Averages)
    history = get_adg_history(recent_entries)

    return {
        "value": round(current_adg, 3),  # e.g., 0.850 kg
        "unit": "kg/day",
        "trend": get_adg_trend(current_adg, days),  # Compare with previous period
        "status": get_adg_status(current_adg),
        "history": history,
    }


def get_adg_status(value: float) -> str:
    if value < 0.3:
        return "CRITICAL"  # Losing money
    if value < 0.6:
        return "MAINTENANCE"
    return "PROFITABLE"


def get_adg_trend(current_value: float, days: int = 90) -> str:
    """
    Compares current ADG with the previous period (e.g. 90-180 days ago).
    Returns 'UP', 'DOWN', or 'STABLE'.
    """
    now = timezone.now()
    cutoff_date_current = now - timedelta(days=days)
    cutoff_date_prev = now - timedelta(days=days * 2)

    # Calculate Previous ADG
    prev_entries = WeightRecord.objects.filter(
        session__date__gte=cutoff_date_prev,
        session__date__lt=cutoff_date_current,
        animal__status=Cattle.STATUS_AVAILABLE,
        adg__isnull=False,
    )
    stats = prev_entries.aggregate(avg_gain=Avg("adg"))
    prev_adg = float(stats["avg_gain"] or 0.0)

    # Compare
    threshold = 0.05  # 50g difference to count as change
    if current_value > prev_adg + threshold:
        return "UP"
    if current_value < prev_adg - threshold:
        return "DOWN"
    return "STABLE"


def get_adg_history(queryset) -> List[float]:
    """
    Generates a list of weekly average ADG values for the sparkline.
    """
    # Annotate by week and avg ADG
    weekly_stats = (
        queryset.annotate(week=TruncWeek("session__date"))
        .values("week")
        .annotate(avg_adg=Avg("adg"))
        .order_by("week")
    )

    # Extract values, ensure float
    history = [float(entry["avg_adg"] or 0.0) for entry in weekly_stats]

    # If not enough data, return at least the current value to render a dot
    if not history:
        history = [0.0]

    return history
