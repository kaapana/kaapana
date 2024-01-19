#!/usr/bin/env python3
import os
import sys
import boto3
import base64
import json
import argparse
import logging
from kubernetes import client, config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_ecr_token(region, aws_access_key_id, aws_secret_access_key, aws_session_token):
    """
    Fetches the ECR token from AWS.
    """
    try:
        ecr_client = boto3.client(
            'ecr',
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token
        )
        response = ecr_client.get_authorization_token()
        token = response['authorizationData'][0]['authorizationToken']
        decoded_token = base64.b64decode(token).decode()
        logging.info("Successfully retrieved ECR token.")
        return decoded_token.split(':')[1]
    except Exception as e:
        logging.error(f"Error fetching ECR token: {e}")
        raise

def update_k8s_secret(secret_name, namespace, token, server):
    """
    Updates or creates a Kubernetes secret with the new ECR token.
    """
    try:
        config.load_kube_config()
        api_instance = client.CoreV1Api()

        secret_data = {
            ".dockerconfigjson": base64.b64encode(json.dumps({
                "auths": {
                    server: {
                        "username": "AWS",
                        "password": token
                    }
                }
            }).encode()).decode()
        }

        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(name=secret_name),
            data=secret_data,
            type="kubernetes.io/dockerconfigjson"
        )

        api_instance.replace_namespaced_secret(secret_name, namespace, secret)
        logging.info(f"Secret '{secret_name}' updated successfully.")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            api_instance.create_namespaced_secret(namespace, secret)
            logging.info(f"Secret '{secret_name}' created successfully.")
        else:
            logging.error(f"Error updating Kubernetes secret: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description='Update Kubernetes secret with AWS ECR credentials.')
    parser.add_argument('--region', help='AWS region')
    parser.add_argument('--secret-name', help='Kubernetes secret name')
    parser.add_argument('--namespace', help='Kubernetes namespace')
    parser.add_argument('--server', help='ECR server URL')
    parser.add_argument('--aws-access-key-id', help='AWS Access Key ID')
    parser.add_argument('--aws-secret-access-key', help='AWS Secret Access Key')
    parser.add_argument('--aws-session-token', help='AWS Session Token (optional)')

    args = parser.parse_args()

    region = args.region or os.environ.get('AWS_REGION')
    secret_name = args.secret_name or os.environ.get('K8S_SECRET_NAME')
    namespace = args.namespace or os.environ.get('K8S_NAMESPACE')
    server = args.server or os.environ.get('ECR_SERVER_URL')
    aws_access_key_id = args.aws_access_key_id or os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = args.aws_secret_access_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    aws_session_token = args.aws_session_token or os.environ.get('AWS_SESSION_TOKEN')

    if not all([region, secret_name, namespace, server, aws_access_key_id, aws_secret_access_key]):
        logging.error("Some required arguments or environment variables are missing.")
        return

    try:
        token = get_ecr_token(region, aws_access_key_id, aws_secret_access_key, aws_session_token)
        update_k8s_secret(secret_name, namespace, token, server)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
