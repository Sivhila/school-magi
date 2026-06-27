"""
tenant.py — Multi-tenant middleware
Identifies which school is making the request based on subdomain,
attaches it to Flask's g object, and enforces subscription status.
"""
from flask import g, request, redirect, url_for, abort, current_app
from models import School


# Subdomains reserved for the platform itself
RESERVED_SUBDOMAINS = {
        "www", "app", "api", "admin", "superadmin",
        "mail", "smtp", "ftp", "cdn", "static", "assets",
        "docs", "help", "support", "billing",
        }


def get_current_school():
    """Return the School for the current request subdomain, or None."""
    host = request.host.split(":")[0]          # strip port
    base = current_app.config.get("BASE_DOMAIN", "localhost")

    # Running on localhost / plain domain → no tenant
    if host == base or host == "localhost" or host == "127.0.0.1":
        return None

    # e.g.  stmarys.yoursaas.com  →  subdomain = "stmarys"
    if host.endswith(f".{base}"):
        subdomain = host[: -(len(base) + 1)]
    else:
        return None

    if subdomain in RESERVED_SUBDOMAINS:
        return None

    return School.query.filter_by(subdomain=subdomain, is_active=True).first()


def init_tenant(app):
    """Register before_request hook on the app."""

    @app.before_request
    def resolve_tenant():
        g.school = get_current_school()

        # If we're on a school subdomain but can't find the school → 404
        host = request.host.split(":")[0]
        base = current_app.config.get("BASE_DOMAIN", "localhost")
        is_subdomain_request = (
                host != base
                and host != "localhost"
                and host != "127.0.0.1"
                and host.endswith(f".{base}")
                )

        if is_subdomain_request and g.school is None:
            abort(404)

        # If school exists but subscription expired → redirect to billing
        if g.school and not g.school.subscription_active():
            if not request.path.startswith("/billing") and \
                    not request.path.startswith("/auth") and \
                    not request.path.startswith("/static"):
                        return redirect(url_for("billing.expired"))
