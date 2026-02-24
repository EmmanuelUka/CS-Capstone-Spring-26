from datetime import datetime

from flask import Blueprint, render_template, __version__ as flask_version

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    now = datetime.now()
    radar_chart = {
        "id": "radarChartCanvas",
        "title": "Player Comparison",
        "labels": ["Finishing", "Playmaking", "Agility", "Mentality", "Defense"],
        "datasets": [
            {"label": "Player A", "values": [4, 5, 4, 4, 3], "max": 5},
            {"label": "Player B", "values": [3, 4, 3, 5, 2], "max": 5},
        ],
        "step": 1,
        "max": 5,
    }
    return render_template(
        "home.html",
        page_title="Hashmark Scout",
        breadcrumbs=[
            {"label": "Hashmark", "url": "/"},
            {"label": "Highlights", "url": "/"},
            {"label": "Visit Logs", "url": "/"}
        ],
        timestamp=now.isoformat(),
        flask_version=flask_version,
        radar_chart=radar_chart,
    )
