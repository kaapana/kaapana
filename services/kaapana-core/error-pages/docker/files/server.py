from flask import Flask
from flask import render_template
from flask import request
# creates a Flask application, named app
app = Flask(__name__)

# a route where we will display a welcome message via an HTML template


@app.route("/50x")
def error_50x():
    host = str(str(request.host))
    return render_template('50x.html.html', host=host)


@app.route("/400")
def error_400():
    host = str(str(request.host))
    return render_template('400.html', host=host)


@app.route("/401")
def error_401():
    host = str(str(request.host))
    return render_template('401.html', host=host)


@app.route("/402")
def error_402():
    host = str(str(request.host))
    return render_template('402.html', host=host)


@app.route("/403")
def error_403():
    host = str(str(request.host))
    return render_template('403.html', host=host)


@app.route("/404")
def error_404():
    host = str(str(request.host))
    print("host: %s" % host)
    return render_template('404-hack.html', host=host)


@app.route("/405")
def error_405():
    host = str(str(request.host))
    return render_template('405.html', host=host)


@app.route("/406")
def error_406():
    host = str(str(request.host))
    return render_template('406.html', host=host)


@app.route("/407")
def error_407():
    host = str(str(request.host))
    return render_template('407.html', host=host)


@app.route("/408")
def error_408():
    host = str(str(request.host))
    return render_template('408.html', host=host)


@app.route("/409")
def error_409():
    host = str(str(request.host))
    return render_template('409.html', host=host)


@app.route("/410")
def error_410():
    host = str(str(request.host))
    return render_template('410.html', host=host)


@app.route("/414")
def error_414():
    host = str(str(request.host))
    return render_template('414.html', host=host)


@app.route("/416")
def error_416():
    host = str(str(request.host))
    return render_template('416.html', host=host)


@app.route("/418")
def error_418():
    host = str(str(request.host))
    return render_template('418.html', host=host)


@app.route("/426")
def error_426():
    host = str(str(request.host))
    return render_template('426.html', host=host)


@app.route("/451")
def error_451():
    host = str(str(request.host))
    return render_template('451.html', host=host)


@app.route("/500")
def error_500():
    host = str(str(request.host))
    return render_template('500.html', host=host)


@app.route("/501")
def error_501():
    host = str(str(request.host))
    return render_template('501.html', host=host)


@app.route("/502")
def error_502():
    host = str(str(request.host))
    return render_template('502.html', host=host)


@app.route("/503")
def error_503():
    host = str(str(request.host))
    return render_template('503.html', host=host)


@app.route("/504")
def error_504():
    host = str(str(request.host))
    return render_template('504.html', host=host)


@app.route("/505")
def error_505():
    host = str(str(request.host))
    return render_template('505.html', host=host)


@app.route("/506")
def error_506():
    host = str(str(request.host))
    return render_template('506.html', host=host)


@app.route("/507")
def error_507():
    host = str(str(request.host))
    return render_template('507.html', host=host)


@app.route("/508")
def error_508():
    host = str(str(request.host))
    return render_template('508.html', host=host)


@app.route("/510")
def error_510():
    host = str(str(request.host))
    return render_template('510.html', host=host)


@app.route("/511")
def error_511():
    host = str(str(request.host))
    return render_template('511.html', host=host)


@app.route("/")
def index():
    host = str(str(request.host))
    return render_template('index.html', host=host)


# run the application
if __name__ == "__main__":
    app.run(port=5000, host='0.0.0.0')
