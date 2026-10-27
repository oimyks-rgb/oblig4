"""Customer site: menu, cart and ordering (C1-C3)."""

from flask import Blueprint, render_template

from ..models import repos
from ..models.domain import EventCategory

bp = Blueprint("shop", __name__)


@bp.route("/")
def index():
    items = repos().food_items.list(published_only=True)
    sections = [
        (category, [i for i in items if category in i.event_categories])
        for category in EventCategory
    ]
    return render_template("shop/index.html", sections=[s for s in sections if s[1]])
