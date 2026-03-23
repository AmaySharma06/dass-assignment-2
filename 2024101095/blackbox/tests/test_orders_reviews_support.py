from __future__ import annotations

from uuid import uuid4

from .conftest import TIMEOUT
from .helpers import extract_object, get_field


class TestOrders:
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
