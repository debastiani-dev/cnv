from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.cattle.services.cattle_service import CattleService
from apps.health.services import HealthService
from apps.purchases.services.purchase_service import PurchaseService
from apps.sales.services.sale_service import SaleService
from apps.weight.services.weight_service import WeightService


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fetch stats
        cattle_stats = CattleService.get_cattle_stats()
        sales_stats = SaleService.get_sales_stats()
        purchases_stats = PurchaseService.get_purchases_stats()

        # Calculate Net Profit
        net_profit = sales_stats["total_revenue"] - purchases_stats["total_cost"]

        # Health Stats
        active_withdrawal_count = HealthService.get_active_withdrawal_count()
        recent_health_events = HealthService.get_recent_events(limit=5)

        # Weight Stats
        weight_stats = WeightService.get_herd_adg_stats()

        # Add to context
        context.update(
            {
                "cattle_stats": cattle_stats,
                "sales_stats": sales_stats,
                "purchases_stats": purchases_stats,
                "net_profit": net_profit,
                "active_withdrawal_count": active_withdrawal_count,
                "recent_health_events": recent_health_events,
                "weight_stats": weight_stats,
            }
        )
        return context
