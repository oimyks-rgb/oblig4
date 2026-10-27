"""Checkout: turning the cart into an order (C3)."""

from datetime import date

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from ..models import repos
from ..models.cart import cart_lines, cart_total
from ..models.domain import EventCategory
from ..models.orders import MIN_LEAD_DAYS, earliest_event_date, parse_checkout, place_order
from .auth import login_required

bp = Blueprint("order", __name__, url_prefix="/order")

EMPTY_GROUP_ROWS = 3


def _group_rows(form):
    """Guest-group rows to show: what was typed, padded with empty rows."""
    rows = list(zip(form.getlist("group_count"), form.getlist("group_note"))) if form else []
    rows = [r for r in rows if any(v.strip() for v in r)]
    return rows + [("", "")] * max(EMPTY_GROUP_ROWS - len(rows), 1)


@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    lines, notices = cart_lines(session.get("cart", {}), repos().food_items)
    for notice in notices:
        flash(notice, "error")
    if not lines:
        flash("Your cart is empty. Add something from the menu first.", "error")
        return redirect(url_for("shop.index"))

    today = date.today()
    errors = {}
    form = request.form if request.method == "POST" else None
    if form is not None:
        order, errors = parse_checkout(form, lines, g.user, today, repos().food_items)
        if not errors:
            order = place_order(repos().orders, order)
            session.pop("cart", None)
            flash(f"Thank you! Your order {order.reference} has been submitted. "
                  "Ekte Mat will confirm it soon.", "success")
            return redirect(url_for("account.order", order_id=order.id))

    return (
        render_template(
            "order/checkout.html",
            lines=lines,
            total=cart_total(lines),
            form=form or {},
            errors=errors,
            group_rows=_group_rows(form),
            categories=list(EventCategory),
            earliest=earliest_event_date(today).isoformat(),
            min_lead_days=MIN_LEAD_DAYS,
        ),
        400 if errors else 200,
    )
