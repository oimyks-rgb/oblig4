"""Admin panel for Ekte Mat staff: food items, images, orders, questions (A1-A4)."""

from flask import Blueprint, render_template

from ..models import repos

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
def index():
    items = repos().food_items.list()
    return render_template("admin/index.html", items=items)
