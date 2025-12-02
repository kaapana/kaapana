import os
from flask import render_template, Response
from app import app


@app.route("/")
@app.route("/index")
def index():
    hello_world_user = os.environ["HELLO_WORLD_USER"]
    return render_template(
        "index.html", title="Home", hello_world_user=hello_world_user
    )


@app.route("/metrics", methods=["GET"])
def metrics():
    hello_world_user = os.environ.get("HELLO_WORLD_USER", "unknown").replace('"', '\\"')
    metrics_output = (
        "\n".join(
            [
                "# HELP hello_world_app_info Basic metadata about the hello-world app.",
                "# TYPE hello_world_app_info gauge",
                f'hello_world_app_info{{user="{hello_world_user}"}} 1',
            ]
        )
        + "\n"
    )
    return Response(metrics_output, mimetype="text/plain")
