"""Admin panel for Ekte Mat staff: food items, images, orders, questions (A1-A4)."""

from dataclasses import replace
from datetime import date, timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from ..models import image_generator, repos
from ..models.domain import Allergen, DietaryLabel, EventCategory, OrderStatus, PaymentStatus
from ..models.food_items import parse_food_item, publish_errors
from ..models.image_generation import (
    INSTRUCTION_MAX,
    ImageGenerationError,
    default_illustration_prompt,
)
from ..models.images import ImageError, process_image
from ..models.order_status import check_transition, is_open, next_statuses
from ..models.questions import ANSWER_MAX, new_answer, parse_answer
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
        flash(f"Added {item.name}. Now add a picture.", "success")
        return redirect(url_for("admin.image_page", item_id=item.id))
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
    item = _get_item_or_404(item_id)
    if repos().food_items.is_ordered(item_id):
        flash(f"{item.name} has been ordered, so it can't be deleted. Unpublish it instead.", "error")
        return redirect(url_for("admin.food_items"))
    repos().food_items.delete(item_id)
    _delete_if_unused(item.image_filename)
    flash(f"Deleted {item.name}.", "success")
    return redirect(url_for("admin.food_items"))


# ---------- A2 pictures ----------

DRAFTS_KEY = "image_drafts"  # session: {item_id: draft image name}


def _draft_for(item_id):
    return session.get(DRAFTS_KEY, {}).get(item_id)


def _set_draft(item_id, name):
    drafts = dict(session.get(DRAFTS_KEY, {}))
    old = drafts.pop(item_id, None)
    if old:
        repos().images.delete(old)
    if name:
        drafts[item_id] = name
    session[DRAFTS_KEY] = drafts


def _render_image_page(item, status=200, error=None, instruction=None, mode="create"):
    return (
        render_template(
            "admin/food_items/image.html",
            item=item,
            error=error,
            generator_enabled=image_generator() is not None,
            instruction=instruction if instruction is not None else default_illustration_prompt(item),
            mode=mode,
            instruction_max=INSTRUCTION_MAX,
        ),
        status,
    )


def _store_draft(item, data):
    """Check the picture, store it as a draft and go to the preview."""
    images = repos().images
    images.cleanup_drafts(timedelta(days=1))
    _set_draft(item.id, images.save(process_image(data), draft=True))
    return redirect(url_for("admin.image_preview", item_id=item.id))


@bp.route("/food-items/<item_id>/image")
@admin_required
def image_page(item_id):
    return _render_image_page(_get_item_or_404(item_id))


@bp.route("/food-items/<item_id>/image/upload", methods=["POST"])
@admin_required
def upload_image(item_id):
    item = _get_item_or_404(item_id)
    upload = request.files.get("picture")
    try:
        return _store_draft(item, upload.read() if upload else b"")
    except ImageError as error:
        return _render_image_page(item, 400, error=str(error))


@bp.route("/food-items/<item_id>/image/generate", methods=["POST"])
@admin_required
def generate_image(item_id):
    item = _get_item_or_404(item_id)
    generator = image_generator()
    if generator is None:
        abort(404)
    instruction = request.form.get("instruction", "").strip()
    mode = request.form.get("mode", "create")
    if not instruction:
        return _render_image_page(item, 400, "Write an instruction for the picture.", instruction, mode)
    if len(instruction) > INSTRUCTION_MAX:
        message = f"The instruction can be at most {INSTRUCTION_MAX} characters."
        return _render_image_page(item, 400, message, instruction, mode)
    try:
        if mode == "modify":
            current = repos().images.read(item.image_filename or "")
            if current is None:
                return _render_image_page(item, 400, "There is no picture to modify.", instruction, mode)
            data = generator.modify(current, instruction)
        else:
            data = generator.create(instruction)
        return _store_draft(item, data)
    except ImageGenerationError as error:
        return _render_image_page(item, 502, str(error), instruction, mode)
    except ImageError:
        message = "The image service returned something that is not a usable picture."
        return _render_image_page(item, 502, message, instruction, mode)


@bp.route("/food-items/<item_id>/image/preview")
@admin_required
def image_preview(item_id):
    item = _get_item_or_404(item_id)
    draft = _draft_for(item_id)
    if not draft or not repos().images.exists(draft):
        return redirect(url_for("admin.image_page", item_id=item_id))
    return render_template("admin/food_items/image_preview.html", item=item, draft=draft)


def _delete_if_unused(name):
    if name and not any(i.image_filename == name for i in repos().food_items.list()):
        repos().images.delete(name)


@bp.route("/food-items/<item_id>/image/save", methods=["POST"])
@admin_required
def save_image(item_id):
    item = _get_item_or_404(item_id)
    draft = _draft_for(item_id)
    if not draft or not repos().images.exists(draft):
        flash("The preview has expired. Please try again.", "error")
        return redirect(url_for("admin.image_page", item_id=item_id))
    old = item.image_filename
    new_name = repos().images.promote(draft)
    _set_draft(item_id, None)
    repos().food_items.update(replace(item, image_filename=new_name))
    if old != new_name:
        _delete_if_unused(old)
    flash(f"Saved the new picture for {item.name}.", "success")
    return redirect(url_for("admin.food_items"))


@bp.route("/food-items/<item_id>/image/discard", methods=["POST"])
@admin_required
def discard_image(item_id):
    _get_item_or_404(item_id)
    _set_draft(item_id, None)
    flash("The new picture was discarded.", "success")
    return redirect(url_for("admin.image_page", item_id=item_id))


