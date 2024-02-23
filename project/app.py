import os

from cs50 import SQL
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    jsonify,
)
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import calendar, re
from datetime import date, datetime, timedelta
from helpers import login_required, checkups_list

# Configures application
app = Flask(__name__)


# Configures session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configures CS50 Library to use SQLite database
db = SQL("sqlite:///health.db")


# Ensures the user always sees the most recent version
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Defines a class to pass events into calendar
class EventCalendar(calendar.HTMLCalendar):
    def __init__(self, events, current_month, current_year):
        super().__init__()
        self.events = events
        self.current_month = current_month
        self.current_year = current_year

    def formatday(self, day, weekday):
        if day != 0:
            event_html = ""
            for event in self.events:
                if (
                    datetime.strptime(event["last_checkup"], "%Y-%m-%d").day == day
                    and datetime.strptime(event["last_checkup"], "%Y-%m-%d").month
                    == self.current_month
                    and datetime.strptime(event["last_checkup"], "%Y-%m-%d").year
                    == self.current_year
                ):
                    event_html += f"<p>{event['checkup_name']}</p>"
                if (
                    event["next_checkup"] != ""
                    and datetime.strptime(event["next_checkup"], "%Y-%m-%d").day == day
                    and datetime.strptime(event["next_checkup"], "%Y-%m-%d").month
                    == self.current_month
                    and datetime.strptime(event["next_checkup"], "%Y-%m-%d").year
                    == self.current_year
                ):
                    event_html += f"<p>{event['checkup_name']}</p>"

            if event_html != "":
                return f'<td class="event-day day">{day}{event_html}</td>'
            else:
                return f'<td class="day">{day}</td>'
        return '<td class="day"></td>'


@app.route("/register", methods=["GET", "POST"])
def register():
    """Registers user"""

    if request.method == "POST":
        today = datetime.today()
        name = request.form.get("username")
        bd = request.form.get("BD")
        gender = request.form.get("gender")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        usernames = [
            row["username"] for row in db.execute("SELECT username FROM users")
        ]

        try:
            birthday = datetime.strptime(bd, "%Y-%m-%d").date()
        except ValueError:
            return render_template(
                "register.html",
                message="Registration failed. Birthday has to be a date.",
            )

        age = (
            today.year
            - birthday.year
            - ((today.month, today.day) < (birthday.month, birthday.day))
        )

        if not name:
            return render_template(
                "register.html", message="Registration failed. Please enter name."
            )
        elif not re.match("^[A-Za-z0-9]{5,}$", name):
            return render_template(
                "register.html",
                message="Registration failed. Username can only contain letters and numbers and has to be at least 5 characters long.",
            )
        elif name in usernames:
            return render_template(
                "register.html", message="Registration failed. Username already exists."
            )
        elif not bd or age < 18:
            return render_template(
                "register.html",
                message="Registration failed. You must be of age to register.",
            )
        elif not gender:
            return render_template(
                "register.html", message="Registration failed. Please choose gender."
            )
        elif not password or len(password) < 8:
            return render_template(
                "register.html",
                message="Registration failed. Please enter password of at least 8 characters.",
            )
        elif password != confirmation:
            return render_template(
                "register.html", message="Registration failed. Passwords don't match."
            )

        hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
        db.execute(
            "INSERT INTO users (username, birthday, age, sex, hash) VALUES(?, ?, ?, ?, ?)",
            name,
            birthday,
            age,
            gender,
            hash,
        )
        return render_template("login.html")

    else:
        return render_template("register.html")


@app.route("/")
@login_required
def index():
    """Displays a calendar with logged checkups"""

    today = date.today()
    year = today.year
    month = today.month
    allevents = db.execute(
        "SELECT checkup_name, last_checkup, next_checkup FROM checkups JOIN user_checkups ON checkups.id = user_checkups.checkups_id WHERE user_checkups.users_id = ?",
        session["user_id"],
    )

    events = [
        event
        for event in allevents
        if datetime.strptime(event["last_checkup"], "%Y-%m-%d").month == month
        or (
            event["next_checkup"] != ""
            and datetime.strptime(event["next_checkup"], "%Y-%m-%d").month == month
        )
    ]
    c = EventCalendar(events, month, year)
    month = c.formatmonth(year, month)

    return render_template("index.html", month=month)


