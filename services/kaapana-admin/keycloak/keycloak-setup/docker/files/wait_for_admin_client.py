"""
initContainer helper for the setup job.

Blocks until the kaapana-admin client can authenticate via client_credentials.
This enforces ordering between the two plain Jobs (bootstrap → setup) without a
Helm hook: the setup container only starts once the bootstrap job has created the
kaapana-admin client.
"""

import os
import sys
import time

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

POLL_INTERVAL_SECONDS = 5
# Bounded wait so a failed bootstrap (e.g. wrong admin password) surfaces as a
# failed Pod instead of hanging forever in Init.
MAX_WAIT_SECONDS = int(os.getenv("ADMIN_CLIENT_WAIT_TIMEOUT", 600))

host = os.environ["KEYCLOAK_HOST"]
port = int(os.getenv("KEYCLOAK_HTTPS_PORT", 443))
secret = os.environ["KAAPANA_ADMIN_CLIENT_SECRET"]
url = f"https://{host}:{port}/auth/realms/master/protocol/openid-connect/token"

waited = 0
while waited < MAX_WAIT_SECONDS:
    try:
        r = requests.post(
            url,
            verify=False,
            data={
                "client_id": "kaapana-admin",
                "client_secret": secret,
                "grant_type": "client_credentials",
            },
            timeout=10,
        )
        if r.status_code == 200:
            print("kaapana-admin client is ready.", flush=True)
            sys.exit(0)
        print(
            f"kaapana-admin client not ready yet (HTTP {r.status_code}); retrying ...",
            flush=True,
        )
    except Exception as e:
        print(f"kaapana-admin client not reachable yet ({e}); retrying ...", flush=True)
    time.sleep(POLL_INTERVAL_SECONDS)
    waited += POLL_INTERVAL_SECONDS

print(
    f"kaapana-admin client never became ready within {MAX_WAIT_SECONDS}s — "
    "bootstrap job likely failed.",
    flush=True,
)
sys.exit(1)
