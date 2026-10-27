"""Customer account: login, my orders and questions (C3-C5)."""

from urllib.parse import urlsplit

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from ..models import repos
from ..models.accounts import authenticate, register_customer
from ..models.domain import OrderStatus
from ..models.questions import TEXT_MAX as QUESTION_MAX
from ..models.questions import new_question, parse_question
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
    """My orders (C4): the customer's orders with status, payment status and questions."""
    orders = repos().orders.list_for_customer(g.user.id)
    questions = {}
    for question in repos().questions.list_for_customer(g.user.id):
        asked, answered = questions.get(question.order_id, (0, 0))
        questions[question.order_id] = (asked + 1, answered + question.is_answered)
    return render_template(
        "account/index.html", orders=orders, questions=questions, statuses=list(OrderStatus)
    )


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


def _visible_order_or_404(order_id):
    found = repos().orders.get(order_id)
    if found is None or (found.customer_id != g.user.id and not g.user.is_admin):
        abort(404)  # don't reveal that other customers' orders exist
    return found


def _render_order(found, question_text="", errors=None, status=200):
    return (
        render_template(
            "account/order.html",
            order=found,
            questions=repos().questions.list_for_order(found.id),
            can_ask=found.customer_id == g.user.id,
            question_text=question_text,
            errors=errors or {},
            text_max=QUESTION_MAX,
        ),
        status,
    )


@bp.route("/orders/<order_id>")
@login_required
def order(order_id):
    """One order: confirmation after checkout (C3), details for my orders (C4), questions (C5)."""
    return _render_order(_visible_order_or_404(order_id))


@bp.route("/orders/<order_id>/questions", methods=["POST"])
@login_required
def ask_question(order_id):
    found = _visible_order_or_404(order_id)
    if found.customer_id != g.user.id:
        abort(404)  # only the customer who placed the order asks about it
    text, errors = parse_question(request.form.get("text", ""))
    if errors:
        return _render_order(found, text, errors, 400)
    repos().questions.add(new_question(found, g.user, text))
    flash("Your question was sent. Ekte Mat will answer here.", "success")
    return redirect(url_for("account.order", order_id=found.id, _anchor="questions"))


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You are logged out.", "success")
    return redirect(url_for("shop.index"))
