"""Customer account: login, my orders and questions (C3-C5)."""

from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..models import repos
from ..models.accounts import authenticate
from .auth import login_required

bp = Blueprint("account", __name__, url_prefix="/account")


def _safe_next(target):
    """Only follow redirects to a path on this site."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


@bp.route("/")
@login_required
def index():
    return render_template("account/index.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = _safe_next(request.values.get("next"))
    if request.method == "POST":
        email = request.form.get("email", "")
        user = authenticate(repos().users, email, request.form.get("password", ""))
        if user is None:
            flash("Wrong e-mail or password.", "error")
            return render_template("account/login.html", email=email, next=next_url), 401
        session.clear()
        session["user_id"] = user.id
        flash(f"Logged in as {user.name}.", "success")
        default = url_for("admin.index") if user.is_admin else url_for("shop.index")
        return redirect(next_url or default)
    return render_template("account/login.html", email="", next=next_url)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You are logged out.", "success")
    return redirect(url_for("shop.index"))