@app.route("/get-calendar", methods=["POST"])
def get_calendar():
    """Allows the user to check previous and upcoming months"""

    data = request.get_json()
    year = data["year"]
    month = data["month"]
    allevents = db.execute(
        "SELECT checkup_name, last_checkup, next_checkup FROM checkups JOIN user_checkups ON checkups.id = user_checkups.checkups_id WHERE user_checkups.users_id = ?",
        session["user_id"],
    )

    events = [
        event
        for event in allevents
        if datetime.strptime(event["last_checkup"], "%Y-%m-%d").month == month
        or (
            event["next_checkup"] != ""
            and datetime.strptime(event["next_checkup"], "%Y-%m-%d").month == month
        )
    ]
    calendar = EventCalendar(events, month, year)
    new_calendar = calendar.formatmonth(year, month)

    return jsonify(new_calendar=new_calendar)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Logs the user in"""

    session.clear()

    if request.method == "POST":
        if not request.form.get("username") or not request.form.get("password"):
            return render_template(
                "login.html", message="Login failed. Enter username and password."
            )

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return render_template(
                "login.html", message="Login failed. Incorrect username or password."
            )

        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    """Logs the user out"""

    session.clear()
    return redirect("/")


@app.route("/checkups", methods=["GET", "POST"])
@login_required
def checkups():
    """Shows recent medical checkups, allows the user to add checkups and appointments, displays history"""

    if request.method == "GET":
        dates = []
        checkups, checkup_names = checkups_list(session["user_id"])
        today = datetime.today().date()

        for checkup_name in checkup_names:
            checkup_dict = {
                "checkup_name": checkup_name,
                "last_checkup": "",
                "next_checkup": "",
            }
            dates.append(checkup_dict)
            singlecheck = db.execute(
                "SELECT checkup_name, last_checkup, next_checkup FROM checkups JOIN user_checkups ON checkups.id = user_checkups.checkups_id WHERE user_checkups.users_id = ? AND checkups.checkup_name = ? ORDER BY last_checkup DESC LIMIT 1",
                session["user_id"],
                checkup_name,
            )
            if singlecheck:
                for checkup_dict in dates:
                    if checkup_dict["checkup_name"] == checkup_name:
                        checkup_dict["last_checkup"] = singlecheck[0]["last_checkup"]

                        if singlecheck[0]["next_checkup"]:
                            checkup_dict["next_checkup"] = singlecheck[0][
                                "next_checkup"
                            ]

                        else:
                            age = db.execute(
                                "SELECT age FROM users WHERE id = ?", session["user_id"]
                            )[0]["age"]
                            last_checkup = singlecheck[0]["last_checkup"]
                            last_checkup_datetime = datetime.strptime(
                                last_checkup, "%Y-%m-%d"
                            )

                            if age < 50:
                                if checkup_name != "Dental checkup":
                                    standard_recommended = (
                                        last_checkup_datetime + timedelta(days=1095)
                                    )
                                    if standard_recommended.date() < today:
                                        checkup_dict[
                                            "next_checkup"
                                        ] = "Recommended: there was no checkup in more than 3 years. Schedule as soon as possible."
                                    else:
                                        checkup_dict["next_checkup"] = (
                                            "Recommended: "
                                            + standard_recommended.strftime("%Y-%m-%d")
                                        )

                                else:
                                    standard_recommended = (
                                        last_checkup_datetime + timedelta(days=365)
                                    )
                                    if standard_recommended.date() < today:
                                        checkup_dict[
                                            "next_checkup"
                                        ] = "Recommended: there was no checkup in more than 1 years. Schedule as soon as possible."
                                    else:
                                        checkup_dict["next_checkup"] = (
                                            "Recommended: "
                                            + standard_recommended.strftime("%Y-%m-%d")
                                        )

                            elif age >= 50:
                                standard_recommended = (
                                    last_checkup_datetime + timedelta(days=365)
                                )
                                if standard_recommended.date() < today:
                                    checkup_dict[
                                        "next_checkup"
                                    ] = "Recommended: there was no checkup in more than 1 years. Schedule as soon as possible."
                                else:
                                    checkup_dict[
                                        "next_checkup"
                                    ] = "Recommended: " + standard_recommended.strftime(
                                        "%Y-%m-%d"
                                    )

        return render_template(
            "/checkups.html",
            checkups=checkups,
            checkup_names=checkup_names,
            dates=dates,
        )

    if request.method == "POST":
        checkups, checkup_names = checkups_list(session["user_id"])
        action = request.form.get("action")
        checkup = request.form.get("checkup")
        checkup_name = request.form.get("checkupname")
        gender = db.execute("SELECT sex FROM users WHERE id = ?", session["user_id"])[
            0
        ]["sex"]
        birthday = db.execute(
            "SELECT birthday FROM users WHERE id = ?", session["user_id"]
        )[0]["birthday"]
        birthday = datetime.strptime(birthday, "%Y-%m-%d")

        if action == "add":
            if not checkup_name or checkup_name.lower() in (
                name.lower() for name in checkup_names
            ):
                flash(
                    "Checkup not added. Checkup name was missed or checkup already exists."
                )
                return redirect(url_for("checkups"))

            else:
                db.execute(
                    "INSERT INTO checkups (checkup_name, is_preset, for_gender, users_id) VALUES (?, ?, ?, ?)",
                    checkup_name.capitalize(),
                    False,
                    gender,
                    session["user_id"],
                )
                return redirect(url_for("checkups"))

        elif action == "update":
            try:
                if not checkup or not request.form.get("last_checkup"):
                    flash("Pick a checkup and last checkup date to continue.")
                    return redirect(url_for("checkups"))

                elif (
                    datetime.strptime(
                        request.form.get("last_checkup"), "%Y-%m-%d"
                    ).date()
                    > datetime.today().date()
                ):
                    flash("Last checkup date cannot be in the future.")
                    return redirect(url_for("checkups"))

                elif (
                    datetime.strptime(
                        request.form.get("last_checkup"), "%Y-%m-%d"
                    ).date()
                    < birthday.date()
                ):
                    flash("Last checkup date cannot be earlier than your birthday.")
                    return redirect(url_for("checkups"))

                elif request.form.get("next_checkup"):
                    if request.form.get("last_checkup") > request.form.get(
                        "next_checkup"
                    ):
                        flash("Last checkup date cannot be later than next checkup.")
                        return redirect(url_for("checkups"))

                    elif (
                        datetime.strptime(
                            request.form.get("next_checkup"), "%Y-%m-%d"
                        ).date()
                        < datetime.today().date()
                    ):
                        flash("Next checkup date cannot be in the past.")
                        return redirect(url_for("checkups"))

                    else:
                        checkup_id = db.execute(
                            "SELECT id FROM checkups WHERE checkup_name = ?", checkup
                        )[0]["id"]
                        db.execute(
                            "INSERT INTO user_checkups (users_id, checkups_id, last_checkup, next_checkup) VALUES (?, ?, ?, ?)",
                            session["user_id"],
                            checkup_id,
                            request.form.get("last_checkup"),
                            request.form.get("next_checkup"),
                        )
                        return redirect(url_for("checkups"))

                else:
                    checkup_id = db.execute(
                        "SELECT id FROM checkups WHERE checkup_name = ?", checkup
                    )[0]["id"]
                    db.execute(
                        "INSERT INTO user_checkups (users_id, checkups_id, last_checkup, next_checkup) VALUES (?, ?, ?, ?)",
                        session["user_id"],
                        checkup_id,
                        request.form.get("last_checkup"),
                        request.form.get("next_checkup"),
                    )
                    return redirect(url_for("checkups"))

            except ValueError:
                flash("Last and next checkup input has to be a valid date")
                return redirect(url_for("checkups"))

        elif action == "history":
            checkups = db.execute(
                "SELECT user_checkups.id, checkup_name, last_checkup, next_checkup FROM checkups JOIN user_checkups ON checkups.id = user_checkups.checkups_id WHERE user_checkups.users_id = ? ORDER BY last_checkup DESC",
                session["user_id"],
            )
            print(checkups)
            return render_template(
                "/checkups.html", dates=checkups, action=request.form.get("action")
            )

        elif action.startswith("delete-"):
            id = action.split("-")[1]
            db.execute("DELETE FROM user_checkups WHERE id = ?", id)
            checkups = db.execute(
                "SELECT checkup_name, last_checkup, next_checkup FROM checkups JOIN user_checkups ON checkups.id = user_checkups.checkups_id WHERE user_checkups.users_id = ? ORDER BY last_checkup DESC",
                session["user_id"],
            )
            return redirect(url_for("reduced", action="history"))


@app.route("/checkups/<action>")
def reduced(action):
    checkups = db.execute(
        "SELECT user_checkups.id, checkup_name, last_checkup, next_checkup FROM checkups JOIN user_checkups ON checkups.id = user_checkups.checkups_id WHERE user_checkups.users_id = ? ORDER BY last_checkup DESC",
        session["user_id"],
    )
    return render_template("/checkups.html", dates=checkups, action=action)


@app.route("/recommendations", methods=["GET", "POST"])
@login_required
def recommendations():
    """Allows the user to display doctor's recommendations"""

    if request.method == "GET":
        _, checkup_names = checkups_list(session["user_id"])
        advices = db.execute(
            "SELECT recommendation, recommendations.id, checkup_name FROM recommendations JOIN checkups ON recommendations.checkups_id=checkups.id WHERE recommendations.users_id = ?",
            session["user_id"],
        )

        return render_template(
            "/recommendations.html", checkup_names=checkup_names, advices=advices
        )

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            checkup = request.form.get("checkup")
            text = request.form.get("text")

            if not checkup or not text:
                flash("Pick a checkup and type doctor's recommendation.")
                return redirect(url_for("recommendations"))

            checkup_id = db.execute(
                "SELECT id FROM checkups WHERE checkup_name = ?", checkup
            )[0]["id"]
            db.execute(
                "INSERT INTO recommendations (users_id, checkups_id, recommendation) VALUES (?, ?, ?)",
                session["user_id"],
                checkup_id,
                text,
            )
            return redirect(url_for("recommendations"))

        if action.startswith("delete-"):
            id = action.split("-")[1]
            db.execute("DELETE FROM recommendations WHERE id = ?", id)
            return redirect(url_for("recommendations"))
