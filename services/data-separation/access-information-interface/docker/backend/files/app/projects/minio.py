import json
import re

import requests
from fastapi import Request
from kaapanapy.helper import get_minio_client, minio_credentials
from kaapanapy.logger import get_logger

from app.projects.schemas import Project
from app.projects.crud import get_rights

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

    def create_policy(self, policy_name: str, policy: dict):
        """
        Create a policy that corresponds to a right in the access-information-point for the bucket_name.
        This function uses the MinIO Console API to create a policy.
        """
        payload = {"name": policy_name, "policy": json.dumps(policy, indent=4)}
        headers = {"Content-Type": "application/json"}
        headers.update(self.minio_console_header)

        r = requests.post(
            f"{self.minio_console_url}/api/v1/policies",
            headers=headers,
            data=json.dumps(payload),
        )
        r.raise_for_status()

    async def setup_new_project(self, project: Project, session):
        """
        Create a bucket in MinIO for the project as well as policies for different access scopes for this bucket.
        """

        bucket_name = project.s3_bucket
        logger.info(f"Create bucket {bucket_name}")
        try:
            self.minio_client.make_bucket(bucket_name=bucket_name)
        except Exception as e:
            logger.warning(str(e))

        db_rights = await get_rights(session)

        for right in db_rights:
            if not right.claim_key == "policy":
                continue
            claim_value = right.claim_value
            assert claim_value
            policy_name = f"{claim_value}_{project.id}"
            logger.info(f"Create policy for {policy_name=}")
            policy = get_policy_for_role_and_bucket(
                claim_value=claim_value, bucket_name=bucket_name
            )
            self.create_policy(policy_name=policy_name, policy=policy)

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


def get_policy_for_role_and_bucket(claim_value, bucket_name):
    """
    Return the policy object for a role in the access-information-point backend and bucket_name.
    """
    action_by_role = {
        "read_project": ["s3:GetBucketLocation", "s3:GetObject", "s3:ListBucket"],
        "admin_project": [
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
                "Action": action_by_role.get(claim_value),
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
            },
        ],
    }


def is_valid_minio_bucket_name(bucket_name: str) -> bool:
    """
    https://abp.io/docs/latest/framework/infrastructure/blob-storing/minio
    MinIO is the defacto standard for S3 compatibility, So MinIO has some rules for naming bucket. The following rules apply for naming MinIO buckets:
    * Bucket names must be between 3 and 63 characters long.
    * Bucket names can consist only of lowercase letters, numbers, dots (.), and hyphens (-).
    * Bucket names must begin and end with a letter or number.
    * Bucket names must not be formatted as an IP address (for example, 192.168.5.4).
    * Bucket names can't begin with 'xn--'.
    * Bucket names must be unique within a partition.
    * Buckets used with Amazon S3 Transfer Acceleration can't have dots (.) in their names. For more information about transfer acceleration, see Amazon S3 Transfer Acceleration.
    """
    # Check length
    if not (3 <= len(bucket_name) <= 63):
        return False
    # Check allowed characters and no IP address formatting
    if not re.fullmatch(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$", bucket_name):
        return False
    # Ensure it does not resemble an IP address
    if re.match(r"(\d+\.){3}\d+", bucket_name):
        return False
    # Ensure it doesn not begin with 'xn--'
    if bucket_name.startswith("xn--"):
        return False
    return True


def test_is_valid_minio_bucket_name() -> bool:
    # Test the function

    success = True
    test_bucket_names = [
        ("valid-bucket-name", True),
        ("InvalidBucket", False),
        ("bucket-with-dots.", False),
        ("123", True),
        ("192.168.1.1", False),
        ("a" * 64, False),
    ]

    for name_tuple in test_bucket_names:
        valid_response = is_valid_minio_bucket_name(name_tuple[0])
        assert name_tuple[1] == valid_response
        success = name_tuple[1] == valid_response

    return success
