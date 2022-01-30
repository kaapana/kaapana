import os
import requests
import base64
from flask import render_template, redirect, g, Blueprint, request, jsonify, Response, url_for
from flask import Blueprint, render_template

from app import app
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from app.forms import ClientNetworkForm, RemoteNetworkForm # HostNetworkForm, 
from app.models import ClientNetwork, RemoteNetwork # HostNetwork
from urllib.parse import urlparse
from app import login_manager
from flask_login import login_required

admin = Blueprint('admin', __name__)

@admin.route('/',  methods=['GET', 'POST'])
@admin.route('/index', methods=['GET', 'POST'])
def index():
    hello_world_user = os.environ['HELLO_WORLD_USER']

    client_form = ClientNetworkForm()
    remote_form = RemoteNetworkForm()

    client_network = ClientNetwork.query.first()
    remote_network = RemoteNetwork.query.first()

    return render_template(
        'index.html', title='Home', hello_world_user=hello_world_user,
        client_network=client_network, remote_network=remote_network,
        client_form=client_form, remote_form=remote_form)

@admin.route("/client-network", methods=['POST'])
def client_network():
    client_form = ClientNetworkForm()

    # Will fail if we run flask run due to the application root! {'csrf_token': ['The CSRF tokens do not match.']}
    # client_form.validate()
    # print(client_form.errors)
    if client_form.validate_on_submit():
        print('jo')
        db.session.query(ClientNetwork).delete()
        db.session.commit()
        url = urlparse(request.base_url)
        print(url)
        client_network = ClientNetwork(
            token=base64.b64encode(client_form.token.data.encode()).decode(),
            protocol='https',
            host=url.hostname,
            port=url.port or 443,
            ssl_check=client_form.ssl_check.data)
        db.session.add(client_network)
        db.session.commit()
    return redirect('index')

@app.route("/get-client-network")
def get_client_network():
    client_network = ClientNetwork.query.first()
    return jsonify({
            'header': {'FederatedAuthorization': f'{client_network.token}'},
            'protocol': client_network.protocol,
            'host': client_network.host,
            'port': client_network.port,
            'ssl_check': client_network.ssl_check
        })

@admin.route("/remote-network", methods=['POST'])
def remote_network():
    remote_form = RemoteNetworkForm()
    # Will fail if we run flask run due to the application root! {'csrf_token': ['The CSRF tokens do not match.']}
    # client_form.validate()
    # print(client_form.errors)
    if remote_form.validate_on_submit():
        db.session.query(RemoteNetwork).delete()
        db.session.commit()
        remote_network = RemoteNetwork(
            token=base64.b64encode(remote_form.token.data.encode()).decode(),
            protocol='https',
            host=remote_form.host.data,
            port=remote_form.port.data,
            ssl_check=remote_form.ssl_check.data)
        db.session.add(remote_network)
        db.session.commit()
    return redirect('index')

@app.route("/get-remote-network")
def get_remote_network():
    remote_network = RemoteNetwork.query.first()
    return jsonify({
            'header': {'FederatedAuthorization': f'{remote_network.token}'},
            'protocol': remote_network.protocol,
            'host': remote_network.host,
            'port': remote_network.port,
            'ssl_check': remote_network.ssl_check
        })


# network_form = HostNetworkForm()
# if network_form.validate_on_submit():
#     db.session.query(HostNetwork).delete()
#     db.session.commit()
#     host_network = HostNetwork(
#         username=network_form.username.data,
#         password=network_form.password.data,
#         protocol=network_form.protocol.data,
#         host=network_form.host.data,
#         port=network_form.port.data,
#         client_id=network_form.client_id.data,
#         client_secret=network_form.client_secret.data,
#         ssl_check=network_form.ssl_check.data)
#     db.session.add(host_network)
#     db.session.commit()
#     return redirect('index')

# @app.route("/get-auth-headers")
# def get_auth_headers():
#     host_networks = HostNetwork.query.all()
#     for host_network in host_networks:
#         pass
#     print(host_network.username)
#     payload = {
#         'username': host_network.username,
#         'password': host_network.password,
#         'client_id': host_network.client_id,
#         'client_secret': host_network.client_secret,
#         'grant_type': 'password'
#     }
#     url = f'{host_network.protocol}://{host_network.host}:{host_network.port}/auth/realms/kaapana/protocol/openid-connect/token'
#     r = requests.post(url, verify=host_network.ssl_check, data=payload)
#     access_token = r.json()['access_token']
#     return jsonify({
#             'header': {'Authorization': f'Bearer {access_token}'},
#             'protocol': host_network.protocol,
#             'host': host_network.host,
#             'port': host_network.port,
#             'ssl_check': host_network.ssl_check
#         })