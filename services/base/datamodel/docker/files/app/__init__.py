from flask import Flask
from app.api.v1 import api_v1
from datamodel import DM

app = Flask(__name__)


DM.setup_db(app)
app.datamodel = DM
app.register_blueprint(api_v1, url_prefix='/api/v1')


from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)