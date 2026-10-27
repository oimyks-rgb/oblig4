"""Customer site: menu, cart and ordering (C1-C3)."""

from flask import Blueprint, abort, g, make_response, render_template

from ..models import repos
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
