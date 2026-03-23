from __future__ import annotations

from uuid import uuid4

import pytest

from .conftest import TIMEOUT
from .helpers import extract_list, extract_object, get_field


class TestProfile:
    def test_get_profile_returns_user_object(self, session, api_url, user_headers, server_ready):
        response = session.get(api_url("/profile"), headers=user_headers, timeout=TIMEOUT)
        assert response.status_code == 200
        payload = extract_object(response.json(), "profile", "user", "data")
        assert isinstance(payload, dict)

    def test_profile_rejects_short_name(self, session, api_url, user_headers, server_ready):
        response = session.put(
            api_url("/profile"),
            json={"name": "A", "phone": "9876543210"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400

    def test_profile_rejects_invalid_phone_length(self, session, api_url, user_headers, server_ready):
        response = session.put(
            api_url("/profile"),
            json={"name": "Valid Name", "phone": "12345"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400

    def test_profile_rejects_alphabetic_phone(self, session, api_url, user_headers, server_ready):
        response = session.put(
            api_url("/profile"),
            json={"name": "Valid Name", "phone": "abcdefghij"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400

    def test_profile_rejects_non_digit_phone(self, session, api_url, user_headers, server_ready):
        response = session.put(
            api_url("/profile"),
            json={"name": "Valid Name", "phone": "12345abcde"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400


class TestAddresses:
    def test_pincode_validation_accepts_500001_and_rejects_12345(self, session, api_url, user_headers, server_ready):
        suffix = uuid4().hex[:8]
        valid_payload = {
            "label": "HOME",
            "street": f"{suffix} Valid Street",
            "city": "Hyderabad",
            "pincode": "500001",
            "is_default": False,
        }
        invalid_payload = {
            "label": "HOME",
            "street": f"{suffix} Invalid Street",
            "city": "Hyderabad",
            "pincode": "12345",
            "is_default": False,
        }

        valid_response = session.post(api_url("/addresses"), json=valid_payload, headers=user_headers, timeout=TIMEOUT)
        invalid_response = session.post(api_url("/addresses"), json=invalid_payload, headers=user_headers, timeout=TIMEOUT)

        assert valid_response.status_code in (200, 201)
        assert invalid_response.status_code == 400

        if valid_response.status_code in (200, 201):
            created = extract_object(valid_response.json(), "address", "data")
            address_id = get_field(created, "address_id", "id")
            if address_id is not None:
                session.delete(api_url(f"/addresses/{address_id}"), headers=user_headers, timeout=TIMEOUT)

    def test_create_address_rejects_missing_required_field(self, session, api_url, user_headers, server_ready):
        response = session.post(
            api_url("/addresses"),
            json={"label": "HOME", "city": "Hyderabad", "pincode": "500001"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400

    def test_create_address_rejects_invalid_label(self, session, api_url, user_headers, server_ready):
        response = session.post(
            api_url("/addresses"),
            json={
                "label": "HOSTEL",
                "street": "Lane 1",
                "city": "Hyderabad",
                "pincode": "500001",
                "is_default": False,
            },
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400

    def test_create_address_rejects_short_street(self, session, api_url, user_headers, server_ready):
        response = session.post(
            api_url("/addresses"),
            json={
                "label": "HOME",
                "street": "1234",
                "city": "Hyderabad",
                "pincode": "500001",
                "is_default": False,
            },
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400

    def test_create_address_rejects_invalid_pincode_type(self, session, api_url, user_headers, server_ready):
        response = session.post(
            api_url("/addresses"),
            json={
                "label": "HOME",
                "street": "Street Name 12",
                "city": "Hyderabad",
                "pincode": 500001,
                "is_default": False,
            },
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400

    def test_create_address_success_response_contains_address_object(self, session, api_url, user_headers, server_ready):
        suffix = uuid4().hex[:8]
        payload = {
            "label": "HOME",
            "street": f"{suffix} Residency Road",
            "city": "Hyderabad",
            "pincode": "500001",
            "is_default": False,
        }
        response = session.post(api_url("/addresses"), json=payload, headers=user_headers, timeout=TIMEOUT)
        assert response.status_code in (200, 201)

        address = extract_object(response.json(), "address", "data")
        address_id = get_field(address, "address_id", "id")
        assert address_id is not None
        assert str(get_field(address, "pincode")) == payload["pincode"]

        cleanup = session.delete(api_url(f"/addresses/{address_id}"), headers=user_headers, timeout=TIMEOUT)
        assert cleanup.status_code in (200, 204)

    @pytest.mark.xfail(
        reason="Bug: address update response returns stale street and does not reflect updates",
        strict=False,
    )
    def test_update_address_allows_only_street_and_default(
        self, session, api_url, user_headers, created_address, server_ready
    ):
        address_id = get_field(created_address, "address_id", "id")
        original_label = get_field(created_address, "label")
        original_city = get_field(created_address, "city")
        original_pincode = get_field(created_address, "pincode")

        update_response = session.put(
            api_url(f"/addresses/{address_id}"),
            json={
                "street": "Updated Street 123",
                "is_default": True,
                "label": "OFFICE",
                "city": "Mumbai",
                "pincode": "400001",
            },
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert update_response.status_code == 200

        updated = extract_object(update_response.json(), "address", "data")
        assert get_field(updated, "street") == "Updated Street 123"
        assert get_field(updated, "is_default") is True
        assert get_field(updated, "label") == original_label
        assert get_field(updated, "city") == original_city
        assert str(get_field(updated, "pincode")) == str(original_pincode)

    def test_delete_missing_address_returns_404(self, session, api_url, user_headers, server_ready):
        response = session.delete(api_url("/addresses/999999999"), headers=user_headers, timeout=TIMEOUT)
        assert response.status_code == 404

    def test_only_one_default_address(self, session, api_url, user_headers, server_ready):
        suffix = uuid4().hex[:8]
        payload_1 = {
            "label": "HOME",
            "street": f"{suffix} A Street",
            "city": "Hyderabad",
            "pincode": "500001",
            "is_default": True,
        }
        payload_2 = {
            "label": "OFFICE",
            "street": f"{suffix} B Street",
            "city": "Hyderabad",
            "pincode": "500002",
            "is_default": True,
        }

        create_1 = session.post(api_url("/addresses"), json=payload_1, headers=user_headers, timeout=TIMEOUT)
        create_2 = session.post(api_url("/addresses"), json=payload_2, headers=user_headers, timeout=TIMEOUT)
        assert create_1.status_code in (200, 201)
        assert create_2.status_code in (200, 201)

        addr_1 = extract_object(create_1.json(), "address", "data")
        addr_2 = extract_object(create_2.json(), "address", "data")
        id_1 = get_field(addr_1, "address_id", "id")
        id_2 = get_field(addr_2, "address_id", "id")

        list_response = session.get(api_url("/addresses"), headers=user_headers, timeout=TIMEOUT)
        assert list_response.status_code == 200
        all_addresses = extract_list(list_response.json(), "addresses", "data", "items")
        defaults = [a for a in all_addresses if get_field(a, "is_default") is True]
        assert len(defaults) == 1

        session.delete(api_url(f"/addresses/{id_1}"), headers=user_headers, timeout=TIMEOUT)
        session.delete(api_url(f"/addresses/{id_2}"), headers=user_headers, timeout=TIMEOUT)
