"""Customer site: menu, cart and ordering (C1-C3)."""

from flask import Blueprint, abort, flash, g, make_response, redirect, render_template, request, session, url_for

from ..models import repos
from ..models.cart import cart_lines, cart_portions, cart_total, parse_quantity, validate_quantity
from ..models.domain import EventCategory
from ..models.images import is_draft

bp = Blueprint("shop", __name__)


@bp.route("/")
def index():
    items = repos().food_items.list(published_only=True)
    sections = [
        (category, [i for i in items if category in i.event_categories])
        for category in EventCategory
    ]
    return render_template("shop/index.html", sections=[s for s in sections if s[1]])


@bp.route("/images/<name>")
def image(name):
    """Pictures from the image store (A2). Names are content hashes, so they can be cached for long."""
    data = repos().images.read(name)
    if data is None or (is_draft(name) and not (g.user and g.user.is_admin)):
        abort(404)
    response = make_response(data)
    response.headers["Content-Type"] = "image/jpeg"
    response.headers["X-Content-Type-Options"] = "nosniff"
    if is_draft(name):
        response.headers["Cache-Control"] = "private, no-store"
    else:
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


# ---------- C2 shopping cart (kept in the session as {food_item_id: quantity}) ----------


def get_cart() -> dict:
    return dict(session.get("cart", {}))


def save_cart(cart: dict) -> None:
    session["cart"] = cart


@bp.app_context_processor
def inject_cart_count():
    return {"cart_portions": cart_portions(session.get("cart", {}))}


def _published_item_or_none(item_id):
    item = repos().food_items.get(item_id or "")
    return item if item and item.published else None


@bp.route("/cart/add", methods=["POST"])
def cart_add():
    item = _published_item_or_none(request.form.get("item_id"))
    if item is None:
        flash("That item is not on the menu.", "error")
        return redirect(url_for("shop.index"))
    raw = request.form.get("quantity", "").strip()
    quantity = parse_quantity(raw) if raw else item.min_order_qty
    cart = get_cart()
    if quantity is None or quantity < 1:
        error, total = "Enter a whole number of portions.", None
    else:
        # The minimum applies to the total in the cart, so adding 5 more to 10 is fine
        total = cart.get(item.id, 0) + quantity
        error = validate_quantity(item, total)
    if error:
        flash(error, "error")
        return redirect(url_for("shop.index"))
    cart[item.id] = total
    save_cart(cart)
    flash(f"Added {quantity} × {item.name} to your cart.", "success")
    return redirect(url_for("shop.index"))


@bp.route("/cart")
def cart():
    current = get_cart()
    lines, notices = cart_lines(current, repos().food_items)
    for notice in notices:
        flash(notice, "error")
    if notices:  # drop items that are no longer on the menu
        save_cart({line.food_item_id: line.quantity for line in lines})
    return _render_cart(lines, {})


def _render_cart(lines, errors, status=200):
    items = {line.food_item_id: repos().food_items.get(line.food_item_id) for line in lines}
    minimums = {item_id: item.min_order_qty for item_id, item in items.items() if item}
    return (
        render_template(
            "shop/cart.html", lines=lines, total=cart_total(lines), errors=errors, minimums=minimums
        ),
        status,
    )


@bp.route("/cart/update", methods=["POST"])
def cart_update():
    cart, errors = get_cart(), {}
    for item_id in list(cart):
        raw = request.form.get(f"quantity-{item_id}")
        if raw is None:
            continue
        quantity = parse_quantity(raw)
        if quantity == 0:
            del cart[item_id]
            continue
        item = _published_item_or_none(item_id)
        if item is None:
            del cart[item_id]
            continue
        error = validate_quantity(item, quantity)
        if error:
            errors[item_id] = error  # keep the old quantity
        else:
            cart[item_id] = quantity
    save_cart(cart)
    if errors:
        lines, _ = cart_lines(cart, repos().food_items)
        return _render_cart(lines, errors, 400)
    flash("Cart updated.", "success")
    return redirect(url_for("shop.cart"))


@bp.route("/cart/remove", methods=["POST"])
def cart_remove():
    cart = get_cart()
    if cart.pop(request.form.get("item_id", ""), None) is not None:
        save_cart(cart)
        flash("Removed from your cart.", "success")
    return redirect(url_for("shop.cart"))
