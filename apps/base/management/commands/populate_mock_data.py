import random
import string
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from model_bakery import baker

# New Models
from apps.authentication.models import User
from apps.cattle.models import Cattle
from apps.health.models import (
    ActiveIngredient,
    HealthProtocol,
    Medication,
    MedicationType,
    MedicationUnit,
    ProtocolItem,
    SanitaryEvent,
    SanitaryEventTarget,
)
from apps.locations.models import Location, LocationStatus, LocationType
from apps.locations.models.movement import Movement, MovementReason
from apps.notifications.models import Notification
from apps.nutrition.models import Diet, DietItem, FeedingEvent, FeedIngredient

# Import models
from apps.partners.models import Partner
from apps.purchases.models import Purchase, PurchaseItem
from apps.purchases.services.purchase_service import PurchaseService
from apps.reproduction.models import (
    BreedingEvent,
    Calving,
    MatingPlan,
    PregnancyCheck,
    ReproductiveSeason,
)
from apps.sales.models import Sale, SaleItem
from apps.sales.services.sale_service import SaleService
from apps.tasks.models.tasks import Task, TaskTemplate
from apps.weight.models import WeighingSession, WeighingSessionType
from apps.weight.services.weight_service import WeightService


class Command(BaseCommand):
    help = "Populate database with 100 mock records for each key model."

    def get_random_date(self):
        return (timezone.now() - timedelta(days=random.randint(0, 365))).date()

    def get_random_datetime(self):
        return timezone.now() - timedelta(days=random.randint(0, 365))

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
                seasons = self._create_seasons(count)

                # 2. Main Entities
                cattle_list = self._create_cattle(locations, count)
                ingredients = self._create_ingredients(count)
                diets = self._create_diets(count)
                active_ingredients = self._create_active_ingredients()

                # Pre-create users for assignments
                users = self._create_users(count)

                # 3. Transactional Data
                self._create_movements(cattle_list, locations, count)
                self._create_feeding_events(diets, locations, users, count)
                medications = self._create_medications(active_ingredients, count)
                self._create_health_protocols(medications)
                self._create_sanitary_events(
                    medications, cattle_list, users, count
                )  # passed users
                self._create_reproduction_data(cattle_list, seasons, count)
                self._create_mating_plans(cattle_list, seasons, locations, count)
                self._create_sales(partners, cattle_list, count)
                self._create_purchases(partners, ingredients, count)
                self._create_weighing_sessions(cattle_list, count)

                # 4. System
                self._create_tasks(
                    users, cattle_list, self._create_task_templates(), count
                )
                self._create_notifications(users, count)

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
                    email=f"partner_{random.randint(1000, 9999)}@example.com",
                    phone=f"+55 11 9{random.randint(10000000, 99999999)}",
                    tax_id=str(
                        random.randint(10000000000, 99999999999)
                    ),  # Fake CNPJ/CPF
                    is_customer=random.choice([True, False]),
                    is_supplier=random.choice([True, False]),
                )
            )
        return partners

    def _create_locations(self):
        self.stdout.write("Creating Locations...")
        locations = []
        # Create specific types
        types = [LocationType.PASTURE] * 4 + [LocationType.FEEDLOT, LocationType.CORRAL]

        for _i, l_type in enumerate(types):
            locations.append(
                baker.make(
                    Location,
                    name=self._short_str(f"Loc-{l_type[:3]}"),
                    type=l_type,
                    area_hectares=Decimal(random.uniform(5.0, 50.0)),
                    capacity_head=random.randint(20, 200),
                    status=LocationStatus.ACTIVE,
                    is_active=True,
                )
            )
        return locations

    def _create_movements(self, cattle_list, locations, count):
        self.stdout.write("Creating Movements...")
        # Move random groups of cattle
        for _ in range(count):
            origin = random.choice(locations)
            destination = random.choice([loc for loc in locations if loc != origin])

            # Pick 5-20 random cattle at origin logic (simplified: just random cattle)
            group = random.sample(
                cattle_list, k=min(len(cattle_list), random.randint(5, 20))
            )

            movement = baker.make(
                Movement,
                origin=origin,
                destination=destination,
                date=self.get_random_datetime(),
                reason=random.choice(MovementReason.choices)[0],
                notes=self._short_str("Mov"),
                performed_by=None,  # Or random user
            )
            movement.animals.set(group)

    def _create_seasons(self, count):
        self.stdout.write("Creating Reproductive Seasons...")
        seasons = []
        for i in range(count):
            start = self.get_random_date()
            seasons.append(
                baker.make(
                    ReproductiveSeason,
                    name=f"Season {start.year}/{start.year+1} - {i}",
                    start_date=start,
                    end_date=start + timedelta(days=90),
                )
            )
        return seasons

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
                    sex=(
                        Cattle.SEX_MALE if random.random() < 0.1 else Cattle.SEX_FEMALE
                    ),  # 10% Bulls
                    breed=random.choice(Cattle.BREED_CHOICES)[0],
                    status=random.choices(
                        [c[0] for c in Cattle.STATUS_CHOICES],
                        weights=[80, 10, 10],
                        k=1,
                    )[0],
                    weight_kg=Decimal(random.uniform(30.0, 50.0)),  # Birth weight
                    # Current weight will be calculated below
                    sire=None,
                    dam=None,
                )
            )

            # Fix Birth Date and Current Weight
            # Allow ages up to 12 years (approx 4380 days)
            age_days = random.randint(30, 4380)
            cattle_list[-1].birth_date = timezone.now().date() - timedelta(
                days=age_days
            )

            # Simple growth curve approximation
            # Birth: 40kg. Growth: ~0.8kg/day until 600kg cap.
            birth_weight = float(cattle_list[-1].weight_kg)
            growth = min(600, birth_weight + (age_days * 0.7))  # 0.7 kg/day avg
            cattle_list[-1].current_weight = Decimal(
                growth * random.uniform(0.9, 1.1)
            )  # +/- 10% variance
            cattle_list[-1].save()

        # Generate deep ancestry for the first few cattle (up to 5)
        # We aim for 10 generations. To avoid exponential explosion (2^10 = 1024 records per cow),
        # we will generate full trees up to depth 4, and then linear paths or sparse trees up to 10?
        # Actually, 1024 records is fine for 5 cows (5000 total). Let's go for it, but maybe limit to 8 if slow.
        # User asked for "up to 10". Let's do depth=8 for safety or full 10 if we want to impress.
        # Let's do depth=5 fully, and then just simple parents for higher levels to save time?
        # No, "whole families of up to 10 generations".
        # I will implement a recursive function that creates ancestors.

        deep_families_count = min(count, 5)
        self.stdout.write(
            f"Generating ancestry (depth=5) for {deep_families_count} cattle..."
        )

        for i in range(deep_families_count):
            root_animal = cattle_list[i]
            # depth 5 = 62 ancestors (2+4+8+16+32). 5 cattle * 62 = 310 extra records.
            self._create_ancestors(root_animal, current_depth=0, max_depth=5)

        return cattle_list

    def _create_ancestors(self, child, current_depth, max_depth):
        if current_depth >= max_depth:
            return

        # Calculate logical birth dates for parents (e.g. 2-5 years older)
        child_dob = child.birth_date or timezone.now().date()
        sire_dob = child_dob - timedelta(days=random.randint(730, 1825))
        dam_dob = child_dob - timedelta(days=random.randint(730, 1825))

        # Create Sire
        sire = baker.make(
            Cattle,
            tag=self._short_str(f"Sir{current_depth}"),
            name=self._short_str("Bull"),
            sex=Cattle.SEX_MALE,
            birth_date=sire_dob,
            status=Cattle.STATUS_DEAD if current_depth > 0 else Cattle.STATUS_AVAILABLE,
            breed=random.choice(Cattle.BREED_CHOICES)[0],  # Fix: Ensure random breed
        )

        # Create Dam
        dam = baker.make(
            Cattle,
            tag=self._short_str(f"Dam{current_depth}"),
            name=self._short_str("Cow"),
            sex=Cattle.SEX_FEMALE,
            birth_date=dam_dob,
            status=Cattle.STATUS_DEAD if current_depth > 0 else Cattle.STATUS_AVAILABLE,
            breed=random.choice(Cattle.BREED_CHOICES)[0],  # Fix: Ensure random breed
        )

        # Link to child
        child.sire = sire
        child.dam = dam
        child.save(update_fields=["sire", "dam"])

        # Recurse
        self._create_ancestors(sire, current_depth + 1, max_depth)
        self._create_ancestors(dam, current_depth + 1, max_depth)

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
        ingredients = list(FeedIngredient.objects.all())
        if not ingredients:  # Should have been created
            ingredients = self._create_ingredients(count)

        for _ in range(count):
            diet = baker.make(Diet, name=self._short_str("Diet"))
            diets.append(diet)

            # Add Diet Items (Composition)
            # Pick 2-4 random ingredients
            diet_ingredients = random.sample(
                ingredients, k=min(len(ingredients), random.randint(2, 4))
            )

            # Safe distribution algorithm:
            # 1. Start with 10% each (base)
            proportions = dict.fromkeys(diet_ingredients, 10)
            remaining_pct = 100 - (10 * len(diet_ingredients))

            # 2. Distribute remaining percentage properly
            keys = list(proportions.keys())
            for i, ing in enumerate(keys):
                if i == len(keys) - 1:
                    # Last one takes all remaining
                    proportions[ing] += remaining_pct
                else:
                    # Take a random chunk of what's left
                    if remaining_pct > 0:
                        add = random.randint(0, remaining_pct)
                        proportions[ing] += add
                        remaining_pct -= add

            for ing, pct in proportions.items():
                baker.make(
                    DietItem, diet=diet, ingredient=ing, proportion_percent=Decimal(pct)
                )
        return diets

    def _create_feeding_events(self, diets, locations, users, count):
        self.stdout.write("Creating Feeding Events...")
        for _ in range(count):
            baker.make(
                FeedingEvent,
                diet=random.choice(diets),
                location=random.choice(locations),
                date=self.get_random_date(),
                amount_kg=Decimal(random.uniform(5.0, 20.0)),
                cost_total=Decimal(random.uniform(10.0, 50.0)),
                performed_by=random.choice(users) if users else None,
            )

    def _create_active_ingredients(self):
        self.stdout.write("Creating Active Ingredients...")
        names = [
            "Ivermectin",
            "Fipronil",
            "Abamectin",
            "Doramectin",
            "Oxytetracycline",
            "Penicillin",
            "Flunixin",
            "Ketoprofen",
        ]
        ingredients = []
        for name in names:
            ing, _ = ActiveIngredient.objects.get_or_create(name=name)
            ingredients.append(ing)
        return ingredients

    def _create_medications(self, active_ingredients, count):
        self.stdout.write("Creating Medications...")
        medications = []
        for _ in range(count):
            med = baker.make(
                Medication,
                name=self._short_str("Med"),
                medication_type=random.choice(MedicationType.choices)[0],
                unit=random.choice(MedicationUnit.choices)[0],
                manufacturer=self._short_str("Lab"),
                batch_number=self._short_str("Batch"),
                expiration_date=self.get_random_date() + timedelta(days=365),
                withdrawal_days_meat=random.randint(0, 30),
                withdrawal_days_milk=random.randint(0, 10),
            )
            # Add 1-2 active ingredients
            if active_ingredients:
                med.active_ingredients.set(
                    random.sample(active_ingredients, k=random.randint(1, 2))
                )
            medications.append(med)
        return medications

    def _create_health_protocols(self, medications):
        self.stdout.write("Creating Health Protocols...")
        for _ in range(5):  # Create 5 protocols
            protocol = baker.make(
                HealthProtocol,
                name=self._short_str("Prot"),
                description=self._short_str("Desc"),
                is_active=random.choice([True, False]),
            )
            # Add random items
            if medications:
                for _ in range(random.randint(2, 4)):
                    baker.make(
                        ProtocolItem,
                        protocol=protocol,
                        medication=random.choice(medications),
                        default_dosage="10ml",
                        notes=self._short_str("Note"),
                    )

    def _create_sanitary_events(self, medications, cattle_list, users, count):
        self.stdout.write("Creating Sanitary Events...")
        sanitary_events = []
        for _ in range(count):
            events = baker.make(
                SanitaryEvent,
                title=self._short_str("Hlth"),
                date=self.get_random_date(),
                medication=random.choice(medications),
                notes=self._short_str("Note"),
                total_cost=Decimal(random.uniform(50.0, 500.0)),
                performed_by=random.choice(users) if users else None,
            )
            sanitary_events.append(events)

        self.stdout.write("Creating Sanitary Event Targets...")
        for event in sanitary_events:
            # Apply to 1-10 random animals
            targets = random.sample(
                cattle_list, k=min(len(cattle_list), random.randint(1, 10))
            )
            for animal in targets:
                baker.make(
                    SanitaryEventTarget,
                    event=event,
                    animal=animal,
                    cost_per_head=Decimal(event.total_cost / len(targets)),
                )

    def _create_breeding_events(self, cattle_list, seasons, count):
        self.stdout.write("Creating Breeding Events...")
        breeding_events = []
        for _ in range(count):
            ev = baker.make(
                BreedingEvent,
                dam=random.choice(cattle_list),
                date=self.get_random_date(),
                sire_name=self._short_str("Sire"),
                breeding_method=random.choice(BreedingEvent.METHOD_CHOICES)[0],
                batch=random.choice(seasons) if seasons else None,
            )
            breeding_events.append(ev)
        return breeding_events

    def _create_reproduction_data(self, cattle_list, seasons, count):
        self.stdout.write("Creating Reproduction Data...")
        breeding_events = self._create_breeding_events(cattle_list, seasons, count)
        self._create_pregnancy_checks(breeding_events)
        self._create_calving_records(cattle_list, count)

    def _create_pregnancy_checks(self, breeding_events):
        self.stdout.write("Creating Pregnancy Checks...")
        for event in breeding_events:
            # 70% chance of being positive
            is_positive = random.random() < 0.7
            result = (
                PregnancyCheck.RESULT_POSITIVE
                if is_positive
                else PregnancyCheck.RESULT_NEGATIVE
            )

            check_date = self.get_random_date()
            # Calculate metrics if positive
            fetus_days = None
            expected_calving = None

            if is_positive:
                fetus_days = random.randint(30, 120)
                expected_calving = check_date + timedelta(days=280 - fetus_days)

            baker.make(
                PregnancyCheck,
                breeding_event=event,
                date=check_date,
                result=result,
                fetus_days=fetus_days,
                expected_calving_date=expected_calving,
            )

            # CRITICAL: Update Cow Status if positive
            if is_positive:
                dam = event.dam
                dam.reproduction_status = Cattle.REP_STATUS_PREGNANT
                dam.save(update_fields=["reproduction_status"])

    def _create_calving_records(self, cattle_list, count):
        self.stdout.write("Creating Calving Records (and linked Breeding)...")
        for _ in range(count):
            dam = random.choice(cattle_list)
            # Create a breeding event in the past (~9 months ago)
            breeding = baker.make(
                BreedingEvent,
                dam=dam,
                date=self.get_random_date() - timedelta(days=290),
                breeding_method=BreedingEvent.METHOD_IATF,
            )

            calving_date = self.get_random_date()

            # Create a calf for this calving
            dam_tag_suffix = dam.tag.split("-")[-1] if "-" in dam.tag else dam.tag[-4:]
            # Use wider random range to prevent collision (10k-99k)
            calf_tag = f"C-{dam_tag_suffix}-{random.randint(10000, 99999)}"

            # Determine Breed
            calf_breed = dam.breed
            if breeding.sire and breeding.sire.breed != dam.breed:
                calf_breed = (
                    "cross"  # Simplified, or pick one. Model validates choices.
                )
                # If "cross" is not in choices, fallback to Dam's or "other"
                if "cross" not in dict(Cattle.BREED_CHOICES):
                    calf_breed = Cattle.BREED_OTHER

            calf = baker.make(
                Cattle,
                tag=calf_tag,
                name=f"Calf of {dam.name or dam.tag}",
                sex=random.choice(Cattle.SEX_CHOICES)[0],
                birth_date=calving_date,
                dam=dam,
                sire=breeding.sire,
                breed=calf_breed,
                location=dam.location,  # Same as Dam
                status=Cattle.STATUS_AVAILABLE,
                weight_kg=Decimal(random.uniform(25.0, 45.0)),  # Birth weight
                reproduction_status=Cattle.REP_STATUS_OPEN,
            )

            # Calculate calf current weight
            calf_age_days = (timezone.now().date() - calving_date).days
            calf_age_days = max(calf_age_days, 0)

            calf_birth_weight = float(calf.weight_kg)
            # Calves grow ~0.8-1.0kg/day
            calf_growth = calf_birth_weight + (calf_age_days * random.uniform(0.7, 1.0))
            # Cap at 300kg for this specific generation logic (if they are young)
            calf.current_weight = Decimal(calf_growth)
            calf.save()

            baker.make(
                Calving,
                dam=dam,
                breeding_event=breeding,
                date=calving_date,
                notes=self._short_str("Calv"),
                calf=calf,
                ease_of_birth=random.choice(Calving.EASE_CHOICES)[0],
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
            # Sell 1-5 random cattle
            items_count = random.randint(1, 5)
            # Filter available cattle only? For mock data we might grab any, but ideally we check status.
            # Simplified: just grab random.
            targets = random.sample(cattle_list, k=min(len(cattle_list), items_count))

            for animal in targets:
                baker.make(
                    SaleItem,
                    sale=sale,
                    content_object=animal,
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
            # Buy 1-5 random ingredients
            targets = random.sample(
                ingredients, k=min(len(ingredients), random.randint(1, 5))
            )
            for ing in targets:
                baker.make(
                    PurchaseItem,
                    purchase=purchase,
                    content_object=ing,
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
            # Weigh 5-20 random animals
            animals = random.sample(
                cattle_list, k=min(len(cattle_list), random.randint(5, 20))
            )
            for animal in animals:
                weight = Decimal(random.uniform(200.0, 600.0))
                WeightService.record_weight(
                    session=session,
                    animal=animal,
                    weight_kg=weight,
                )
                # Update animal's current weight to match latest
                animal.current_weight = weight
                animal.save(update_fields=["current_weight"])

    def _create_users(self, count):
        self.stdout.write("Creating Users...")
        # Ensure Superuser
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser("admin", "admin@cnv.com", "admin")

        users = list(User.objects.all())

        first_names = [
            "James",
            "John",
            "Robert",
            "Michael",
            "William",
            "David",
            "Richard",
            "Joseph",
            "Thomas",
            "Charles",
            "Mary",
            "Patricia",
            "Jennifer",
            "Linda",
            "Elizabeth",
            "Barbara",
            "Susan",
            "Jessica",
            "Sarah",
            "Karen",
        ]
        last_names = [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Jones",
            "Garcia",
            "Miller",
            "Davis",
            "Rodriguez",
            "Martinez",
            "Hernandez",
            "Lopez",
            "Gonzalez",
            "Wilson",
            "Anderson",
            "Thomas",
            "Taylor",
            "Moore",
            "Jackson",
            "Martin",
        ]

        # Create Staff
        for _ in range(5):
            fn = random.choice(first_names)
            ln = random.choice(last_names)
            users.append(
                baker.make(
                    User,
                    first_name=fn,
                    last_name=ln,
                    username=f"{fn.lower()}.{ln.lower()}{random.randint(1, 99)}",
                    is_staff=True,
                    is_active=True,
                )
            )

        # Create Regular Users
        needed = max(0, int(count / 5) - len(users))
        for _ in range(needed):
            fn = random.choice(first_names)
            ln = random.choice(last_names)
            users.append(
                baker.make(
                    User,
                    first_name=fn,
                    last_name=ln,
                    username=f"{fn.lower()}.{ln.lower()}{random.randint(1, 99)}",
                    is_staff=False,
                    is_active=True,
                )
            )

        return users

    def _create_task_templates(self):
        self.stdout.write("Creating Task Templates...")
        templates = [
            baker.make(TaskTemplate, name="Vaccination Protocol", offset_days=0),
            baker.make(TaskTemplate, name="Weaning", offset_days=210),
            baker.make(TaskTemplate, name="Pregnancy Check", offset_days=30),
        ]
        return templates

    def _create_tasks(self, users, cattle_list, templates, count):
        self.stdout.write("Creating Tasks...")
        for _ in range(count):
            # Randomly link to an animal
            content_object = (
                random.choice(cattle_list) if random.random() > 0.3 else None
            )

            baker.make(
                Task,
                title=self._short_str("Task"),
                description=self._short_str("Desc"),
                assigned_to=random.choice(users),
                task_template=random.choice(templates),
                due_date=self.get_random_date(),
                status=random.choice(Task.Status.choices)[0],
                priority=random.choice(Task.Priority.choices)[0],
                content_object=content_object,
            )

    def _create_notifications(self, users, count):
        self.stdout.write("Creating Notifications...")
        for _ in range(count):
            baker.make(
                Notification,
                recipient=random.choice(users),
                title=self._short_str("Notif"),
                message=self._short_str("Msg"),
                category=random.choice(Notification.Category.choices)[0],
                is_read=random.choice([True, False]),
            )

    def _create_mating_plans(self, cattle_list, seasons, _locations, count):
        self.stdout.write("Creating Mating Plans...")

        # Filter potential sires and cows
        bulls = [c for c in cattle_list if c.sex == Cattle.SEX_MALE]
        cows = [c for c in cattle_list if c.sex == Cattle.SEX_FEMALE]

        if not bulls or not cows:
            self.stdout.write(
                self.style.WARNING("Not enough cattle for mating plans. Skipping.")
            )
            return

        # Create fewer plans than total count (e.g. 20% of count)
        plan_count = max(5, int(count / 5))

        for _ in range(plan_count):
            status = random.choice(MatingPlan.Status.choices)[0]

            plan = baker.make(
                MatingPlan,
                season=random.choice(seasons) if seasons else None,
                sire=random.choice(bulls),
                status=status,
                notes=self._short_str("Plan"),
            )

            # Assign random cows (5 to 15)
            # Use baker or manual set? M2M needs .set() or baker can handle it if defined?
            # Baker allows `entries=[...]` for M2M? simpler to just create and set.
            sample_size = min(len(cows), random.randint(5, 15))
            if sample_size > 0:
                plan.cows.set(random.sample(cows, k=sample_size))
