from config import Config
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask's circular-import idiom: the modules below import `app` from this package
from app import forms, models, routes  # noqa: E402, F401
