from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.locations.models import Location, LocationType
from apps.reproduction.models import MatingExclusion, MatingPlan
from apps.reproduction.services.mating_service import MatingPlanService


@pytest.mark.django_db
class TestMatingPlanModel:
    def test_str(self):
        # MatingPlan __str__ uses sire.name and season.name.
        # Cattle might not have 'name' set if we only set 'tag'.
        # But let's assume we set tag. If Cattle has no name field, it might use str(cattle) which is tag.
        # Let's check Cattle model first. If it has name, we should set it.
        # Based on previous reads, Cattle has 'name' field.
        plan = baker.make(
            MatingPlan, season__name="2025", sire__tag="BULL001", sire__name="Hercules"
        )
        assert "2025" in str(plan)
        # __str__ format: f"{self.sire.name} - {self.season.name}"
        assert "Hercules" in str(plan)

    def test_defaults(self):
        plan = MatingPlan.objects.create(
            season=baker.make("reproduction.ReproductiveSeason"),
            sire=baker.make(Cattle, sex=Cattle.SEX_MALE),
        )
        assert plan.status == MatingPlan.Status.DRAFT


@pytest.mark.django_db
class TestMatingExclusionModel:
    def test_str_representation(self):
        """Test the __str__ method of MatingExclusion (line 81 coverage)."""
        bull = baker.make(
            Cattle, name="Bull X", tag="BULLX", status=Cattle.STATUS_AVAILABLE
        )
        cow = baker.make(
            Cattle, name="Cow Y", tag="COWY", status=Cattle.STATUS_AVAILABLE
        )
        exclusion = baker.make(MatingExclusion, animal_a=bull, animal_b=cow)

        # Cattle __str__ is "TAG (Status)"
        expected_str = "Exclusion: BULLX (Available) x COWY (Available)"
        assert expected_str in str(exclusion)


@pytest.mark.django_db
class TestMatingPlanService:
    def test_crud_lifecycle(self):
        # Create
        plan = baker.make(MatingPlan, status=MatingPlan.Status.DRAFT)
        assert MatingPlanService.get_all_plans().count() == 1

        # Soft Delete
        MatingPlanService.delete_plan(plan)
        assert MatingPlanService.get_all_plans().count() == 0
        assert MatingPlanService.get_deleted_plans().count() == 1

        # Restore
        MatingPlanService.restore_plan(plan.pk)
        assert MatingPlanService.get_all_plans().count() == 1
        assert MatingPlanService.get_deleted_plans().count() == 0

        # Hard Delete
        MatingPlanService.hard_delete_plan(plan.pk)
        assert MatingPlan.all_objects.count() == 0

    def test_create_plan_exception(self):
        """Test simple exception in create_plan for coverage."""
        with pytest.raises(NotImplementedError):
            MatingPlanService.create_plan({})


