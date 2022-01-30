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

remote = Blueprint('remote', __name__)


@remote.route("/health-check")
@login_required
def health_check():
    return Response(f"Federated backend is up and running!", 200)

@remote.route('/trigger-workflow', methods=['POST'])
@login_required
def trigger_workflow():
    data = request.get_json(force=True)
    resp = requests.post('http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/meta-trigger',  json=data)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    response = Response(resp.content, resp.status_code, headers)
    return response

@remote.route('/minio-presigned-url', methods=['POST'])
@login_required
def minio_presigned_url():
    print(request.form)
    data = request.form.to_dict()
    print(data)
    if data['method'] == 'GET':
        print(f'http://minio-service.store.svc:9000{data["path"]}')
        resp = requests.get(f'http://minio-service.store.svc:9000{data["path"]}')
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)
        return response
    elif data['method'] == 'PUT':
        print(f'http://minio-service.store.svc:9000{data["path"]}')
        file = request.files['file']
        resp = requests.put(f'http://minio-service.store.svc:9000{data["path"]}', data=file)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        print(resp)
        response = Response(resp.content, resp.status_code, headers)
        return response