from config import Config
from flask import Flask

app = Flask(__name__)
app.config.from_object(Config)

from app import routes
