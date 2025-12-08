from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle


class ItemLookupViewTestMixin:
    """
    Mixin to test the ItemLookupView.
    Requires 'client' and 'django_user_model' fixtures, usually provided by pytest-django class-based tests if configured,
    or we can pass them in.
    However, pytest style often uses functions or fixtures.
    For class-based tests in pytest, we can use the 'client' fixture via method argument if signature matches.
    """

    lookup_url_name: str | None = None  # Override this

    def test_item_lookup_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        cow1 = baker.make(Cattle, name="Bessie")
        cow2 = baker.make(
            Cattle, name="Daisy", is_deleted=True
        )  # Should be filtered out

        ct = ContentType.objects.get_for_model(Cattle)

        url = reverse(self.lookup_url_name)
        response = client.get(f"{url}?content_type_id={ct.pk}")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        ids = [item["id"] for item in data["results"]]
        assert str(cow1.pk) in ids
        assert str(cow2.pk) not in ids

    def test_item_lookup_view_invalid_ct(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        # User model is not whitelisted
        ct = ContentType.objects.get_for_model(django_user_model)

        url = reverse(self.lookup_url_name)
        response = client.get(f"{url}?content_type_id={ct.pk}")

        assert response.status_code == 403
