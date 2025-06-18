import csv
import datetime
import subprocess
import urllib
import uuid
from cs50 import SQL

from flask import redirect, render_template, session
from functools import wraps

# Configures CS50 Library to use SQLite database
db = SQL("sqlite:///health.db")


def login_required(f):
    """
    Login Required Decorator:
    https://flask.palletsprojects.com/en/3.0.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def checkups_list(user_id):
    """ Generates a list of checkups for specific user """

    user = db.execute("SELECT username FROM users WHERE id = ?", user_id)[0]["username"]
    gender = db.execute("SELECT sex FROM users WHERE username = ?", user)[0]["sex"]

    if gender == 'e':
        checkups = db.execute("SELECT * FROM checkups WHERE is_preset = ? OR users_id = ?", 1, session["user_id"])
    else:
        checkups = db.execute("SELECT * FROM checkups WHERE (for_gender = ? OR for_gender = ?) AND (is_preset = ? OR users_id = ?)", gender, 'a', 1, session["user_id"])

    checkup_names = [checkup['checkup_name'] for checkup in checkups]

    return checkups, checkup_names