@pytest.mark.django_db
class TestMatingPlanViews:
    def test_list_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        baker.make(MatingPlan, _quantity=3)

        url = reverse("reproduction:matingplan_list")
        response = client.get(url)

        assert response.status_code == 200
        assert len(response.context["plans"]) == 3

    def test_create_view_context_and_success(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse("reproduction:matingplan_add")

        # Test Get Context
        response_get = client.get(url)
        assert response_get.status_code == 200
        assert "title" in response_get.context
        assert response_get.context["title"] == "Create Mating Plan"

    def test_create_view_post(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        season = baker.make("reproduction.ReproductiveSeason")
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE)
        cow = baker.make(Cattle, sex=Cattle.SEX_FEMALE)

        url = reverse("reproduction:matingplan_add")
        data = {
            "season": season.pk,
            "sire": sire.pk,
            "cows": [cow.pk],
            "status": MatingPlan.Status.DRAFT,
            "notes": "Test Plan",
        }

        response = client.post(url, data)
        assert response.status_code == 302  # Redirects to list
        assert MatingPlan.objects.count() == 1

        plan = MatingPlan.objects.first()
        assert plan.sire == sire
        assert plan.cows.count() == 1
        assert plan.notes == "Test Plan"

    def test_update_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        # Create a valid plan with a Male Sire
        valid_sire = baker.make(Cattle, sex=Cattle.SEX_MALE)
        plan = baker.make(MatingPlan, sire=valid_sire, notes="Old Notes")

        # Ensure plan has a cow to start with (though m2m doesn't set via make easily unless related)
        # We need another cow to update WITH.
        cow_for_update = baker.make(Cattle, sex=Cattle.SEX_FEMALE)

        url = reverse("reproduction:matingplan_edit", kwargs={"pk": plan.pk})

        data = {
            "season": plan.season.pk,
            "sire": plan.sire.pk,
            "cows": [cow_for_update.pk],  # Required field
            "status": MatingPlan.Status.APPROVED_WAITING,
            "notes": "New Notes",
        }

        response = client.get(url)
        assert "title" in response.context
        assert response.context["title"] == "Edit Mating Plan"

        response = client.post(url, data)
        if response.status_code != 302:
            print(f"Form Errors: {response.context['form'].errors}")
        assert response.status_code == 302

        plan.refresh_from_db()
        assert plan.notes == "New Notes"
        assert plan.status == MatingPlan.Status.APPROVED_WAITING

    def test_delete_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        plan = baker.make(MatingPlan)
        url = reverse("reproduction:matingplan_delete", kwargs={"pk": plan.pk})

        response = client.post(url)
        assert response.status_code == 302

        assert MatingPlan.objects.count() == 0
        assert MatingPlan.all_objects.count() == 1  # Soft deleted

        assert MatingPlan.all_objects.count() == 1  # Soft deleted

    def test_delete_view_protected(self, client, django_user_model):
        """Test DeleteView checks for ProtectedError/ValidationError (lines 79-80)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        plan = baker.make(MatingPlan)
        url = reverse("reproduction:matingplan_delete", kwargs={"pk": plan.pk})

        # Mock service to raise ProtectedError
        with patch(
            "apps.reproduction.services.mating_service.MatingPlanService.delete_plan",
            side_effect=ValidationError("Cannot delete"),
        ):
            response = client.post(url)
            # Should handle error (usually re-renders or redirects with message, depends on mixin)
            # Mixin `HandleProtectedErrorMixin` usually re-renders confirm page with error.
            assert response.status_code == 200
            assert "Cannot delete" in response.content.decode()

    def test_restore_view_errors(self, client, django_user_model):
        """Test RestoreView error handling (lines 98-99, 104-111)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # 1. Test Restore Exception (Post)
        plan = baker.make(MatingPlan, is_deleted=True)
        url_restore = reverse("reproduction:matingplan_restore", kwargs={"pk": plan.pk})

        with patch(
            "apps.reproduction.services.mating_service.MatingPlanService.restore_plan",
            side_effect=Exception("Generic Error"),
        ):
            response = client.post(url_restore, follow=True)
            # Should redirect and show error message
            assert "Generic Error" in [m.message for m in response.context["messages"]]

        # 2. Test Get Not Found
        url_restore_404 = reverse(
            "reproduction:matingplan_restore",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url_restore_404, follow=True)
        assert "Mating Plan not found." in [
            m.message for m in response.context["messages"]
        ]

    def test_hard_delete_post_not_found(self, client, django_user_model):
        """Test HardDelete POST with non-existent ID."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url_hard = reverse(
            "reproduction:matingplan_permanent_delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url_hard, follow=True)
        assert "Mating Plan not found." in [
            m.message for m in response.context["messages"]
        ]

    def test_hard_delete_get_not_found(self, client, django_user_model):
        """Test HardDelete GET with non-existent ID."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url_hard = reverse(
            "reproduction:matingplan_permanent_delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url_hard, follow=True)
        assert "Mating Plan not found." in [
            m.message for m in response.context["messages"]
        ]

    def test_hard_delete_protected_error(self, client, django_user_model):
        """Test HardDelete handles ProtectedError gracefully."""
        user = baker.make(django_user_model)
        client.force_login(user)

        plan = baker.make(MatingPlan, is_deleted=True)
        url_hard = reverse(
            "reproduction:matingplan_permanent_delete", kwargs={"pk": plan.pk}
        )

        with patch(
            "apps.reproduction.services.mating_service.MatingPlanService.hard_delete_plan",
            side_effect=ValidationError("Protected"),
        ):
            response = client.post(url_hard)
            assert response.status_code == 200
            assert "Protected" in response.content.decode()

    def test_hard_delete_race_condition(self, client, django_user_model):
        """Test HardDelete race condition where object disappears during error handling."""
        user = baker.make(django_user_model)
        client.force_login(user)

        plan = baker.make(MatingPlan, is_deleted=True)
        url_hard = reverse(
            "reproduction:matingplan_permanent_delete", kwargs={"pk": plan.pk}
        )

        with patch(
            "apps.reproduction.services.mating_service.MatingPlanService.hard_delete_plan",
            side_effect=ValidationError("Protected"),
        ):
            # Simulate object deletion concurrently by mocking retrieval failure
            with patch(
                "apps.reproduction.models.MatingPlan.all_objects.get",
                side_effect=MatingPlan.DoesNotExist,
            ):
                response = client.post(url_hard, follow=True)
                # Should redirect to trash since object is gone
                assert response.status_code == 200

    def test_hard_delete_success(self, client, django_user_model):
        """Test successful Hard Delete flow."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # 1. Start with Soft Deleted Plan
        plan = baker.make(MatingPlan, is_deleted=True)

        # 2. Hard Delete
        url_hard = reverse(
            "reproduction:matingplan_permanent_delete", kwargs={"pk": plan.pk}
        )
        response = client.post(url_hard, follow=True)

        assert response.status_code == 200
        messages = [m.message for m in response.context["messages"]]
        assert "Mating Plan permanently deleted." in messages
        assert MatingPlan.all_objects.count() == 0

    def test_allocation_wizard(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        # Setup: Plan in APPROVED_WAITING
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE, tag="SIRE001")
        cows = baker.make(Cattle, sex=Cattle.SEX_FEMALE, _quantity=2)
        pasture = baker.make(
            Location,
            type=LocationType.PASTURE,
            area_hectares=10,
            is_active=True,
            name="Paddock 1",
        )

        plan = baker.make(
            MatingPlan, sire=sire, status=MatingPlan.Status.APPROVED_WAITING
        )
        plan.cows.set(cows)

        # Ensure animals are NOT in pasture yet
        assert sire.location != pasture
        for cow in cows:
            assert cow.location != pasture

        url = reverse("reproduction:matingplan_activate", kwargs={"pk": plan.pk})

        # 1. GET Request (Wizard)
        response = client.get(url)
        assert response.status_code == 200
        assert "paddock_options" in response.context

        # 2. POST (Execute Move)
        response = client.post(url, {"paddock_id": pasture.pk})
        assert response.status_code == 302  # Redirect to List

        plan.refresh_from_db()
        assert plan.status == MatingPlan.Status.ACTIVE

        # Check Sire Move
        sire.refresh_from_db()
        assert sire.location == pasture

        # Check Cows Move
        for cow in plan.cows.all():
            cow.refresh_from_db()
        for cow in plan.cows.all():
            cow.refresh_from_db()
            assert cow.location == pasture

    def test_allocation_wizard_visual_indicators(self, client, django_user_model):
        """Test visual indicators (valid, warning, error) in Allocation Wizard (lines 46-53)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Setup plan and pastures
        plan = baker.make(MatingPlan, status=MatingPlan.Status.APPROVED_WAITING)
        paddock_ok = baker.make(
            Location, type=LocationType.PASTURE, is_active=True, name="OK Paddock"
        )
        paddock_warn = baker.make(
            Location, type=LocationType.PASTURE, is_active=True, name="Warn Paddock"
        )
        paddock_err = baker.make(
            Location, type=LocationType.PASTURE, is_active=True, name="Err Paddock"
        )

        url = reverse("reproduction:matingplan_activate", kwargs={"pk": plan.pk})

        # Mock AllocationService.validate_move to return different results per paddock
        def side_effect_validate(paddock, _animals):
            if paddock == paddock_ok:
                return {"valid": True, "errors": [], "warnings": []}
            if paddock == paddock_warn:
                return {"valid": True, "errors": [], "warnings": ["Capacity Warning"]}
            if paddock == paddock_err:
                return {"valid": False, "errors": ["Too Small"], "warnings": []}
            return {"valid": True, "errors": [], "warnings": []}

        with patch(
            "apps.locations.services.allocation.AllocationService.validate_move",
            side_effect=side_effect_validate,
        ):
            response = client.get(url)
            assert response.status_code == 200
            options = response.context["paddock_options"]

            # Verify OK Paddock
            opt_ok = next(o for o in options if o["location"] == paddock_ok)
            assert opt_ok["status"] == "valid"
            assert "🟢" in opt_ok["icon"]

            # Verify Warning Paddock
            opt_warn = next(o for o in options if o["location"] == paddock_warn)
            assert opt_warn["status"] == "warning"
            assert "🟡" in opt_warn["icon"]

            # Verify Error Paddock
            opt_err = next(o for o in options if o["location"] == paddock_err)
            assert opt_err["status"] == "error"
            assert "🔴" in opt_err["icon"]

    def test_allocation_post_cases(self, client, django_user_model):
        """Test POST edge cases: Decide Later, Invalid Paddock (lines 74-80, 111-113)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        plan = baker.make(MatingPlan, status=MatingPlan.Status.APPROVED_WAITING)
        url = reverse("reproduction:matingplan_activate", kwargs={"pk": plan.pk})

        # 1. Decide Later (No paddock_id)
        response = client.post(url, {})  # Empty POST
        assert response.status_code == 302
        # Should redirect to List
        assert response.url == reverse("reproduction:matingplan_list")
        # Plan remains waiting
        plan.refresh_from_db()
        assert plan.status == MatingPlan.Status.APPROVED_WAITING

        # 2. Invalid Paddock ID
        response = client.post(
            url, {"paddock_id": "00000000-0000-0000-0000-000000000000"}
        )
        assert response.status_code == 302
        assert response.url == reverse("reproduction:matingplan_list")
        # Check message
        if response.context:
            list(
                response.context["messages"]
            )  # Consume iterator if present without assigning
        # Since it's a redirect, we might need to follow to see messages or rely on session
        response_follow = client.post(
            url, {"paddock_id": "00000000-0000-0000-0000-000000000000"}, follow=True
        )
        assert "Invalid Paddock selected." in [
            m.message for m in response_follow.context["messages"]
        ]

    def test_delete_view_http_delete(self, client, django_user_model):
        """Test HTTP DELETE method on DeleteView (line 73 coverage)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        plan = baker.make(MatingPlan)
        url = reverse("reproduction:matingplan_delete", kwargs={"pk": plan.pk})

        response = client.delete(url)
        assert response.status_code == 302
        assert MatingPlan.objects.count() == 0

    def test_restore_view_success(self, client, django_user_model):
        """Test happy path for RestoreView POST (line 97 coverage)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        plan = baker.make(MatingPlan, is_deleted=True)
        url = reverse("reproduction:matingplan_restore", kwargs={"pk": plan.pk})

        response = client.post(url, follow=True)
        assert response.status_code == 200
        assert "Mating Plan restored successfully." in [
            m.message for m in response.context["messages"]
        ]
        plan.refresh_from_db()
        assert not plan.is_deleted

    def test_restore_view_get_success(self, client, django_user_model):
        """Test happy path for RestoreView GET (line 106 coverage)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        plan = baker.make(MatingPlan, is_deleted=True)
        url = reverse("reproduction:matingplan_restore", kwargs={"pk": plan.pk})

        response = client.get(url)
        assert response.status_code == 200
        assert "plan" in response.context
        assert response.context["plan"] == plan
        assert "reproduction/matingplan_confirm_restore.html" in [
            t.name for t in response.templates
        ]

    def test_hard_delete_view_get_success(self, client, django_user_model):
        """Test happy path for HardDeleteView GET (line 139 coverage)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        plan = baker.make(MatingPlan, is_deleted=True)
        url = reverse(
            "reproduction:matingplan_permanent_delete", kwargs={"pk": plan.pk}
        )

        response = client.get(url)
        assert response.status_code == 200
        assert "plan" in response.context
        assert response.context["plan"] == plan
        assert "reproduction/matingplan_confirm_permanent_delete.html" in [
            t.name for t in response.templates
        ]
