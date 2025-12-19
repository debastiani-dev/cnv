from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.views.generic import TemplateView

from apps.cattle.services.cattle_service import CattleService
from apps.finance.services.costing import CostingService
from apps.health.services import HealthService
from apps.locations.services import LocationService
from apps.nutrition.models.ingredient import FeedIngredient
from apps.purchases.services.purchase_service import PurchaseService
from apps.sales.services.sale_service import SaleService
from apps.tasks.services.tasks import TaskService
from apps.weight.services.weight_service import WeightService


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._get_dashboard_stats())
        return context

    def _get_dashboard_stats(self):
        """Helper to fetch all dashboard statistics."""
        # Fetch stats
        sales_stats = SaleService.get_sales_stats(days=90)
        purchases_stats = PurchaseService.get_purchases_stats(days=90)
        cost_stats = CostingService.get_cost_stats(days=90)

        # Calculate Net Profit
        total_expenses = purchases_stats["total_cost"] + cost_stats["total_cost"]
        net_profit = sales_stats["total_revenue"] - total_expenses

        return {
            "cattle_stats": CattleService.get_cattle_stats(),
            "sales_stats": sales_stats,
            "purchases_stats": purchases_stats,
            "cost_stats": cost_stats,
            "productivity_stats": CattleService.get_productivity_stats(),
            "net_profit": net_profit,
            "active_withdrawal_count": HealthService.get_active_withdrawal_count(),
            "recent_health_events": HealthService.get_recent_events(limit=5),
            "weight_stats": WeightService.get_herd_adg_stats(),
            "location_stats": LocationService.get_dashboard_stats(),
            "low_stock_ingredients": FeedIngredient.objects.filter(
                stock_quantity__lte=F("min_stock_alert")
            )[:5],
            "overdue_tasks_count": (
                TaskService.get_overdue_tasks(user=self.request.user).count()
            ),
            "todays_tasks": TaskService.get_overdue_tasks(user=self.request.user)[:5],
        }
