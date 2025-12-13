import random
import string
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.health.models import (
    Medication,
    MedicationType,
    MedicationUnit,
    SanitaryEvent,
    SanitaryEventTarget,
)
from apps.locations.models import Location
from apps.nutrition.models import Diet, FeedingEvent, FeedIngredient

# Import models
from apps.partners.models import Partner
from apps.purchases.models import Purchase, PurchaseItem
from apps.purchases.services.purchase_service import PurchaseService
from apps.reproduction.models import (
    BreedingEvent,
    Calving,
    PregnancyCheck,
    ReproductiveSeason,
)
from apps.sales.models import Sale, SaleItem
from apps.sales.services.sale_service import SaleService
from apps.weight.models import WeighingSession, WeighingSessionType
from apps.weight.services.weight_service import WeightService


class Command(BaseCommand):
    help = "Populate database with 100 mock records for each key model."

    def get_random_date(self):
        return (timezone.now() - timedelta(days=random.randint(0, 365))).date()

    def _short_str(self, prefix="Str"):
        """Returns a string with max 15 characters."""
        # prefix (e.g. 3 chars) + '-' + 11 random chars = 15
        available = 15 - len(prefix) - 1
        if available < 1:
            return prefix[:15]

        suffix = "".join(
            random.choices(string.ascii_letters + string.digits, k=available)
        )
        return f"{prefix}-{suffix}"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of records to create per model",
        )

    def handle(self, *args, **options):
        count = options["count"]
        self.stdout.write(
            self.style.WARNING(f"Starting data population (count={count})...")
        )

        try:
            with transaction.atomic():
                # 1. Base dependencies
                partners = self._create_partners(count)
                locations = self._create_locations()  # locations count is fixed at 5
                self._create_seasons(count)

                # 2. Main Entities
                cattle_list = self._create_cattle(locations, count)
                ingredients = self._create_ingredients(count)
                diets = self._create_diets(count)

                # 3. Transactional Data
                self._create_feeding_events(diets, locations, count)
                medications = self._create_medications(count)
                self._create_sanitary_events(medications, cattle_list, count)
                breeding_events = self._create_breeding_events(cattle_list, count)
                self._create_pregnancy_checks(breeding_events)
                self._create_calving_records(cattle_list, count)
                self._create_sales(partners, cattle_list, count)
                self._create_purchases(partners, ingredients, count)
                self._create_weighing_sessions(cattle_list, count)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error populating data: {e}"))
            raise e

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully populated database with 100 records for each model!"
            )
        )

    def _create_partners(self, count):
        self.stdout.write("Creating Partners...")
        partners = []
        for _ in range(count):
            partners.append(
                baker.make(
                    Partner,
                    name=self._short_str("Prt"),
                    email=self._short_str("mb")
                    + "@ex.com",  # Email might be longer, but name is key? Instruction says "strings". I'll keep email reasonable but valid.
                    is_customer=random.choice([True, False]),
                    is_supplier=random.choice([True, False]),
                )
            )
        return partners

    def _create_locations(self):
        self.stdout.write("Creating Locations...")
        locations = []
        for _ in range(5):
            locations.append(
                baker.make(
                    Location,
                    name=self._short_str("Loc"),
                    area_hectares=Decimal(random.uniform(0.5, 4.9)),
                    capacity_head=random.randint(10, 100),
                )
            )
        return locations

    def _create_seasons(self, count):
        self.stdout.write("Creating Reproductive Seasons...")
        for _ in range(count):
            baker.make(ReproductiveSeason, name=self._short_str("Sea"))

    def _create_cattle(self, locations, count):
        self.stdout.write("Creating Cattle...")
        cattle_list = []
        for _ in range(count):
            cattle_list.append(
                baker.make(
                    Cattle,
                    tag=self._short_str("Tag"),
                    name=self._short_str("Cow"),
                    location=random.choice(locations) if locations else None,
                    birth_date=self.get_random_date(),
                    sex=random.choice(Cattle.SEX_CHOICES)[0],
                    breed=random.choice(Cattle.BREED_CHOICES)[0],
                    status=random.choices(
                        [c[0] for c in Cattle.STATUS_CHOICES],
                        weights=[80, 10, 10],
                        k=1,
                    )[0],
                    weight_kg=Decimal(random.uniform(30.0, 50.0)),  # Birth weight
                    current_weight=Decimal(
                        random.uniform(200.0, 600.0)
                    ),  # Initial guess
                )
            )
        return cattle_list

    def _create_ingredients(self, count):
        self.stdout.write("Creating Ingredients...")
        ingredients = []
        for _ in range(count):
            ingredients.append(
                baker.make(
                    FeedIngredient,
                    name=self._short_str("Ing"),
                    stock_quantity=Decimal(random.uniform(1000.0, 10000.0)),
                    unit_cost=Decimal(random.uniform(0.5, 10.0)),
                    min_stock_alert=Decimal(random.uniform(100.0, 1000.0)),
                )
            )
        return ingredients

    def _create_diets(self, count):
        self.stdout.write("Creating Diets...")
        diets = []
        for _ in range(count):
            diets.append(baker.make(Diet, name=self._short_str("Diet")))
        return diets

    def _create_feeding_events(self, diets, locations, count):
        self.stdout.write("Creating Feeding Events...")
        for _ in range(count):
            baker.make(
                FeedingEvent,
                diet=random.choice(diets),
                location=random.choice(locations),
                date=self.get_random_date(),
            )

    def _create_medications(self, count):
        self.stdout.write("Creating Medications...")
        medications = []
        for _ in range(count):
            medications.append(
                baker.make(
                    Medication,
                    name=self._short_str("Med"),
                    medication_type=random.choice(MedicationType.choices)[0],
                    unit=random.choice(MedicationUnit.choices)[0],
                )
            )
        return medications

    def _create_sanitary_events(self, medications, cattle_list, count):
        self.stdout.write("Creating Sanitary Events...")
        sanitary_events = []
        for _ in range(count):
            events = baker.make(
                SanitaryEvent,
                title=self._short_str("Hlth"),
                date=self.get_random_date(),
                medication=random.choice(medications),
                notes=self._short_str("Note"),
            )
            sanitary_events.append(events)

        self.stdout.write("Creating Sanitary Event Targets...")
        for event in sanitary_events:
            baker.make(
                SanitaryEventTarget,
                event=event,
                animal=random.choice(cattle_list),
            )

    def _create_breeding_events(self, cattle_list, count):
        self.stdout.write("Creating Breeding Events...")
        breeding_events = []
        for _ in range(count):
            ev = baker.make(
                BreedingEvent,
                dam=random.choice(cattle_list),
                date=self.get_random_date(),
                sire_name=self._short_str("Sire"),  # Explicitly short sire name
            )
            breeding_events.append(ev)
        return breeding_events

    def _create_pregnancy_checks(self, breeding_events):
        self.stdout.write("Creating Pregnancy Checks...")
        for event in breeding_events:
            baker.make(
                PregnancyCheck,
                breeding_event=event,
                date=self.get_random_date(),
            )

    def _create_calving_records(self, cattle_list, count):
        self.stdout.write("Creating Calving Records...")
        for _ in range(count):
            baker.make(
                Calving,
                dam=random.choice(cattle_list),
                date=self.get_random_date(),
                notes=self._short_str("Note"),
            )

    def _create_sales(self, partners, cattle_list, count):
        self.stdout.write("Creating Sales...")
        sales = []
        for _ in range(count):
            sales.append(
                baker.make(
                    Sale,
                    partner=random.choice(partners),
                    date=self.get_random_date(),
                    notes=self._short_str("Note"),
                )
            )

        self.stdout.write("Creating Sale Items...")
        for sale in sales:
            # Sell cattle
            baker.make(
                SaleItem,
                sale=sale,
                content_object=random.choice(cattle_list),
                quantity=1,
                unit_price=1000.00,
            )
            SaleService.update_sale_totals(sale)

    def _create_purchases(self, partners, ingredients, count):
        self.stdout.write("Creating Purchases...")
        purchases = []
        for _ in range(count):
            purchases.append(
                baker.make(
                    Purchase,
                    partner=random.choice(partners),
                    date=self.get_random_date(),
                    notes=self._short_str("Note"),
                )
            )

        self.stdout.write("Creating Purchase Items...")
        for purchase in purchases:
            # Buy Ingredients
            baker.make(
                PurchaseItem,
                purchase=purchase,
                content_object=random.choice(ingredients),
                quantity=100,
                unit_price=10.00,
            )

            PurchaseService.update_purchase_totals(purchase)

    def _create_weighing_sessions(self, cattle_list, count):
        self.stdout.write("Creating Weighing Sessions...")
        sessions = []
        for _ in range(count):
            sessions.append(
                baker.make(
                    WeighingSession,
                    name=self._short_str("Ses"),
                    date=self.get_random_date(),
                    session_type=random.choice(WeighingSessionType.choices)[0],
                )
            )

        self.stdout.write("Creating Weight Records...")
        for session in sessions:
            # Weigh a random animal in this session
            animal = random.choice(cattle_list)
            WeightService.record_weight(
                session=session,
                animal=animal,
                weight_kg=Decimal(random.uniform(200.0, 600.0)),
            )
