from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.cattle.services.cattle_service import CattleService
from apps.purchases.services.purchase_service import PurchaseService
from apps.sales.services.sale_service import SaleService


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

        # Add to context
        context.update(
            {
                "cattle_stats": cattle_stats,
                "sales_stats": sales_stats,
                "purchases_stats": purchases_stats,
                "net_profit": net_profit,
            }
        )
        return context
