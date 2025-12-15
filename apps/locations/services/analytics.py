from decimal import Decimal

from django.db.models import Sum

from apps.cattle.models import Cattle
from apps.locations.models import Location


def get_stocking_rate_metrics():
    """
    Calculates the global stocking rate (AU/ha).
    """
    # 1. Total Weight of Active Herd in Pastures (Exclude Feedlot/Hospital if needed)
    total_weight = Cattle.objects.filter(
        status=Cattle.STATUS_AVAILABLE,
        location__type="PASTURE",  # Ensure we only count animals consuming grass
    ).aggregate(total=Sum("current_weight"))["total"] or Decimal("0.00")

    # 2. Total Area of Active Pastures
    total_area = Location.objects.filter(type="PASTURE", is_active=True).aggregate(
        total=Sum("area_hectares")
    )["total"] or Decimal(
        "1.00"
    )  # Avoid Div/0

    # 3. Calculations
    total_au = total_weight / Decimal("450.00")  # 1 AU = 450kg
    stocking_rate = total_au / total_area

    return {
        "rate": float(round(stocking_rate, 2)),
        "total_au": int(total_au),
        "total_area": int(total_area),
        "status": get_rate_status(stocking_rate),
    }


def get_rate_status(rate):
    if rate < 0.5:
        return "UNDERSTOCKED"
    if rate > 1.5:
        return "OVERSTOCKED"
    return "OPTIMAL"
