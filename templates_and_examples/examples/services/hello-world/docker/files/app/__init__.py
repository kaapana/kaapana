from config import Config
from flask import Flask

app = Flask(__name__)
app.config.from_object(Config)

# Flask's circular-import idiom: the modules below import `app` from this package
from app import routes  # noqa: E402, F401
