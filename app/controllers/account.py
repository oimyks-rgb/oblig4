"""Customer account: login, my orders and questions (C3-C5)."""

from flask import Blueprint, render_template

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.route("/")
def index():
    return render_template("account/index.html")
