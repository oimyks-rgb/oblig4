"""Login state for all blueprints: g.user, current_user in templates, and access decorators."""

from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from ..models import repos


def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = repos().users.get(user_id) if user_id else None
    if user_id and g.user is None:  # user deleted since login
        session.clear()


def inject_current_user():
    return {"current_user": g.get("user")}


def init_app(app):
    app.before_request(load_logged_in_user)
    app.context_processor(inject_current_user)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("account.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not g.user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped
