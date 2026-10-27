"""Admin panel for Ekte Mat staff: food items, images, orders, questions (A1-A4)."""

from dataclasses import replace

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..models import repos
from ..models.domain import Allergen, DietaryLabel, EventCategory
from ..models.food_items import parse_food_item, publish_errors
from .auth import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def index():
    return redirect(url_for("admin.food_items"))


# ---------- A1 food items ----------


def _get_item_or_404(item_id):
    item = repos().food_items.get(item_id)
    if item is None:
        abort(404)
    return item


def _render_form(item, errors, status=200, is_new=False):
    return (
        render_template(
            "admin/food_items/form.html",
            item=item,
            errors=errors,
            # Raw input, so invalid values (e.g. "abc" as price) are shown again as typed
            form=request.form if request.method == "POST" else None,
            is_new=is_new,
            categories=list(EventCategory),
            allergens=list(Allergen),
            dietary_labels=list(DietaryLabel),
        ),
        status,
    )


@bp.route("/food-items/")
@admin_required
def food_items():
    return render_template("admin/food_items/list.html", items=repos().food_items.list())


@bp.route("/food-items/new", methods=["GET", "POST"])
@admin_required
def new_food_item():
    if request.method == "POST":
        item, errors = parse_food_item(request.form)
        if errors:
            return _render_form(item, errors, 400, is_new=True)
        repos().food_items.add(item)
        flash(f"Added {item.name}.", "success")
        return redirect(url_for("admin.food_items"))
    item, _ = parse_food_item({"price_nok": "", "min_order_qty": "1"})
    return _render_form(item, {}, is_new=True)


@bp.route("/food-items/<item_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_food_item(item_id):
    existing = _get_item_or_404(item_id)
    if request.method == "POST":
        # The picture is managed separately (A2), so keep it
        item, errors = parse_food_item(request.form, item_id, existing.image_filename)
        if errors:
            return _render_form(item, errors, 400)
        repos().food_items.update(item)
        flash(f"Saved {item.name}.", "success")
        return redirect(url_for("admin.food_items"))
    return _render_form(existing, {})


@bp.route("/food-items/<item_id>/publish", methods=["POST"])
@admin_required
def toggle_published(item_id):
    item = _get_item_or_404(item_id)
    if not item.published:
        errors = publish_errors(item)
        if errors:
            for message in errors.values():
                flash(f"{item.name} was not published: {message}", "error")
            return redirect(url_for("admin.food_items"))
    item = replace(item, published=not item.published)
    repos().food_items.update(item)
    flash(f"{item.name} is now {'published' if item.published else 'hidden from customers'}.", "success")
    return redirect(url_for("admin.food_items"))


@bp.route("/food-items/<item_id>/delete", methods=["POST"])
@admin_required
def delete_food_item(item_id):
    # TODO(C3): once orders exist, block deleting items that have been ordered
    # and ask staff to unpublish them instead.
    item = _get_item_or_404(item_id)
    repos().food_items.delete(item_id)
    flash(f"Deleted {item.name}.", "success")
    return redirect(url_for("admin.food_items"))
