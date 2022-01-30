import base64

from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask import redirect, url_for

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin.index'


from app.admin.routes import admin
from app.remote.routes import remote

app.register_blueprint(admin)
app.register_blueprint(remote, url_prefix='/remote')
# from app import routes
from app.models import ClientNetwork, RemoteNetwork

@login_manager.request_loader
def load_user_from_request(request):
# https://gist.github.com/danielfennelly/9a7e9b71c0c38cd124d0862fd93ce217
# https://flask-login.readthedocs.io/en/latest/#flask_login.login_required
# https://www.digitalocean.com/community/tutorials/how-to-add-authentication-to-your-app-with-flask-login
    # first, try to login using the api_key url arg
    # print(request.args)
    # token = request.args.get('token')
    # print(token)
    # if token:
    #     token = base64.b64encode(token.encode()).decode()
    #     client_network = ClientNetwork.query.filter_by(token=token).first()
    #     if client_network:
    #         return client_network

    # # next, try to login using Basic Auth
    token = request.headers.get('FederatedAuthorization')
    print(token)
    if token:
        token = base64.b64encode(token.encode()).decode()
        client_network = ClientNetwork.query.filter_by(token=token).first()
        if client_network:
            return client_network

    # finally, return None if both methods did not login the user
    return None

@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('admin.index'), code=302)

@app.shell_context_processor
def make_shell_context():
    return {'ClientNetwork': ClientNetwork, 'RemoteNetwork': RemoteNetwork}