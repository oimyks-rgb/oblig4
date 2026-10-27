"""Customer account: login, my orders and questions (C3-C5)."""

from urllib.parse import urlsplit

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from ..models import repos
from ..models.accounts import authenticate, register_customer
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


def _start_session(user):
    """New session for the logged-in user (prevents session fixation), keeping the cart."""
    cart = session.get("cart")
    session.clear()
    session["user_id"] = user.id
    if cart:
        session["cart"] = cart


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
        _start_session(user)
        flash(f"Logged in as {user.name}.", "success")
        default = url_for("admin.index") if user.is_admin else url_for("shop.index")
        return redirect(next_url or default)
    return render_template("account/login.html", email="", next=next_url)


@bp.route("/register", methods=["GET", "POST"])
def register():
    next_url = _safe_next(request.values.get("next"))
    form, errors = {}, {}
    if request.method == "POST":
        form = request.form
        user, errors = register_customer(
            repos().users,
            form.get("name", ""),
            form.get("email", ""),
            form.get("password", ""),
            form.get("confirm", ""),
        )
        if user:
            _start_session(user)
            flash(f"Welcome, {user.name}! Your account is ready.", "success")
            return redirect(next_url or url_for("shop.cart"))
    status = 400 if errors else 200
    return render_template("account/register.html", form=form, errors=errors, next=next_url), status


@bp.route("/orders/<order_id>")
@login_required
def order(order_id):
    """One order: confirmation after checkout (C3) and detail page for my orders (C4)."""
    found = repos().orders.get(order_id)
    if found is None or (found.customer_id != g.user.id and not g.user.is_admin):
        abort(404)  # don't reveal that other customers' orders exist
    return render_template("account/order.html", order=found)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You are logged out.", "success")
    return redirect(url_for("shop.index"))
