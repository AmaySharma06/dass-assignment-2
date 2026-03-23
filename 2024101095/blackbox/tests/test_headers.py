from __future__ import annotations

from .conftest import TIMEOUT


def test_missing_roll_header_is_rejected(session, api_url, server_ready):
    response = session.get(api_url("/admin/users"), timeout=TIMEOUT)
    assert response.status_code == 401


def test_invalid_roll_header_is_rejected(session, api_url, server_ready):
    response = session.get(
        api_url("/admin/users"),
        headers={"X-Roll-Number": "abc"},
        timeout=TIMEOUT,
    )
    assert response.status_code == 400


def test_user_endpoint_requires_user_id(session, api_url, admin_headers, server_ready):
    response = session.get(api_url("/profile"), headers=admin_headers, timeout=TIMEOUT)
    assert response.status_code == 400


def test_invalid_user_id_is_rejected(session, api_url, admin_headers, server_ready):
    headers = dict(admin_headers)
    headers["X-User-ID"] = "not-an-int"
    response = session.get(api_url("/profile"), headers=headers, timeout=TIMEOUT)
    assert response.status_code == 400
