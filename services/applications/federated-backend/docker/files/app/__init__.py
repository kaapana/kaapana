import base64

from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask import redirect, url_for
from elasticsearch import Elasticsearch


app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin.index'

_elastichost = "elastic-meta-service.meta.svc:9200"
es = Elasticsearch(hosts=_elastichost)


from app.admin.routes import admin
from app.remote.routes import remote
from app.models import ClientNetwork, RemoteNetwork

app.register_blueprint(admin)
app.register_blueprint(remote, url_prefix='/remote')


@login_manager.request_loader
def load_user_from_request(request):
    # https://gist.github.com/danielfennelly/9a7e9b71c0c38cd124d0862fd93ce217
    # https://flask-login.readthedocs.io/en/latest/#flask_login.login_required
    # https://www.digitalocean.com/community/tutorials/how-to-add-authentication-to-your-app-with-flask-login
    token = request.headers.get('FederatedAuthorization')
    if token:
        client_network = ClientNetwork.query.filter_by(token=token).first()
        if client_network:
            return client_network
    return None


@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('admin.index'), code=302)


@app.shell_context_processor
def make_shell_context():
    return {'ClientNetwork': ClientNetwork, 'RemoteNetwork': RemoteNetwork}