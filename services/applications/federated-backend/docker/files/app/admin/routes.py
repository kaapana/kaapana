import os
import json
import uuid
from cryptography.fernet import Fernet
from flask import render_template, redirect, g, Blueprint, request, jsonify, Response, url_for
from flask import Blueprint, render_template


from app import app
from app import db

from app.forms import ClientNetworkForm, RemoteNetworkForm
from app.models import ClientNetwork, RemoteNetwork
from urllib.parse import urlparse


admin = Blueprint('admin', __name__)

@admin.route('/',  methods=['GET', 'POST'])
@admin.route('/index', methods=['GET', 'POST'])
def index():
    node_id = os.environ['NODE_ID']

    client_form = ClientNetworkForm()
    remote_form = RemoteNetworkForm()

    client_network = ClientNetwork.query.first()
    remote_network = RemoteNetwork.query.first()
    if client_network and client_network.allowed_dags is not None:
        client_network.allowed_dags = ", ".join(json.loads(client_network.allowed_dags))
    if client_network and client_network.allowed_datasets is not None:
        client_network.allowed_datasets = ", ".join(json.loads(client_network.allowed_datasets))
    return render_template(
        'index.html', title='Home', node_id=node_id,
        client_network=client_network, remote_network=remote_network,
        client_form=client_form, remote_form=remote_form)

@admin.route("/client-network", methods=['POST'])
def client_network():
    client_form = ClientNetworkForm()

    # Will fail if we run flask run due to the application root! {'csrf_token': ['The CSRF tokens do not match.']}
    # client_form.validate()
    # print(client_form.errors)
    if client_form.validate_on_submit():
        db.session.query(ClientNetwork).delete()
        db.session.commit()
        if client_form.fernet_encrypted.data is True:
            fernet_key=Fernet.generate_key().decode()
        else:
            fernet_key='deactivated'
        url = urlparse(request.base_url)
        client_network = ClientNetwork(
            token=str(uuid.uuid4()),
            protocol='https',
            host=url.hostname,
            port=url.port or 443,
            ssl_check=client_form.ssl_check.data,
            fernet_key=fernet_key,
            allowed_dags=json.dumps(client_form.allowed_dags.data),
            allowed_datasets=json.dumps(client_form.allowed_datasets.data),
        )
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
            'ssl_check': client_network.ssl_check,
            'fernet_key': client_network.fernet_key
        })

@admin.route("/remote-network", methods=['POST'])
def remote_network():
    remote_form = RemoteNetworkForm()
    # Will fail if we run flask run due to the application root! {'csrf_token': ['The CSRF tokens do not match.']}
    # remote_form.validate()
    # print(remote_form.errors)
    if remote_form.validate_on_submit():
        db.session.query(RemoteNetwork).delete()
        db.session.commit()
        remote_network = RemoteNetwork(
            token=remote_form.token.data,
            protocol='https',
            host=remote_form.host.data,
            port=remote_form.port.data,
            ssl_check=remote_form.ssl_check.data,
            fernet_key=remote_form.fernet_key.data or 'deactivated'
        )
        db.session.add(remote_network)
        db.session.commit()
    return redirect('index')

@app.route("/get-remote-network")
def get_remote_network():
    remote_network = RemoteNetwork.query.first()
    return jsonify({
            'headers': {'FederatedAuthorization': f'{remote_network.token}'},
            'protocol': remote_network.protocol,
            'host': remote_network.host,
            'port': remote_network.port,
            'ssl_check': remote_network.ssl_check,
            'fernet_key': remote_network.fernet_key
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