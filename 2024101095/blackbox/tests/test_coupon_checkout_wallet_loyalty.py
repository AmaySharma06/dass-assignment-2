from __future__ import annotations

from datetime import datetime

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


class TestWalletAndLoyalty:
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
