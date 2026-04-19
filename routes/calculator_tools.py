from flask import Blueprint, render_template

bp = Blueprint("calc", __name__)


@bp.route("/calculator")
def calculator():
    return render_template("tools/calculator.html")


@bp.route("/date")
def date_calc():
    return render_template("tools/date_calc.html")


@bp.route("/time-difference")
def time_difference():
    return render_template("tools/time_difference.html")


@bp.route("/pomodoro")
def pomodoro():
    return render_template("tools/pomodoro.html")
