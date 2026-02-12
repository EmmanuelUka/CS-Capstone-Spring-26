from datetime import datetime

from flask import Blueprint, render_template, __version__ as flask_version

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    now = datetime.now()
    return render_template(
        "home.html",
        page_title="Dashboard",
        breadcrumbs=[
            {"label": "Home", "url": "/"},
            {"label": "Second Page", "url": "/"},
            {"label": "third page", "url": "/"}
        ],
        timestamp=now,
        flask_version=flask_version,
    )
