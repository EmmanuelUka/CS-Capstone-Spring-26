from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, __version__ as flask_version
from summeryGenerator import generate_scout_report

bp = Blueprint("main", __name__)


def generateSummery(text: str, name: str = "", position: str = "") -> dict:
    normalized_text = text.strip()
    words = [word.strip(".,!?:;()").lower() for word in normalized_text.split() if word.strip()]
    preview = normalized_text[:120]
    longest_word = max(words, key=len) if words else ""
    summary_text = ""
    player_name = name.strip() or "Player"
    player_position = position.strip()
    if normalized_text:
        try:
            summary_text = generate_scout_report(
            name=player_name,
            pos=player_position,
            prev="",
            notes=normalized_text,
            stream=True,
            suppress_stream_output=True,
        )
        except Exception as exc:
            summary_text = f"Unable to generate summary: {exc}"
    return {
        "summary": summary_text,
        "preview": preview,
        "word_count": len(words),
        "unique_words": len(set(words)),
        "longest_word": longest_word,
        "length": len(normalized_text),
    }


@bp.route("/api/generate-summary", methods=["POST"])
def generate_summary():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    name = payload.get("name", "")
    position = payload.get("position", "")
    if not isinstance(text, str):
        text = str(text)
    if not isinstance(name, str):
        name = str(name)
    if not isinstance(position, str):
        position = str(position)
    result = generateSummery(text, name=name, position=position)
    return jsonify(result)


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
