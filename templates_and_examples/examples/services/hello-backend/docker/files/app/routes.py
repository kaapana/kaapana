import os
from flask import render_template, redirect, jsonify
from app import app
from app import db
from app.forms import AddUserForm
from app.models import User


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def index():
    hello_world_user = os.environ["HELLO_WORLD_USER"]
    form = AddUserForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        db.session.add(user)
        db.session.commit()
        return redirect("index")
    users = User.query.all()
    return render_template(
        "index.html",
        title="Home",
        hello_world_user=hello_world_user,
        users=users,
        form=form,
    )
