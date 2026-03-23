from __future__ import annotations

from decimal import Decimal

import pytest

from .conftest import TIMEOUT
from .helpers import extract_cart_item, extract_list, extract_object, get_field


class TestProducts:
    def test_public_product_price_matches_admin_price(self, session, api_url, admin_headers, user_headers, active_product, server_ready):
        product_id = active_product["product_id"]

        admin_response = session.get(api_url("/admin/products"), headers=admin_headers, timeout=TIMEOUT)
        assert admin_response.status_code == 200
        admin_products = extract_list(admin_response.json(), "products", "data", "items")
        admin_item = next((p for p in admin_products if get_field(p, "product_id", "id") == product_id), None)
        assert admin_item is not None

        public_response = session.get(api_url(f"/products/{product_id}"), headers=user_headers, timeout=TIMEOUT)
        assert public_response.status_code == 200
        public_item = extract_object(public_response.json(), "product", "data")

        admin_price = Decimal(str(get_field(admin_item, "price", default=0)))
        public_price = Decimal(str(get_field(public_item, "price", default=0)))
        assert public_price == admin_price

    def test_products_list_excludes_inactive(self, session, api_url, admin_headers, user_headers, server_ready):
        admin_response = session.get(api_url("/admin/products"), headers=admin_headers, timeout=TIMEOUT)
        public_response = session.get(api_url("/products"), headers=user_headers, timeout=TIMEOUT)

        assert admin_response.status_code == 200
        assert public_response.status_code == 200

        admin_products = extract_list(admin_response.json(), "products", "data", "items")
        public_products = extract_list(public_response.json(), "products", "data", "items")

        inactive_ids = {
            get_field(product, "product_id", "id")
            for product in admin_products
            if get_field(product, "is_active", "active", default=True) is False
        }
        public_ids = {get_field(product, "product_id", "id") for product in public_products}

        assert inactive_ids.isdisjoint(public_ids)

    def test_missing_product_returns_404(self, session, api_url, user_headers, server_ready):
        response = session.get(api_url("/products/999999999"), headers=user_headers, timeout=TIMEOUT)
        assert response.status_code == 404

    def test_inactive_product_not_reachable_in_public_listing(
        self, session, api_url, user_headers, inactive_product_id, server_ready
    ):
        response = session.get(api_url("/products"), headers=user_headers, timeout=TIMEOUT)
        assert response.status_code == 200
        products = extract_list(response.json(), "products", "data", "items")
        ids = {get_field(product, "product_id", "id") for product in products}
        assert inactive_product_id not in ids

    def test_products_filter_search_and_sort_accept_valid_inputs(self, session, api_url, user_headers, server_ready):
        response = session.get(
            api_url("/products?category=electronics&search=a&sort=asc"),
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 200


class TestCart:
    def test_cart_subtotal_must_equal_unit_price_times_quantity(self, session, api_url, user_headers, active_product, clear_cart, server_ready):
        product_id = active_product["product_id"]
        unit_price = Decimal(str(active_product["price"]))

        add_response = session.post(
            api_url("/cart/add"),
            json={"product_id": product_id, "quantity": 3},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_response.status_code in (200, 201)

        cart_response = session.get(api_url("/cart"), headers=user_headers, timeout=TIMEOUT)
        assert cart_response.status_code == 200

        cart_payload = cart_response.json()
        item = extract_cart_item(cart_payload, product_id)
        assert item is not None

        subtotal = Decimal(str(get_field(item, "subtotal")))
        expected_subtotal = unit_price * Decimal("3")
        assert subtotal == expected_subtotal

    def test_cart_total_must_equal_sum_of_item_subtotals(self, session, api_url, user_headers, active_products, clear_cart, server_ready):
        first, second = active_products

        add_first = session.post(
            api_url("/cart/add"),
            json={"product_id": first["product_id"], "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        add_second = session.post(
            api_url("/cart/add"),
            json={"product_id": second["product_id"], "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_first.status_code in (200, 201)
        assert add_second.status_code in (200, 201)

        cart_response = session.get(api_url("/cart"), headers=user_headers, timeout=TIMEOUT)
        assert cart_response.status_code == 200
        payload = cart_response.json()

        items = extract_list(payload, "items", "cart_items")
        computed_total = sum(Decimal(str(get_field(item, "subtotal", default=0))) for item in items)
        observed_total = Decimal(str(get_field(payload, "total", "cart_total", default=0)))
        assert observed_total == computed_total

    def test_cart_total_must_equal_sum_of_expected_unit_prices(self, session, api_url, user_headers, active_products, clear_cart, server_ready):
        first, second = active_products

        add_first = session.post(
            api_url("/cart/add"),
            json={"product_id": first["product_id"], "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        add_second = session.post(
            api_url("/cart/add"),
            json={"product_id": second["product_id"], "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_first.status_code in (200, 201)
        assert add_second.status_code in (200, 201)

        cart_response = session.get(api_url("/cart"), headers=user_headers, timeout=TIMEOUT)
        assert cart_response.status_code == 200
        payload = cart_response.json()

        expected_total = Decimal(str(first["price"])) + Decimal(str(second["price"]))
        observed_total = Decimal(str(get_field(payload, "total", "cart_total", default=0)))
        assert observed_total == expected_total

    def test_cart_add_update_remove_and_clear(self, session, api_url, user_headers, active_product, clear_cart, server_ready):
        product_id = active_product["product_id"]

        add_once = session.post(
            api_url("/cart/add"),
            json={"product_id": product_id, "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_once.status_code in (200, 201)

        add_again = session.post(
            api_url("/cart/add"),
            json={"product_id": product_id, "quantity": 2},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_again.status_code in (200, 201)

        cart_response = session.get(api_url("/cart"), headers=user_headers, timeout=TIMEOUT)
        assert cart_response.status_code == 200

        cart_payload = cart_response.json()
        item = extract_cart_item(cart_payload, product_id)
        assert item is not None
        assert get_field(item, "quantity") == 3

        update_response = session.post(
            api_url("/cart/update"),
            json={"product_id": product_id, "quantity": 2},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert update_response.status_code == 200

        remove_response = session.post(
            api_url("/cart/remove"),
            json={"product_id": product_id},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert remove_response.status_code == 200

        clear_response = session.delete(api_url("/cart/clear"), headers=user_headers, timeout=TIMEOUT)
        assert clear_response.status_code in (200, 204)

    def test_cart_total_includes_multiple_items(self, session, api_url, user_headers, active_products, clear_cart, server_ready):
        first, second = active_products

        add_first = session.post(
            api_url("/cart/add"),
            json={"product_id": first["product_id"], "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        add_second = session.post(
            api_url("/cart/add"),
            json={"product_id": second["product_id"], "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_first.status_code in (200, 201)
        assert add_second.status_code in (200, 201)

        cart_response = session.get(api_url("/cart"), headers=user_headers, timeout=TIMEOUT)
        assert cart_response.status_code == 200
        payload = cart_response.json()
        assert get_field(payload, "total", "cart_total") is not None

    def test_cart_rejects_invalid_quantity_and_missing_product(self, session, api_url, user_headers, clear_cart, server_ready):
        invalid_zero = session.post(
            api_url("/cart/add"),
            json={"product_id": 1, "quantity": 0},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert invalid_zero.status_code == 400

        invalid_negative = session.post(
            api_url("/cart/add"),
            json={"product_id": 1, "quantity": -1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert invalid_negative.status_code == 400

        missing_product = session.post(
            api_url("/cart/add"),
            json={"product_id": 999999999, "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert missing_product.status_code == 404

    def test_cart_rejects_quantity_above_available_stock(self, session, api_url, admin_headers, user_headers, active_product, clear_cart, server_ready):
        product_id = active_product["product_id"]

        admin_response = session.get(api_url("/admin/products"), headers=admin_headers, timeout=TIMEOUT)
        assert admin_response.status_code == 200
        products = extract_list(admin_response.json(), "products", "data", "items")
        product = next((p for p in products if get_field(p, "product_id", "id") == product_id), None)
        assert product is not None

        raw_stock = get_field(product, "stock", "stock_quantity", "quantity", "inventory", default=None)
        if raw_stock is None:
            pytest.skip("Stock quantity field missing for active product")

        stock = int(float(str(raw_stock)))
        response = session.post(
            api_url("/cart/add"),
            json={"product_id": product_id, "quantity": stock + 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400

    def test_cart_update_rejects_quantity_below_one(self, session, api_url, user_headers, active_product, clear_cart, server_ready):
        product_id = active_product["product_id"]

        add_response = session.post(
            api_url("/cart/add"),
            json={"product_id": product_id, "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_response.status_code in (200, 201)

        update_zero = session.post(
            api_url("/cart/update"),
            json={"product_id": product_id, "quantity": 0},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert update_zero.status_code == 400

        update_negative = session.post(
            api_url("/cart/update"),
            json={"product_id": product_id, "quantity": -1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert update_negative.status_code == 400

    @pytest.mark.xfail(
        reason="Bug: cart/add accepts missing or wrong-typed quantity in current server build",
        strict=False,
    )
    def test_cart_rejects_missing_fields_and_wrong_types(self, session, api_url, user_headers, clear_cart, server_ready):
        missing_quantity = session.post(
            api_url("/cart/add"),
            json={"product_id": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert missing_quantity.status_code == 400

        wrong_type_quantity = session.post(
            api_url("/cart/add"),
            json={"product_id": 1, "quantity": "two"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert wrong_type_quantity.status_code == 400

    def test_cart_remove_missing_item_returns_404(self, session, api_url, user_headers, clear_cart, server_ready):
        response = session.post(
            api_url("/cart/remove"),
            json={"product_id": 999999999},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 404
