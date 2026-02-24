from datetime import datetime

from flask import Blueprint, render_template, __version__ as flask_version

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    now = datetime.now()
    radar_chart = {
        "id": "radarChartCanvas",
        "title": "Skills Radar",
        "labels": ["Backend", "Frontend", "UX", "DevOps", "Testing"],
        "datasets": [
            {"label": "Current", "values": [3, 4, 2, 4, 3], "max": 5},
            {"label": "Target", "values": [4, 5, 4, 5, 4], "max": 5},
        ],
        "step": 1,
        "max": 5,
    }
    return render_template(
        "home.html",
        page_title="Dashboard",
        breadcrumbs=[
            {"label": "Home", "url": "/"},
            {"label": "Second Page", "url": "/"},
            {"label": "third page", "url": "/"}
        ],
        timestamp=now.isoformat(),
        flask_version=flask_version,
        radar_chart=radar_chart,
    )