@bp.route("/food-items/<item_id>/image/remove", methods=["POST"])
@admin_required
def remove_image(item_id):
    item = _get_item_or_404(item_id)
    repos().food_items.update(replace(item, image_filename=None))
    _delete_if_unused(item.image_filename)
    flash(f"Removed the picture for {item.name}.", "success")
    return redirect(url_for("admin.image_page", item_id=item_id))


@bp.app_errorhandler(413)
def file_too_large(error):
    flash("The file is too large (max 5 MB).", "error")
    return redirect(request.referrer or url_for("admin.food_items"))


# ---------- A3 orders ----------

STATUS_FILTERS = ("open", "all")


@bp.context_processor
def inject_unanswered_count():
    """Admin pages only: the number of questions waiting for an answer (A4), shown in the admin nav."""
    if not (g.get("user") and g.user.is_admin):
        return {}
    return {"unanswered_count": len(repos().questions.list_unanswered())}


def _parse_status_filter(raw):
    """("open"/"all"/OrderStatus, error)"""
    raw = (raw or "open").strip()
    if raw in STATUS_FILTERS:
        return raw, None
    try:
        return OrderStatus(raw), None
    except ValueError:
        return "open", "Unknown status filter; showing open orders."


def _parse_date_filter(raw):
    raw = (raw or "").strip()
    if not raw:
        return None, None
    try:
        return date.fromisoformat(raw), None
    except ValueError:
        return None, "Use a valid event date."


@bp.route("/orders/")
@admin_required
def orders():
    status_filter, status_error = _parse_status_filter(request.args.get("status"))
    event_date, date_error = _parse_date_filter(request.args.get("event_date"))
    for error in (status_error, date_error):
        if error:
            flash(error, "error")

    found = repos().orders.list(
        status=status_filter if isinstance(status_filter, OrderStatus) else None,
        event_date=event_date,
    )
    if status_filter == "open":
        found = [o for o in found if is_open(o.status)]
    found.sort(key=lambda o: (o.event_date, o.created_at))  # soonest event first, for the kitchen

    customers = {cid: repos().users.get(cid) for cid in {o.customer_id for o in found}}
    unanswered = {}
    for question in repos().questions.list_unanswered():
        unanswered[question.order_id] = unanswered.get(question.order_id, 0) + 1
    return render_template(
        "admin/orders/list.html",
        orders=found,
        customers=customers,
        unanswered=unanswered,
        statuses=list(OrderStatus),
        status_filter=status_filter.value if isinstance(status_filter, OrderStatus) else status_filter,
        event_date=event_date.isoformat() if event_date else "",
    )


def _get_order_or_404(order_id):
    found = repos().orders.get(order_id)
    if found is None:
        abort(404)
    return found


@bp.route("/orders/<order_id>")
@admin_required
def order(order_id):
    found = _get_order_or_404(order_id)
    return render_template(
        "admin/orders/order.html",
        order=found,
        customer=repos().users.get(found.customer_id),
        questions=repos().questions.list_for_order(found.id),
        next_statuses=next_statuses(found.status),
        payment_statuses=list(PaymentStatus),
        answer_max=ANSWER_MAX,
    )


@bp.route("/orders/<order_id>/status", methods=["POST"])
@admin_required
def change_order_status(order_id):
    found = _get_order_or_404(order_id)
    try:
        new = OrderStatus(request.form.get("status", ""))
    except ValueError:
        flash("Choose a valid status.", "error")
        return redirect(url_for("admin.order", order_id=order_id))
    error = check_transition(found.status, new)
    if error:
        flash(error, "error")
    else:
        repos().orders.update_status(order_id, status=new)
        flash(f"Status of {found.reference} changed to {new.label}.", "success")
    return redirect(url_for("admin.order", order_id=order_id))


@bp.route("/orders/<order_id>/payment", methods=["POST"])
@admin_required
def change_payment_status(order_id):
    found = _get_order_or_404(order_id)
    try:
        new = PaymentStatus(request.form.get("payment_status", ""))
    except ValueError:
        flash("Choose a valid payment status.", "error")
        return redirect(url_for("admin.order", order_id=order_id))
    if new != found.payment_status:
        repos().orders.update_status(order_id, payment_status=new)
        flash(f"Payment status of {found.reference} changed to {new.label}.", "success")
    return redirect(url_for("admin.order", order_id=order_id))


# ---------- A4 questions ----------


@bp.route("/questions/")
@admin_required
def questions():
    waiting = repos().questions.list_unanswered()
    orders_by_id = {oid: repos().orders.get(oid) for oid in {q.order_id for q in waiting}}
    customers = {cid: repos().users.get(cid) for cid in {q.customer_id for q in waiting}}
    return render_template(
        "admin/questions/list.html", questions=waiting, orders=orders_by_id, customers=customers
    )


@bp.route("/questions/<question_id>/answer", methods=["POST"])
@admin_required
def answer_question(question_id):
    order_id = request.form.get("order_id", "")
    found = _get_order_or_404(order_id)
    if not any(q.id == question_id for q in repos().questions.list_for_order(found.id)):
        abort(404)
    text, errors = parse_answer(request.form.get("answer", ""))
    if errors:
        flash(errors["answer"], "error")
    else:
        repos().questions.answer(question_id, new_answer(text, g.user))
        flash("Answer saved. The customer can read it on the order page.", "success")
    return redirect(url_for("admin.order", order_id=found.id, _anchor=f"q-{question_id}"))
