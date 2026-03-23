from __future__ import annotations

import os
from uuid import uuid4

import pytest
import requests

from .helpers import extract_list, extract_object, get_field


BASE_URL = os.getenv("QUICKCART_BASE_URL", "http://localhost:8080").rstrip("/")
API_BASE = f"{BASE_URL}/api/v1"
ROLL_NUMBER = os.getenv("QUICKCART_ROLL_NUMBER", "2024101095")
TIMEOUT = int(os.getenv("QUICKCART_TIMEOUT", "10"))


def _stock_value(product: dict) -> int | None:
    raw = get_field(product, "stock", "stock_quantity", "quantity", "inventory", default=None)
    if raw is None:
        return None
    try:
        return int(float(str(raw)))
    except (TypeError, ValueError):
        return None


@pytest.fixture(scope="session")
def api_url():
    def _api_url(path: str) -> str:
        return f"{API_BASE}{path}"

    return _api_url


@pytest.fixture(scope="session")
def session() -> requests.Session:
    return requests.Session()


@pytest.fixture(scope="session")
def admin_headers() -> dict[str, str]:
    return {"X-Roll-Number": ROLL_NUMBER}


@pytest.fixture(scope="session")
def server_ready(session: requests.Session, api_url, admin_headers: dict[str, str]) -> bool:
    try:
        response = session.get(api_url("/admin/users"), headers=admin_headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        pytest.skip(f"QuickCart server is not reachable at {BASE_URL}: {exc}")

    if response.status_code != 200:
        pytest.skip(
            "QuickCart server did not accept configured headers: "
            f"status={response.status_code}, body={response.text[:200]}"
        )
    return True


@pytest.fixture(scope="session")
def existing_users(session: requests.Session, api_url, admin_headers, server_ready):
    response = session.get(api_url("/admin/users"), headers=admin_headers, timeout=TIMEOUT)
    assert response.status_code == 200
    users = extract_list(response.json(), "users", "data", "items")
    assert users, "admin/users returned no users; tests require seeded users"
    return users


@pytest.fixture(scope="session")
def user_id(existing_users) -> int:
    for user in existing_users:
        candidate = get_field(user, "user_id", "id")
        if isinstance(candidate, int) and candidate > 0:
            return candidate
    pytest.skip("No valid user_id found in admin/users response")


@pytest.fixture
def user_headers(admin_headers, user_id: int) -> dict[str, str]:
    headers = dict(admin_headers)
    headers["X-User-ID"] = str(user_id)
    return headers


@pytest.fixture
def active_product(session: requests.Session, api_url, admin_headers, server_ready):
    response = session.get(api_url("/admin/products"), headers=admin_headers, timeout=TIMEOUT)
    assert response.status_code == 200

    products = extract_list(response.json(), "products", "data", "items")
    for product in products:
        product_id = get_field(product, "product_id", "id")
        is_active = get_field(product, "is_active", "active", default=True)
        stock = _stock_value(product)
        if product_id and is_active and stock is not None and stock > 0:
            return {
                "product_id": product_id,
                "price": float(get_field(product, "price", default=0.0)),
            }

    pytest.skip("No active in-stock product found in admin/products")


@pytest.fixture
def active_products(session: requests.Session, api_url, admin_headers, server_ready):
    response = session.get(api_url("/admin/products"), headers=admin_headers, timeout=TIMEOUT)
    assert response.status_code == 200

    products = extract_list(response.json(), "products", "data", "items")
    out = []
    for product in products:
        product_id = get_field(product, "product_id", "id")
        is_active = get_field(product, "is_active", "active", default=True)
        stock = _stock_value(product)
        if product_id and is_active and stock is not None and stock > 0:
            out.append(
                {
                    "product_id": product_id,
                    "price": float(get_field(product, "price", default=0.0)),
                }
            )
            if len(out) == 2:
                break

    if len(out) < 2:
        pytest.skip("Need at least two active in-stock products for multi-item cart tests")
    return out


@pytest.fixture
def inactive_product_id(session: requests.Session, api_url, admin_headers, server_ready):
    response = session.get(api_url("/admin/products"), headers=admin_headers, timeout=TIMEOUT)
    assert response.status_code == 200

    products = extract_list(response.json(), "products", "data", "items")
    for product in products:
        product_id = get_field(product, "product_id", "id")
        is_active = get_field(product, "is_active", "active", default=True)
        if product_id and is_active is False:
            return product_id

    pytest.skip("No inactive product available in seeded data")


@pytest.fixture
def clear_cart(session: requests.Session, api_url, user_headers, server_ready):
    session.delete(api_url("/cart/clear"), headers=user_headers, timeout=TIMEOUT)
    yield
    session.delete(api_url("/cart/clear"), headers=user_headers, timeout=TIMEOUT)


@pytest.fixture
def created_address(session: requests.Session, api_url, user_headers, server_ready):
    suffix = uuid4().hex[:8]
    payload = {
        "label": "HOME",
        "street": f"{suffix} Test Street",
        "city": "Hyderabad",
        "pincode": "500001",
        "is_default": False,
    }
    response = session.post(api_url("/addresses"), json=payload, headers=user_headers, timeout=TIMEOUT)
    assert response.status_code in (200, 201)

    address = extract_object(response.json(), "address", "data")
    address_id = get_field(address, "address_id", "id")
    assert address_id is not None

    yield address

    session.delete(api_url(f"/addresses/{address_id}"), headers=user_headers, timeout=TIMEOUT)
