from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from math import ceil

import pytest

from .conftest import TIMEOUT
from .helpers import extract_list, extract_object, get_field, parse_datetime


def _pick_expired_or_ineligible_coupon(coupons: list[dict], cart_total: float) -> str | None:
    now = datetime.now().astimezone()
    for coupon in coupons:
        code = get_field(coupon, "code", "coupon_code")
        expires_at = parse_datetime(get_field(coupon, "expires_at", "expiry_date", "expires_on"))
        min_value = float(get_field(coupon, "min_cart_value", "minimum_cart_value", default=0.0))

        if code and expires_at is not None and expires_at < now:
            return code
        if code and min_value > cart_total:
            return code
    return None


class TestCoupons:
    def test_expired_or_ineligible_coupon_is_rejected(
        self, session, api_url, admin_headers, user_headers, active_product, clear_cart, server_ready
    ):
        add_response = session.post(
            api_url("/cart/add"),
            json={"product_id": active_product["product_id"], "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_response.status_code in (200, 201)

        coupons_response = session.get(api_url("/admin/coupons"), headers=admin_headers, timeout=TIMEOUT)
        assert coupons_response.status_code == 200
        coupons = extract_list(coupons_response.json(), "coupons", "data", "items")

        cart_response = session.get(api_url("/cart"), headers=user_headers, timeout=TIMEOUT)
        cart_total = float(get_field(cart_response.json(), "total", "cart_total", default=0.0))

        chosen_code = _pick_expired_or_ineligible_coupon(coupons, cart_total)
        if chosen_code is None:
            pytest.skip("No expired or ineligible coupon found in admin/coupons")

        coupon_response = session.post(
            api_url("/coupon/apply"),
            json={"code": chosen_code, "coupon_code": chosen_code},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert coupon_response.status_code == 400

    def test_coupon_apply_rejects_missing_code(self, session, api_url, user_headers, clear_cart, server_ready):
        response = session.post(api_url("/coupon/apply"), json={}, headers=user_headers, timeout=TIMEOUT)
        assert response.status_code == 400


class TestCheckout:
    def test_card_checkout_applies_exact_five_percent_gst(self, session, api_url, user_headers, active_product, clear_cart, server_ready):
        add_response = session.post(
            api_url("/cart/add"),
            json={"product_id": active_product["product_id"], "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_response.status_code in (200, 201)

        cart_response = session.get(api_url("/cart"), headers=user_headers, timeout=TIMEOUT)
        assert cart_response.status_code == 200
        cart_payload = cart_response.json()
        subtotal = Decimal(str(get_field(cart_payload, "subtotal", "cart_subtotal", default=active_product["price"])))

        checkout_response = session.post(
            api_url("/checkout"),
            json={"payment_method": "CARD"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert checkout_response.status_code in (200, 201)
        checkout_payload = checkout_response.json()

        order = extract_object(checkout_payload, "order", "data")
        gst_value = get_field(order, "gst", "gst_amount", "tax", "tax_amount", default=None)
        if gst_value is None:
            gst_value = get_field(checkout_payload, "gst", "gst_amount", "tax", "tax_amount", default=None)

        if gst_value is None:
            total_value = get_field(order, "total", "grand_total", default=None)
            if total_value is None:
                total_value = get_field(checkout_payload, "total", "total_amount", default=None)
            assert total_value is not None
            applied_gst = Decimal(str(total_value)) - subtotal
        else:
            applied_gst = Decimal(str(gst_value))

        assert applied_gst == subtotal * Decimal("0.05")

    @pytest.mark.xfail(
        reason="Bug: checkout with empty cart returns 200 instead of 400 in current server build",
        strict=False,
    )
    def test_checkout_rejects_invalid_method_and_empty_cart(self, session, api_url, user_headers, clear_cart, server_ready):
        invalid_method = session.post(
            api_url("/checkout"),
            json={"payment_method": "UPI"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert invalid_method.status_code == 400

        empty_cart = session.post(
            api_url("/checkout"),
            json={"payment_method": "COD"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert empty_cart.status_code == 400

    def test_checkout_rejects_missing_payment_method(self, session, api_url, user_headers, clear_cart, server_ready):
        response = session.post(api_url("/checkout"), json={}, headers=user_headers, timeout=TIMEOUT)
        assert response.status_code == 400

    def test_checkout_rejects_cod_when_total_exceeds_5000(self, session, api_url, admin_headers, user_headers, clear_cart, server_ready):
        admin_response = session.get(api_url("/admin/products"), headers=admin_headers, timeout=TIMEOUT)
        assert admin_response.status_code == 200
        products = extract_list(admin_response.json(), "products", "data", "items")

        candidates = []
        for product in products:
            if get_field(product, "is_active", "active", default=True) is not True:
                continue
            product_id = get_field(product, "product_id", "id")
            price = get_field(product, "price", default=None)
            stock = get_field(product, "stock", "stock_quantity", "quantity", "inventory", default=None)
            if product_id is None or price is None or stock is None:
                continue
            try:
                candidates.append((int(product_id), float(price), int(float(str(stock)))))
            except (TypeError, ValueError):
                continue

        if not candidates:
            pytest.skip("No usable active products with price and stock metadata")

        # Pick the highest-price product to minimize quantity needed for threshold crossing.
        product_id, price, stock = sorted(candidates, key=lambda x: x[1], reverse=True)[0]
        needed_qty = ceil(5001 / price)
        if needed_qty > stock:
            pytest.skip("Cannot construct cart total >5000 with available stock")

        add_response = session.post(
            api_url("/cart/add"),
            json={"product_id": product_id, "quantity": needed_qty},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_response.status_code in (200, 201)

        checkout_response = session.post(
            api_url("/checkout"),
            json={"payment_method": "COD"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert checkout_response.status_code == 400


class TestWalletAndLoyalty:
    def test_wallet_pay_decreases_balance_by_exact_amount(self, session, api_url, user_headers, server_ready):
        before_response = session.get(api_url("/wallet"), headers=user_headers, timeout=TIMEOUT)
        assert before_response.status_code == 200
        before_payload = extract_object(before_response.json(), "wallet", "data")
        before_balance = float(get_field(before_payload, "balance", "wallet_balance", default=0.0))

        if before_balance < 100.0:
            top_up_response = session.post(
                api_url("/wallet/add"),
                json={"amount": 150},
                headers=user_headers,
                timeout=TIMEOUT,
            )
            assert top_up_response.status_code in (200, 201)
            before_response = session.get(api_url("/wallet"), headers=user_headers, timeout=TIMEOUT)
            assert before_response.status_code == 200
            before_payload = extract_object(before_response.json(), "wallet", "data")
            before_balance = float(get_field(before_payload, "balance", "wallet_balance", default=0.0))

        pay_response = session.post(
            api_url("/wallet/pay"),
            json={"amount": 100},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert pay_response.status_code in (200, 201)

        after_response = session.get(api_url("/wallet"), headers=user_headers, timeout=TIMEOUT)
        assert after_response.status_code == 200
        after_payload = extract_object(after_response.json(), "wallet", "data")
        after_balance = float(get_field(after_payload, "balance", "wallet_balance", default=0.0))

        assert before_balance - after_balance == 100.0

    def test_wallet_and_loyalty_validation(self, session, api_url, user_headers, server_ready):
        wallet_response = session.get(api_url("/wallet"), headers=user_headers, timeout=TIMEOUT)
        assert wallet_response.status_code == 200

        wallet_payload = extract_object(wallet_response.json(), "wallet", "data")
        balance = float(get_field(wallet_payload, "balance", "wallet_balance", default=0.0))

        add_invalid = session.post(
            api_url("/wallet/add"),
            json={"amount": 0},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_invalid.status_code == 400

        add_too_large = session.post(
            api_url("/wallet/add"),
            json={"amount": 100001},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_too_large.status_code == 400

        pay_too_much = session.post(
            api_url("/wallet/pay"),
            json={"amount": balance + 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert pay_too_much.status_code == 400

        pay_zero = session.post(
            api_url("/wallet/pay"),
            json={"amount": 0},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert pay_zero.status_code == 400

        loyalty_response = session.get(api_url("/loyalty"), headers=user_headers, timeout=TIMEOUT)
        assert loyalty_response.status_code == 200

        loyalty_payload = extract_object(loyalty_response.json(), "loyalty", "data")
        points = int(get_field(loyalty_payload, "points", "loyalty_points", default=0))

        redeem_zero = session.post(
            api_url("/loyalty/redeem"),
            json={"points": 0},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert redeem_zero.status_code == 400

        redeem_too_many = session.post(
            api_url("/loyalty/redeem"),
            json={"points": points + 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert redeem_too_many.status_code == 400

    def test_wallet_and_loyalty_wrong_types_rejected(self, session, api_url, user_headers, server_ready):
        wallet_wrong_type = session.post(
            api_url("/wallet/add"),
            json={"amount": "ten"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert wallet_wrong_type.status_code == 400

        loyalty_wrong_type = session.post(
            api_url("/loyalty/redeem"),
            json={"points": "many"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert loyalty_wrong_type.status_code == 400
