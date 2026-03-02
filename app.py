from __future__ import annotations

import calendar
import logging
import sqlite3
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "calendar.db"
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "app.log"
DATETIME_FMT = "%Y-%m-%dT%H:%M"

app = Flask(__name__)
app.config["SECRET_KEY"] = "calendar-mvp-secret"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers.clear()
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.setLevel(logging.INFO)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: object) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT,
            notes TEXT
        )
        """
    )
    db.commit()


def parse_form_datetime(value: str) -> datetime:
    return datetime.strptime(value, DATETIME_FMT)


def fetch_event(event_id: int) -> Optional[sqlite3.Row]:
    return get_db().execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()


@app.route("/")
def month_view():
    now = datetime.now()
    year = int(request.args.get("year", now.year))
    month = int(request.args.get("month", now.month))

    first_day = datetime(year, month, 1)
    next_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)

    rows = get_db().execute(
        """
        SELECT * FROM events
        WHERE start_time < ? AND end_time >= ?
        ORDER BY start_time ASC
        """,
        (next_month.isoformat(), first_day.isoformat()),
    ).fetchall()

    events_by_day: dict[str, list[sqlite3.Row]] = {}
    for event in rows:
        start = datetime.fromisoformat(event["start_time"]).date()
        end = datetime.fromisoformat(event["end_time"]).date()
        cursor = max(start, first_day.date())
        while cursor <= end and cursor < next_month.date():
            key = cursor.isoformat()
            events_by_day.setdefault(key, []).append(event)
            cursor += timedelta(days=1)

    month_matrix = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    prev_month = first_day - timedelta(days=1)
    next_month_ref = next_month

    month_event_count = len(rows)

    return render_template(
        "index.html",
        month_matrix=month_matrix,
        current_year=year,
        current_month=month,
        month_name=calendar.month_name[month],
        events_by_day=events_by_day,
        month_event_count=month_event_count,
        prev_year=prev_month.year,
        prev_month=prev_month.month,
        next_year=next_month_ref.year,
        next_month=next_month_ref.month,
        today=datetime.now().date(),
    )


@app.route("/events/new", methods=["GET", "POST"])
def create_event():
    if request.method == "POST":
        title = request.form["title"].strip()
        location = request.form.get("location", "").strip()
        notes = request.form.get("notes", "").strip()
        start_raw = request.form["start_time"]
        end_raw = request.form["end_time"]

        try:
            start_dt = parse_form_datetime(start_raw)
            end_dt = parse_form_datetime(end_raw)
        except ValueError:
            flash("时间格式不正确。", "error")
            return render_template("form.html", event=request.form, mode="create")

        if end_dt < start_dt:
            flash("结束时间不能早于开始时间。", "error")
            return render_template("form.html", event=request.form, mode="create")

        get_db().execute(
            """
            INSERT INTO events (title, start_time, end_time, location, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, start_dt.isoformat(), end_dt.isoformat(), location, notes),
        )
        get_db().commit()
        flash("日程已创建。", "success")
        return redirect(url_for("month_view"))

    return render_template("form.html", event=None, mode="create")


@app.post("/events/quick")
def quick_create_event():
    title = request.form.get("title", "").strip() or "未命名日程"
    day_raw = request.form.get("day", "")
    start_hm = request.form.get("start_hm", "09:00")
    end_hm = request.form.get("end_hm", "10:00")

    try:
        start_dt = datetime.fromisoformat(f"{day_raw}T{start_hm}")
        end_dt = datetime.fromisoformat(f"{day_raw}T{end_hm}")
    except ValueError:
        flash("快速新建失败：日期或时间格式不正确。", "error")
        return redirect(url_for("month_view"))

    if end_dt <= start_dt:
        end_dt = start_dt + timedelta(hours=1)

    get_db().execute(
        """
        INSERT INTO events (title, start_time, end_time, location, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title, start_dt.isoformat(), end_dt.isoformat(), "", ""),
    )
    get_db().commit()
    flash("日程已快速创建。", "success")

    return redirect(url_for("month_view", year=start_dt.year, month=start_dt.month))


@app.post("/events/<int:event_id>/move")
def move_event(event_id: int):
    event = fetch_event(event_id)
    if event is None:
        return jsonify({"ok": False, "error": "event not found"}), 404

    payload = request.get_json(silent=True) or {}
    day_raw = str(payload.get("day", "")).strip()

    try:
        new_day = datetime.fromisoformat(day_raw).date()
    except ValueError:
        return jsonify({"ok": False, "error": "invalid day"}), 400

    old_start = datetime.fromisoformat(event["start_time"])
    old_end = datetime.fromisoformat(event["end_time"])
    duration = old_end - old_start

    new_start = datetime.combine(new_day, old_start.time())
    new_end = new_start + duration

    get_db().execute(
        "UPDATE events SET start_time = ?, end_time = ? WHERE id = ?",
        (new_start.isoformat(), new_end.isoformat(), event_id),
    )
    get_db().commit()

    return jsonify({"ok": True})


@app.route("/events/<int:event_id>")
def event_detail(event_id: int):
    event = fetch_event(event_id)
    if event is None:
        flash("日程不存在。", "error")
        return redirect(url_for("month_view"))
    return render_template("view.html", event=event)


@app.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
def edit_event(event_id: int):
    event = fetch_event(event_id)
    if event is None:
        flash("日程不存在。", "error")
        return redirect(url_for("month_view"))

    if request.method == "POST":
        title = request.form["title"].strip()
        location = request.form.get("location", "").strip()
        notes = request.form.get("notes", "").strip()
        start_raw = request.form["start_time"]
        end_raw = request.form["end_time"]

        try:
            start_dt = parse_form_datetime(start_raw)
            end_dt = parse_form_datetime(end_raw)
        except ValueError:
            flash("时间格式不正确。", "error")
            return render_template("form.html", event=request.form, mode="edit", event_id=event_id)

        if end_dt < start_dt:
            flash("结束时间不能早于开始时间。", "error")
            return render_template("form.html", event=request.form, mode="edit", event_id=event_id)

        get_db().execute(
            """
            UPDATE events
            SET title = ?, start_time = ?, end_time = ?, location = ?, notes = ?
            WHERE id = ?
            """,
            (title, start_dt.isoformat(), end_dt.isoformat(), location, notes, event_id),
        )
        get_db().commit()
        flash("日程已更新。", "success")
        return redirect(url_for("event_detail", event_id=event_id))

    payload = {
        "title": event["title"],
        "start_time": datetime.fromisoformat(event["start_time"]).strftime(DATETIME_FMT),
        "end_time": datetime.fromisoformat(event["end_time"]).strftime(DATETIME_FMT),
        "location": event["location"] or "",
        "notes": event["notes"] or "",
    }
    return render_template("form.html", event=payload, mode="edit", event_id=event_id)


@app.post("/events/<int:event_id>/delete")
def delete_event(event_id: int):
    get_db().execute("DELETE FROM events WHERE id = ?", (event_id,))
    get_db().commit()
    flash("日程已删除。", "success")
    return redirect(url_for("month_view"))


@app.template_filter("fmt_dt")
def fmt_dt(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")


setup_logging()

with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
