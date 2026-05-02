"""
Page Routes — Serves the HTML pages of the Xnoppo web interface.
"""

from flask import Blueprint, render_template, current_app

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    config = current_app.config["XNOPPO"]
    return render_template("home.html", config=config.to_dict(), active_page="home")


@pages_bp.route("/emby")
def emby_conf():
    config = current_app.config["XNOPPO"]
    return render_template("emby_conf.html", config=config.to_dict(), active_page="emby")


@pages_bp.route("/oppo")
def oppo_conf():
    config = current_app.config["XNOPPO"]
    return render_template("oppo_conf.html", config=config.to_dict(), active_page="oppo")


@pages_bp.route("/libraries")
def lib_conf():
    config = current_app.config["XNOPPO"]
    return render_template("lib_conf.html", config=config.to_dict(), active_page="libraries")


@pages_bp.route("/paths")
def path_conf():
    config = current_app.config["XNOPPO"]
    return render_template("path_conf.html", config=config.to_dict(), active_page="paths")


@pages_bp.route("/tv")
def tv_conf():
    import os
    config = current_app.config["XNOPPO"].to_dict()
    tv_path = current_app.config["BASE_DIR"] / "lib" / "TV"
    if tv_path.exists():
        config["tv_dirs"] = [d for d in os.listdir(tv_path) if os.path.isdir(tv_path / d)]
    return render_template("tv_conf.html", config=config, active_page="tv")


@pages_bp.route("/av")
def av_conf():
    import os
    config = current_app.config["XNOPPO"].to_dict()
    av_path = current_app.config["BASE_DIR"] / "lib" / "AV"
    if av_path.exists():
        config["av_dirs"] = [d for d in os.listdir(av_path) if os.path.isdir(av_path / d)]
    return render_template("av_conf.html", config=config, active_page="av")


@pages_bp.route("/other")
def other_conf():
    config = current_app.config["XNOPPO"]
    return render_template("other_conf.html", config=config.to_dict(), active_page="other")


@pages_bp.route("/status")
def status():
    config = current_app.config["XNOPPO"]
    return render_template("status.html", config=config.to_dict(), active_page="status")


@pages_bp.route("/remote")
def remote():
    config = current_app.config["XNOPPO"]
    return render_template("remote.html", config=config.to_dict(), active_page="remote")


@pages_bp.route("/help")
def help_page():
    config = current_app.config["XNOPPO"]
    return render_template("help.html", config=config.to_dict(), active_page="help")
