from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from requests.exceptions import ReadTimeout

from .conftest import TIMEOUT
from .helpers import extract_list, extract_object, get_field


def _read_stock(products_payload, product_id: int):
    products = extract_list(products_payload, "products", "data", "items")
    for product in products:
        pid = get_field(product, "product_id", "id")
        if pid == product_id:
            return get_field(product, "stock", "stock_quantity", "quantity", "inventory", default=None)
    return None


class TestOrders:
    def test_cannot_cancel_delivered_order(self, session, api_url, user_headers, server_ready):
        orders_response = session.get(api_url("/orders"), headers=user_headers, timeout=TIMEOUT)
        assert orders_response.status_code == 200

        orders = extract_list(orders_response.json(), "orders", "data", "items")
        delivered = None
        for order in orders:
            status = get_field(order, "order_status", "status")
            if str(status).upper() == "DELIVERED":
                delivered = order
                break

        if delivered is None:
            pytest.skip("No delivered order available in seed data")

        order_id = get_field(delivered, "order_id", "id")
        assert order_id is not None

        try:
            cancel_response = session.post(api_url(f"/orders/{order_id}/cancel"), headers=user_headers, timeout=TIMEOUT)
        except ReadTimeout:
            pytest.fail("Cancel on DELIVERED order timed out; expected a 400 rejection response")
        assert cancel_response.status_code == 400

    def test_invoice_subtotal_plus_gst_matches_total(self, session, api_url, user_headers, active_product, clear_cart, server_ready):
        add_response = session.post(
            api_url("/cart/add"),
            json={"product_id": active_product["product_id"], "quantity": 1},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert add_response.status_code in (200, 201)

        checkout_response = session.post(
            api_url("/checkout"),
            json={"payment_method": "CARD"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert checkout_response.status_code in (200, 201)
        checkout_payload = checkout_response.json()

        order_id = get_field(checkout_payload, "order_id")
        if order_id is None:
            order = extract_object(checkout_payload, "order", "data")
            order_id = get_field(order, "order_id", "id")
        assert order_id is not None

        invoice_response = session.get(api_url(f"/orders/{order_id}/invoice"), headers=user_headers, timeout=TIMEOUT)
        assert invoice_response.status_code == 200
        invoice_payload = invoice_response.json()
        invoice = extract_object(invoice_payload, "invoice", "data")

        subtotal = get_field(invoice, "subtotal", "sub_total", default=None)
        gst = get_field(invoice, "gst", "gst_amount", "tax", "tax_amount", default=None)
        total = get_field(invoice, "total", "total_amount", "grand_total", default=None)

        if subtotal is None:
            subtotal = get_field(invoice_payload, "subtotal", "sub_total", default=None)
        if gst is None:
            gst = get_field(invoice_payload, "gst", "gst_amount", "tax", "tax_amount", default=None)
        if total is None:
            total = get_field(invoice_payload, "total", "total_amount", "grand_total", default=None)

        assert subtotal is not None and gst is not None and total is not None
        assert Decimal(str(subtotal)) + Decimal(str(gst)) == Decimal(str(total))

    def test_cancel_order_restores_product_stock(self, session, api_url, admin_headers, user_headers, active_product, clear_cart, server_ready):
        product_id = active_product["product_id"]

        before_products = session.get(api_url("/admin/products"), headers=admin_headers, timeout=TIMEOUT)
        assert before_products.status_code == 200
        stock_before = _read_stock(before_products.json(), product_id)
        assert stock_before is not None

        add_response = session.post(
            api_url("/cart/add"),
            json={"product_id": product_id, "quantity": 1},
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
        assert checkout_response.status_code in (200, 201)

        checkout_payload = checkout_response.json()
        order_id = get_field(checkout_payload, "order_id")
        if order_id is None:
            order = extract_object(checkout_payload, "order", "data")
            order_id = get_field(order, "order_id", "id")
        assert order_id is not None

        after_checkout_products = session.get(api_url("/admin/products"), headers=admin_headers, timeout=TIMEOUT)
        assert after_checkout_products.status_code == 200
        stock_after_checkout = _read_stock(after_checkout_products.json(), product_id)
        assert stock_after_checkout is not None

        cancel_response = session.post(
            api_url(f"/orders/{order_id}/cancel"),
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert cancel_response.status_code in (200, 201)

        after_cancel_products = session.get(api_url("/admin/products"), headers=admin_headers, timeout=TIMEOUT)
        assert after_cancel_products.status_code == 200
        stock_after_cancel = _read_stock(after_cancel_products.json(), product_id)
        assert stock_after_cancel is not None

        assert int(stock_after_checkout) == int(stock_before) - 1
        assert int(stock_after_cancel) == int(stock_before)

    def test_orders_list_and_missing_cancel(self, session, api_url, user_headers, server_ready):
        orders_response = session.get(api_url("/orders"), headers=user_headers, timeout=TIMEOUT)
        assert orders_response.status_code == 200

        cancel_missing = session.post(
            api_url("/orders/999999999/cancel"),
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert cancel_missing.status_code == 404

    def test_order_detail_missing_returns_404(self, session, api_url, user_headers, server_ready):
        response = session.get(api_url("/orders/999999999"), headers=user_headers, timeout=TIMEOUT)
        assert response.status_code == 404

    def test_invoice_missing_returns_404(self, session, api_url, user_headers, server_ready):
        response = session.get(api_url("/orders/999999999/invoice"), headers=user_headers, timeout=TIMEOUT)
        assert response.status_code == 404


class TestReviews:
    def test_reviews_reject_comment_length_out_of_bounds(self, session, api_url, user_headers, active_product, server_ready):
        product_id = active_product["product_id"]

        empty_comment = session.post(
            api_url(f"/products/{product_id}/reviews"),
            json={"rating": 5, "comment": ""},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert empty_comment.status_code == 400

        long_comment = session.post(
            api_url(f"/products/{product_id}/reviews"),
            json={"rating": 5, "comment": "x" * 201},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert long_comment.status_code == 400

    def test_reviews_reject_out_of_range_ratings(self, session, api_url, user_headers, active_product, server_ready):
        product_id = active_product["product_id"]
        for rating in (0, -1, 6):
            response = session.post(
                api_url(f"/products/{product_id}/reviews"),
                json={"rating": rating, "comment": f"invalid rating {rating}"},
                headers=user_headers,
                timeout=TIMEOUT,
            )
            assert response.status_code == 400

    def test_reviews_reject_invalid_rating(self, session, api_url, user_headers, active_product, server_ready):
        response = session.post(
            api_url(f"/products/{active_product['product_id']}/reviews"),
            json={"rating": 6, "comment": "invalid rating should fail"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400

    def test_reviews_reject_missing_comment(self, session, api_url, user_headers, active_product, server_ready):
        response = session.post(
            api_url(f"/products/{active_product['product_id']}/reviews"),
            json={"rating": 5},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400

    def test_reviews_reject_wrong_rating_type(self, session, api_url, user_headers, active_product, server_ready):
        response = session.post(
            api_url(f"/products/{active_product['product_id']}/reviews"),
            json={"rating": "five", "comment": "wrong type"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400


class TestSupportTickets:
    def test_support_ticket_rejects_open_to_closed_direct_transition(self, session, api_url, user_headers, server_ready):
        suffix = uuid4().hex[:8]
        create_response = session.post(
            api_url("/support/ticket"),
            json={"subject": f"Direct transition {suffix}", "message": "status transition check"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert create_response.status_code in (200, 201)

        created_payload = create_response.json()
        ticket_id = get_field(created_payload, "ticket_id")
        if ticket_id is None:
            ticket = extract_object(created_payload, "ticket", "data")
            ticket_id = get_field(ticket, "ticket_id", "id")
        assert ticket_id is not None

        direct_close = session.put(
            api_url(f"/support/tickets/{ticket_id}"),
            json={"status": "CLOSED"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert direct_close.status_code == 400

    def test_ticket_create_rejects_subject_or_message_length_violation(self, session, api_url, user_headers, server_ready):
        short_subject = session.post(
            api_url("/support/ticket"),
            json={"subject": "abc", "message": "valid message"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert short_subject.status_code == 400

        long_message = session.post(
            api_url("/support/ticket"),
            json={"subject": "Valid Subject", "message": "m" * 501},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert long_message.status_code == 400

    def test_support_ticket_preserves_percent_character_on_fetch(self, session, api_url, user_headers, server_ready):
        subject = f"Special chars {uuid4().hex[:8]}"
        message = "@#$%"

        create_response = session.post(
            api_url("/support/ticket"),
            json={"subject": subject, "message": message},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert create_response.status_code in (200, 201)

        created_payload = create_response.json()
        ticket_id = get_field(created_payload, "ticket_id")
        if ticket_id is None:
            ticket = extract_object(created_payload, "ticket", "data")
            ticket_id = get_field(ticket, "ticket_id", "id")
        assert ticket_id is not None

        fetch_response = session.get(api_url("/support/tickets"), headers=user_headers, timeout=TIMEOUT)
        assert fetch_response.status_code == 200
        tickets = extract_list(fetch_response.json(), "tickets", "data", "items")

        matched = None
        for ticket in tickets:
            if get_field(ticket, "ticket_id", "id") == ticket_id:
                matched = ticket
                break

        assert matched is not None
        assert "%" in str(get_field(matched, "message"))

    def test_support_ticket_lifecycle(self, session, api_url, user_headers, server_ready):
        suffix = uuid4().hex[:8]
        subject = f"Order issue {suffix}"
        message = f"Ticket body preserved {suffix}"

        create_response = session.post(
            api_url("/support/ticket"),
            json={"subject": subject, "message": message},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert create_response.status_code in (200, 201)

        ticket = extract_object(create_response.json(), "ticket", "data")
        ticket_id = get_field(ticket, "ticket_id", "id")
        assert ticket_id is not None
        assert get_field(ticket, "status") == "OPEN"
        assert get_field(ticket, "message") == message

        in_progress = session.put(
            api_url(f"/support/tickets/{ticket_id}"),
            json={"status": "IN_PROGRESS"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert in_progress.status_code == 200

        closed = session.put(
            api_url(f"/support/tickets/{ticket_id}"),
            json={"status": "CLOSED"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert closed.status_code == 200

        invalid_transition = session.put(
            api_url(f"/support/tickets/{ticket_id}"),
            json={"status": "OPEN"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert invalid_transition.status_code == 400

    def test_ticket_create_validation_missing_fields(self, session, api_url, user_headers, server_ready):
        missing_subject = session.post(
            api_url("/support/ticket"),
            json={"message": "hello"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert missing_subject.status_code == 400

        missing_message = session.post(
            api_url("/support/ticket"),
            json={"subject": "Valid Subject"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert missing_message.status_code == 400

    def test_ticket_update_rejects_invalid_status(self, session, api_url, user_headers, server_ready):
        suffix = uuid4().hex[:8]
        create_response = session.post(
            api_url("/support/ticket"),
            json={"subject": f"Subject {suffix}", "message": "Message body"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert create_response.status_code in (200, 201)

        ticket = extract_object(create_response.json(), "ticket", "data")
        ticket_id = get_field(ticket, "ticket_id", "id")
        assert ticket_id is not None

        response = session.put(
            api_url(f"/support/tickets/{ticket_id}"),
            json={"status": "RESOLVED"},
            headers=user_headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 400
