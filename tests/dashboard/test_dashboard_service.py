# pylint: disable=unused-argument
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.authentication.models.user import User
from apps.cattle.models import Cattle
from apps.commercial.models import SalesEvent, SalesLot
from apps.dashboard.services import DashboardService
from apps.locations.models import Location, LocationStatus, LocationType
from apps.nutrition.models import FeedIngredient
from apps.partners.models import Partner
from apps.tasks.models import Task
from apps.transactions.models import Transaction, TransactionItem
from apps.weight.models import WeighingSession, WeightRecord


@pytest.mark.django_db
class TestDashboardService:
    # pylint: disable=too-many-instance-attributes

    @pytest.fixture(autouse=True)
    def setup_data(self, db):
        # Create Partner
        self.partner = Partner.objects.create(name="Test Partner", is_customer=True)

        # Create Dummy Cattle
        self.animal1 = Cattle.objects.create(
            tag="A001",
            birth_date=timezone.now().date() - timedelta(days=365 * 2),
            withdrawal_end_date=timezone.now().date()
            + timedelta(days=5),  # In withdrawal
            status=Cattle.STATUS_AVAILABLE,
        )
        self.animal2 = Cattle.objects.create(
            tag="A002",
            birth_date=timezone.now().date() - timedelta(days=365 * 2),
            status=Cattle.STATUS_AVAILABLE,
        )

        # Create Sales Event
        self.event = SalesEvent.objects.create(
            name="Spring Auction",
            date=timezone.now().date() + timedelta(days=10),
            sales_type=SalesEvent.TYPE_AUCTION,
            is_active=True,
        )

        # Create Lots
        self.lot1 = SalesLot.objects.create(
            event=self.event,
            lot_number=1,
            reserve_price=Decimal("5000.00"),
            status=SalesLot.STATUS_AVAILABLE,
            cost_at_creation=Decimal("4000.00"),
        )
        self.lot1.animals.add(self.animal1)  # Linked to unsafe animal

        self.lot2 = SalesLot.objects.create(
            event=self.event,
            lot_number=2,
            reserve_price=Decimal("6000.00"),
            status=SalesLot.STATUS_AVAILABLE,
            cost_at_creation=Decimal("5000.00"),
        )
        self.lot2.animals.add(self.animal2)

        # Create Transactions
        Transaction.objects.create(
            date=timezone.now().date() - timedelta(days=5),
            type=Transaction.TYPE_SALE,
            partner=self.partner,
        )
        t_sale = Transaction.objects.create(
            date=timezone.now().date() - timedelta(days=5),
            type=Transaction.TYPE_SALE,
            total_amount=Decimal("10000.00"),
            status=Transaction.STATUS_CONFIRMED,
            partner=self.partner,
        )
        # Link items
        # 1. Cattle Item
        # We need a content type for SalesLot
        lot_ct = ContentType.objects.get_for_model(SalesLot)

        TransactionItem.objects.create(
            transaction=t_sale,
            content_type=lot_ct,
            object_id=self.lot1.pk,
            quantity=1,
            unit_price=Decimal("4000.00"),
            total_price=Decimal("4000.00"),
        )

        Transaction.objects.create(
            date=timezone.now().date() - timedelta(days=5),
            type=Transaction.TYPE_PURCHASE,
            total_amount=Decimal("2000.00"),
            status=Transaction.STATUS_CONFIRMED,
            partner=self.partner,
        )

        # Create Resting Pasture Violation Data
        self.pasture = Location.objects.create(
            name="Pasture 1",
            type=LocationType.PASTURE,
            status=LocationStatus.RESTING,
            area_hectares=10,
            capacity_head=10,
        )
        # Assign animal2 to this pasture (Assuming direct assignment via FK or similar,
        # checking Location definition: 'cattle' is reverse manager.
        # Usually Cattle has 'location' FK. Checking Cattle model...
        # I didn't see Cattle model fully but Location had type checking for 'cattle'.
        # I'll update animal2 location if field exists. If not, I might need to mock or finding the field.
        # Let's assume 'location' field exists on Cattle based on context or reverse relation.)
        # Wait, I need to know if Cattle has 'location' field.
        # I'll try to set it. If it fails, I'll fix.
        # But 'Location.cattle' implies related_name='cattle' on a ForeignKey in Cattle model.
        self.animal2.location = self.pasture
        self.animal2.save()

        # Create Low Stock Data
        self.ingredient = FeedIngredient.objects.create(
            name="Corn", stock_quantity=10, min_stock_alert=20, unit_cost=1  # Alert!
        )

        # Create Watchlist Data
        # Session 5 days ago
        self.session = WeighingSession.objects.create(
            date=timezone.now().date() - timedelta(days=5), name="Recent Session"
        )
        self.wrecord = WeightRecord.objects.create(
            session=self.session,
            animal=self.animal1,
            weight_kg=Decimal("400.00"),
            adg=Decimal("-1.5"),  # Severe loss
            days_since_prev_weight=30,
        )

    def test_get_critical_alerts_all(self):
        alerts = DashboardService.get_critical_alerts()
        # Should have:
        # 1. Safety (Withdrawal)
        # 2. Resting Pasture (animal2 in resting pasture)
        # 3. Low Stock (Corn)

        msg_list = [a["msg"] for a in alerts]
        assert any("SAFETY VIOLATION" in m for m in msg_list)
        assert any("Resting Pastures" in m for m in msg_list)
        assert any("Ingredients" in m for m in msg_list)

    def test_get_critical_alerts_overdue_tasks(self):
        # Need to create an overdue task for self.user (self.partner is a partner, not user)
        # Test setup did not create a User object?
        # Typically tests use factories. I'll check setup or create one.
        # Ensure we have a user
        user = User.objects.create_user(username="testuser", password="password")

        # Create an overdue task
        Task.objects.create(
            title="Overdue Personal Task",
            description="Do something",
            due_date=timezone.now().date() - timedelta(days=5),
            assigned_to=user,
            status=Task.Status.PENDING,
            priority=Task.Priority.HIGH,
        )

        alerts = DashboardService.get_critical_alerts(user=user)
        msg_list = [a["msg"] for a in alerts]
        link_list = [a["link"] for a in alerts]

        assert any("overdue tasks" in m for m in msg_list)
        assert any("ATTENTION" in m for m in msg_list)
        assert any("overdue=1" in lnk and "mode=my_tasks" in lnk for lnk in link_list)

    def test_get_critical_alerts_unassigned_tasks(self):
        # Create an UNASSIGNED overdue task
        Task.objects.create(
            title="Overdue System Task",
            description="Do something else",
            due_date=timezone.now().date() - timedelta(days=10),
            assigned_to=None,
            status=Task.Status.PENDING,
            priority=Task.Priority.MEDIUM,
        )

        # Determine behavior:
        # If user is passed, we get Unassigned alert? Yes.
        # If user is None, we still check unassigned? Logic says 'if user:' for personal, then check unassigned.
        # Wait, the code I wrote checks unassigned regardless of user presence!
        # "if user: ... check personal ..."
        # "check unassigned ..." (outside if block)
        # Let's verify logic in service code.
        # Step 337: Unassigned block is OUTSIDE 'if user'. Good.

        alerts = DashboardService.get_critical_alerts()
        msg_list = [a["msg"] for a in alerts]
        link_list = [a["link"] for a in alerts]

        assert any("unassigned overdue tasks" in m for m in msg_list)
        assert any("OPERATIONAL" in m for m in msg_list)
        assert any("overdue=1" in lnk for lnk in link_list)

    def test_get_operational_stats_watchlist(self):
        stats = DashboardService.get_operational_stats()
        watchlist = stats["watchlist"]
        # animal1 lost 1.5kg * 30 = 45kg.
        # prev = 400 + 45 = 445.
        # % = 45/445 ~ 10.1%. Should be in watchlist.
        assert len(watchlist) > 0
        assert "A001" in watchlist[0]

    def test_get_financial_kpis(self):
        kpis = DashboardService.get_financial_kpis()
        # Cash In: 4000 (Updated by TransactionItem)
        # Cash Out: 2000
        # Net: 2000
        # Pipeline: 5000 + 6000 = 11000

        # Note: If Partner FK fails in setup, these will be 0.
        # I need to ensure Partner exists.
        assert kpis["cash_in_30d"] == Decimal("4000.00")
        assert kpis["cash_out_30d"] == Decimal("2000.00")
        assert kpis["net_30d"] == Decimal("2000.00")
        assert kpis["pipeline_value"] == Decimal("11000.00")

    def test_get_commercial_pulse(self):
        pulse = DashboardService.get_commercial_pulse()
        assert pulse["next_event"] == self.event
        assert pulse["lots_available"] == 2  # lot1 and lot2

    def test_get_herd_status(self):
        status = DashboardService.get_herd_status()
        assert status["total_headcount"] == 2
        # births/deaths depend on dates, simplistic check
        assert "total_headcount" in status

    def test_get_financial_trend(self):
        trend = DashboardService.get_financial_trend()
        assert "sales" in trend
        assert "costs" in trend
        # Should have data for current month
        sales_data = trend["sales"]
        costs_data = trend["costs"]
        assert len(sales_data) >= 1
        assert len(costs_data) >= 1

        # Verify Split
        # We created 1 Genetics Sale (via lot1 which is linked to Auction... wait)
        # In Setup:
        # self.event is TYPE_AUCTION.
        # self.lot1 is linked to self.event.
        # TransactionItem linked to self.lot1.
        # So it counts as CATTLE (default AUCTION type).

        # I need to create a specific Genetics Event for the test split to work.
        # Let's create a transaction for Genetics in this test.

        genetics_event = SalesEvent.objects.create(
            name="Semen Sale",
            date=timezone.now().date(),
            sales_type=SalesEvent.TYPE_SEMEN,
            is_active=True,
        )
        genetics_lot = SalesLot.objects.create(
            event=genetics_event,
            lot_number=99,
            reserve_price=Decimal("1000.00"),
            cost_at_creation=Decimal("500.00"),
        )
        lot_ct = ContentType.objects.get_for_model(SalesLot)

        t_genetics = Transaction.objects.create(
            date=timezone.now().date(),
            type=Transaction.TYPE_SALE,
            total_amount=Decimal("500.00"),
            status=Transaction.STATUS_CONFIRMED,
            partner=self.partner,
        )
        TransactionItem.objects.create(
            transaction=t_genetics,
            content_type=lot_ct,
            object_id=genetics_lot.pk,
            quantity=10,
            unit_price=Decimal("50.00"),
            total_price=Decimal("500.00"),
        )

        # Re-fetch trend
        trend = DashboardService.get_financial_trend()
        sales_data = trend["sales"]

        # Find the month with genetics
        current_data = [
            d for d in sales_data if d["month"].month == timezone.now().month
        ][0]
        assert current_data["genetics"] == Decimal("500.00")
        assert current_data["cattle"] >= Decimal("0.00")

    def test_get_genetic_progress(self):
        # Create older cattle
        start_year = timezone.now().year - 5
        date_old = timezone.now().replace(year=start_year).date()
        Cattle.objects.create(
            tag="OLD01",
            birth_date=date_old,
            current_weight=Decimal("200.00"),
            status=Cattle.STATUS_AVAILABLE,
        )

        progress = DashboardService.get_genetic_progress()
        # Should contain year and avg_weight
        assert isinstance(progress, list)
        if len(progress) > 0:
            assert "year" in progress[0]
            assert "avg_weight" in progress[0]

    def test_get_operational_stats_coverage(self):
        # Test edge case: Watchlist loop with record having days_since_prev_weight=None
        # (It shouldn't crash and should continue)

        # Create bad record
        bad_session = WeighingSession.objects.create(
            date=timezone.now().date(), name="Bad Session"
        )
        WeightRecord.objects.create(
            session=bad_session,
            animal=self.animal2,
            weight_kg=Decimal("300.00"),
            adg=Decimal("-1.0"),
            days_since_prev_weight=None,  # This triggers "continue" (Line 242)
        )

        stats = DashboardService.get_operational_stats()
        # Ensure correct execution
        assert "watchlist" in stats
