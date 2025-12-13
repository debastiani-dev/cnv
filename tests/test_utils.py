from unittest.mock import patch

from django.contrib.messages import get_messages
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.reproduction.models import BreedingEvent


def verify_redirect_with_message(
    client, url, expected_message_part, method="get", data=None
):
    """
    Verifies that a request redirects (302) and a specific message is present.
    Commonly used for 'Not Found' checks or success messages.
    """
    if method == "post":
        response = client.post(url, data=data)
    else:
        response = client.get(url, data=data)

    assert response.status_code == 302
    messages = list(get_messages(response.wsgi_request))
    assert any(expected_message_part.lower() in str(m).lower() for m in messages)
    return response


def verify_protected_error_response(
    client, url, error_text="cannot delete", method="post", data=None
):
    """
    Verifies that a view handles ProtectedError correctly by rendering the page
    with an error message (usually 200 OK + error in content/messages).
    """
    if method == "get":
        response = client.get(url, data=data)
    else:
        response = client.post(url, data=data)

    assert response.status_code == 200
    assert error_text.lower() in response.content.decode().lower()
    return response


def verify_service_error_handling(
    response, mock_service, error_message="Service Error"
):
    """
    Verifies that a service failure is handled correctly by the view:
    - Service mock was called.
    - Response is 200 (re-render).
    - Form has non-field errors containing the expected error message.
    """
    assert mock_service.called, "Service should have been called"
    assert response.status_code == 200
    assert "form" in response.context

    form = response.context["form"]
    errors = form.non_field_errors()
    assert errors, "Form should have non-field errors"
    assert any(error_message in str(err) for err in errors)


def verify_post_with_mocked_exception(
    client, url, data, service_method_path, exception_to_raise
):
    """
    Mocks a service method to raise the provided exception,
    performs a POST request, and verifies the view handles it (200 + form error).
    """
    with patch(service_method_path, side_effect=exception_to_raise) as mock_service:
        response = client.post(url, data)
        verify_service_error_handling(response, mock_service, str(exception_to_raise))


def create_pregnant_dam():
    """Creates a pregnant cow with an associated breeding event."""
    dam = baker.make(
        Cattle, sex=Cattle.SEX_FEMALE, reproduction_status=Cattle.REP_STATUS_PREGNANT
    )
    breeding = baker.make(BreedingEvent, dam=dam)
    return dam, breeding


def get_invalid_transaction_data():
    """Returns invalid form data common to purchase/sale views."""
    return {
        "date": "",  # Invalid
        "partner": "",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "0",
    }


def get_valid_sales_form_data(partner, notes="Test Note"):
    """Returns valid base form data for sales views."""
    return {
        "partner": partner.pk,
        "notes": notes,
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
    }
