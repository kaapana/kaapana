# import os
# import requests
# import base64
# from flask import render_template, redirect, g, Blueprint, request, jsonify, Response, url_for

# from app import app
# from app import db
# from werkzeug.security import generate_password_hash, check_password_hash
# from app.forms import ClientNetworkForm, RemoteNetworkForm # HostNetworkForm, 
# from app.models import ClientNetwork, RemoteNetwork # HostNetwork
# from urllib.parse import urlparse
# from app import login_manager
# from flask_login import login_required

# @login_manager.request_loader
# def load_user_from_request(request):
# # https://gist.github.com/danielfennelly/9a7e9b71c0c38cd124d0862fd93ce217
# # https://flask-login.readthedocs.io/en/latest/#flask_login.login_required
#     # first, try to login using the api_key url arg
#     print(request.args)
#     token = request.args.get('token')
#     print(token)
#     if token:
#         token = base64.b64encode(token.encode()).decode()
#         client_network = ClientNetwork.query.filter_by(token=token).first()
#         if client_network:
#             return client_network

#     # # next, try to login using Basic Auth
#     # token = request.headers.get('FederatedAuthorization')
#     # if token:
#     #     token = token.replace('Basic ', '', 1)
#     #     try:
#     #         token = base64.b64decode(token)
#     #     except TypeError:
#     #         pass
#     #     user = User.query.filter_by(token=token).first()
#     #     if user:
#     #         return user

#     # finally, return None if both methods did not login the user
#     return None

# @app.route('/',  methods=['GET', 'POST'])
# @app.route('/index', methods=['GET', 'POST'])
# def index():
#     hello_world_user = os.environ['HELLO_WORLD_USER']

#     # network_form = HostNetworkForm()
#     # if network_form.validate_on_submit():
#     #     db.session.query(HostNetwork).delete()
#     #     db.session.commit()
#     #     host_network = HostNetwork(
#     #         username=network_form.username.data,
#     #         password=network_form.password.data,
#     #         protocol=network_form.protocol.data,
#     #         host=network_form.host.data,
#     #         port=network_form.port.data,
#     #         client_id=network_form.client_id.data,
#     #         client_secret=network_form.client_secret.data,
#     #         ssl_check=network_form.ssl_check.data)
#     #     db.session.add(host_network)
#     #     db.session.commit()
#     #     return redirect('index')

#     # host_networks = HostNetwork.query.first()

#     client_form = ClientNetworkForm()
#     remote_form = RemoteNetworkForm()

#     client_network = ClientNetwork.query.first()
#     remote_network = RemoteNetwork.query.first()

#     return render_template(
#         'index.html', title='Home', hello_world_user=hello_world_user,
#         client_network=client_network, remote_network=remote_network,
#         client_form=client_form, remote_form=remote_form)

# @app.route("/client-network", methods=['POST'])
# def client_network():
#     client_form = ClientNetworkForm()

#     # Will fail if we run flask run due to the application root! {'csrf_token': ['The CSRF tokens do not match.']}
#     # client_form.validate()
#     # print(client_form.errors)
#     if client_form.validate_on_submit():
#         print('jo')
#         db.session.query(ClientNetwork).delete()
#         db.session.commit()
#         url = urlparse(request.base_url)
#         print(url)
#         client_network = ClientNetwork(
#             token=base64.b64encode(client_form.token.data.encode()).decode(),
#             protocol='https',
#             host=url.hostname,
#             port=url.port or 443,
#             ssl_check=client_form.ssl_check.data)
#         db.session.add(client_network)
#         db.session.commit()
#     return redirect('index')

# @app.route("/remote-network", methods=['POST'])
# def remote_network():
#     remote_form = RemoteNetworkForm()
#     # Will fail if we run flask run due to the application root! {'csrf_token': ['The CSRF tokens do not match.']}
#     # client_form.validate()
#     # print(client_form.errors)
#     if remote_form.validate_on_submit():
#         db.session.query(RemoteNetwork).delete()
#         db.session.commit()
#         remote_network = RemoteNetwork(
#             token=base64.b64encode(remote_form.token.data.encode()).decode(),
#             protocol='https',
#             host=remote_form.host.data,
#             port=remote_form.port.data,
#             ssl_check=remote_form.ssl_check.data)
#         db.session.add(remote_network)
#         db.session.commit()
#     return redirect('index')


# @app.route("/health-check")
# @login_required
# def health_check():
#     return Response(f"Federated backend is up and running!", 200)


# # @app.route("/get-auth-headers")
# # def get_auth_headers():
# #     host_networks = HostNetwork.query.all()
# #     for host_network in host_networks:
# #         pass
# #     print(host_network.username)
# #     payload = {
# #         'username': host_network.username,
# #         'password': host_network.password,
# #         'client_id': host_network.client_id,
# #         'client_secret': host_network.client_secret,
# #         'grant_type': 'password'
# #     }
# #     url = f'{host_network.protocol}://{host_network.host}:{host_network.port}/auth/realms/kaapana/protocol/openid-connect/token'
# #     r = requests.post(url, verify=host_network.ssl_check, data=payload)
# #     access_token = r.json()['access_token']
# #     return jsonify({
# #             'header': {'Authorization': f'Bearer {access_token}'},
# #             'protocol': host_network.protocol,
# #             'host': host_network.host,
# #             'port': host_network.port,
# #             'ssl_check': host_network.ssl_check
# #         })

# @app.route('/trigger-workflow', methods=['POST'])
# @login_required
# def trigger_workflow():
#     data = request.get_json(force=True)
#     resp = requests.post('http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/meta-trigger',  json=data)
#     excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
#     headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
#     response = Response(resp.content, resp.status_code, headers)
#     return response

# @app.route('/minio-presigned-url', methods=['POST'])
# @login_required
# def minio_presigned_url():
#     print(request.form)
#     data = request.form.to_dict()
#     print(data)
#     if data['method'] == 'GET':
#         print(f'http://minio-service.store.svc:9000{data["path"]}')
#         resp = requests.get(f'http://minio-service.store.svc:9000{data["path"]}')
#         excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
#         headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
#         response = Response(resp.content, resp.status_code, headers)
#         return response
#     elif data['method'] == 'PUT':
#         print(f'http://minio-service.store.svc:9000{data["path"]}')
#         file = request.files['file']
#         resp = requests.put(f'http://minio-service.store.svc:9000{data["path"]}', data=file)
#         excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
#         headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
#         print(resp)
#         response = Response(resp.content, resp.status_code, headers)
#         return response