from kaapanapy.helper import get_minio_client, minio_credentials
from kaapanapy.logger import get_logger
from fastapi import Request
from .schemas import Project
import json
import requests

logger = get_logger(__name__)


def get_minio_helper(request: Request):
    """
    Get an instance of the MinioHelper class that uses the
    x-forwarded-access-token header in the requests to authenticate against MinIO
    """
    access_token = request.headers.get("x-forwarded-access-token")
    return MinioHelper(access_token=access_token)


class MinioHelper:
    """
    Helper class for managing project specific buckets and policies in MinIO.
    """

    def __init__(self, access_token, wait_for_service=True):
        self.access_token = access_token

        self.minio_service_url = "http://minio-service.services.svc:9000"
        self.minio_console_url = "http://minio-service.services.svc:9090"

        if wait_for_service:
            self.wait_for_service()
        else:
            self.minio_client = get_minio_client(access_token)
        self.minio_console_header = self._login_to_minio_console()

    def _login_to_minio_console(self):
        """
        Retrieve a token Cookie for access to the MinIO Console
        """
        access_key_id, secret_access_key, session_token = minio_credentials(
            self.access_token
        )
        payload = {
            "accessKey": access_key_id,
            "secretKey": secret_access_key,
            "sts": session_token,
        }
        r = requests.post(
            f"{self.minio_console_url}/api/v1/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
        )
        logger.info(f"{access_key_id=}, {secret_access_key=},  {session_token=}")
        r.raise_for_status()
        token_cookie = r.headers.get("set-cookie").split(";")[0]
        logger.info(f"{token_cookie=}")
        return {"Cookie": token_cookie}

    def create_project_bucket(self, bucket_name):
        """
        Create a minio bucket.
        """
        self.minio_client.make_bucket(bucket_name=bucket_name)

    def create_policy(self, role, policy_name, bucket_name):
        """
        Create a policy that corresponds to a role in the access-information-point for the bucket_name.
        This function uses the MinIO Console API to create a policy.
        """
        policy = get_policy_for_role_and_bucket(role, bucket_name)
        payload = {"name": policy_name, "policy": json.dumps(policy, indent=4)}
        headers = {"Content-Type": "application/json"}
        headers.update(self.minio_console_header)

        r = requests.post(
            f"{self.minio_console_url}/api/v1/policies",
            headers=headers,
            data=json.dumps(payload),
        )
        r.raise_for_status()

    def setup_new_project(self, project: Project):
        """
        Create a bucket in MinIO for the project as well as policies for different access scopes for this bucket.
        """

        bucket_name = f"project-{project.name}"
        logger.info(f"Create bucket {bucket_name}")
        try:
            self.create_project_bucket(bucket_name=bucket_name)
        except Exception as e:
            logger.warning(str(e))

        for role in ["read", "admin"]:
            policy_name = f"{role}_project_{project.id}"
            logger.info(f"Create {policy_name=} for {role=}")
            self.create_policy(role, policy_name, bucket_name)

    def wait_for_service(self, max_retries=60, delay=5):
        """
        Retry initializing the minio-client.
        """
        import time

        available = False
        tries = 0
        while not available:
            tries += 1
            try:
                self.minio_client = get_minio_client(self.access_token)
                available = True
                logger.info("Minio available")
                return True
            except Exception as e:
                logger.warning(f"Minio not yet available: {str(e)}")
                time.sleep(delay)
                if tries >= max_retries:
                    logger.error(f"Minio not available after {max_retries} retries!")
                    raise e


def get_policy_for_role_and_bucket(role, bucket_name):
    """
    Return the policy object for a role in the access-information-point backend and bucket_name.
    """
    action_by_role = {
        "read": ["s3:GetBucketLocation", "s3:GetObject", "s3:ListBucket"],
        "admin": [
            "s3:ListBucket",
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:GetBucketLocation",
            "s3:GetObject",
        ],
    }

    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": action_by_role.get(role),
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
            },
        ],
    }
