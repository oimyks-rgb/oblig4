from datetime import date

import pytest

from app.models.domain import OrderStatus, PaymentStatus, Role
from tests.conftest import add_user, make_item
from tests.test_order_repository import make_order


@pytest.fixture
def orders(repositories):
    repositories.food_items.add(make_item("soup", "Soup"))
    if not repositories.users.get_by_email("kari@example.test"):  # customer_client may have added her
        add_user(repositories, "kari", "kari@example.test", Role.CUSTOMER)
    made = {}
    for ref, event, status in [
        ("LATER1", date(2027, 3, 1), OrderStatus.SUBMITTED),
        ("SOON01", date(2027, 1, 10), OrderStatus.APPROVED),
        ("DONE01", date(2027, 1, 5), OrderStatus.DELIVERED),
    ]:
        order = make_order(ref.lower(), "kari", "soup", "EM-" + ref, event_date=event)
        order.status = status
        made[ref] = repositories.orders.add(order)
    return made


def page(client, url):
    response = client.get(url)
    assert response.status_code == 200, url
    return response.get_data(as_text=True)


def test_list_defaults_to_open_orders_soonest_first(admin_client, orders):
    html = page(admin_client, "/admin/orders/")
    assert html.index("EM-SOON01") < html.index("EM-LATER1")
    assert "EM-DONE01" not in html
    assert "Kari" in html


def test_status_and_date_filters(admin_client, orders):
    assert "EM-DONE01" in page(admin_client, "/admin/orders/?status=all")
    html = page(admin_client, "/admin/orders/?status=delivered")
    assert "EM-DONE01" in html and "EM-SOON01" not in html
    html = page(admin_client, "/admin/orders/?status=all&event_date=2027-01-10")
    assert "EM-SOON01" in html and "EM-LATER1" not in html and "EM-DONE01" not in html
    assert "No orders match." in page(admin_client, "/admin/orders/?status=rejected")


def test_bad_filters_are_reported(admin_client, orders):
    assert "Unknown status filter" in page(admin_client, "/admin/orders/?status=lost")
    assert "valid event date" in page(admin_client, "/admin/orders/?event_date=tomorrow")


def test_order_page_shows_customer_and_allowed_statuses(admin_client, orders):
    html = page(admin_client, f"/admin/orders/{orders['LATER1'].id}")
    assert "kari@example.test" in html
    assert '<option value="approved">' in html and '<option value="rejected">' in html
    assert '<option value="delivered">' not in html
    assert "is a final status" in page(admin_client, f"/admin/orders/{orders['DONE01'].id}")


def test_change_status(admin_client, repositories, orders):
    order_id = orders["LATER1"].id
    admin_client.post(f"/admin/orders/{order_id}/status", data={"status": "approved"})
    assert repositories.orders.get(order_id).status == OrderStatus.APPROVED
    assert "changed to Approved" in page(admin_client, f"/admin/orders/{order_id}")


def test_illegal_status_change_is_refused(admin_client, repositories, orders):
    done = orders["DONE01"].id
    admin_client.post(f"/admin/orders/{done}/status", data={"status": "approved"})
    assert repositories.orders.get(done).status == OrderStatus.DELIVERED
    assert "delivered order can&#39;t be changed" in page(admin_client, f"/admin/orders/{done}")
    admin_client.post(f"/admin/orders/{done}/status", data={"status": "teleported"})
    assert "valid status" in page(admin_client, f"/admin/orders/{done}")


def test_change_payment_status(admin_client, repositories, orders):
    order_id = orders["SOON01"].id
    admin_client.post(f"/admin/orders/{order_id}/payment", data={"payment_status": "deposit_paid"})
    assert repositories.orders.get(order_id).payment_status == PaymentStatus.DEPOSIT_PAID
    admin_client.post(f"/admin/orders/{order_id}/payment", data={"payment_status": "bitcoin"})
    assert repositories.orders.get(order_id).payment_status == PaymentStatus.DEPOSIT_PAID


def test_unknown_order_is_404(admin_client):
    assert admin_client.get("/admin/orders/nope").status_code == 404
    assert admin_client.post("/admin/orders/nope/status", data={"status": "approved"}).status_code == 404


def test_access_control(client, customer_client, orders):
    assert customer_client.get("/admin/orders/").status_code == 403
    assert customer_client.post(f"/admin/orders/{orders['LATER1'].id}/status", data={"status": "approved"}).status_code == 403
    customer_client.post("/account/logout")
    assert client.get("/admin/orders/").status_code == 302
