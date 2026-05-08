import argparse
import json
import os
import sys
from pathlib import Path

import requests

# The uploader accepts CI variables in one of three ways (priority):
# 1) --ci-vars-json '<json string>'
# 2) --ci-vars-file /path/to/file.json (JSON or YAML if PyYAML available)
# 3) Fallback: scan environment for variables prefixed with 'CI_' and upload them


def parser():
    p = argparse.ArgumentParser(
        description="Upload CI/CD variables from environment to GitLab project"
    )
    p.add_argument(
        "--api-token",
        help="GitLab API token (or set GITLAB_API_TOKEN env var)",
        default=os.environ.get("GITLAB_API_TOKEN"),
    )
    p.add_argument(
        "--project-id",
        help="GitLab project ID",
        default=os.environ.get("GITLAB_PROJECT_ID"),
    )
    p.add_argument(
        "--gitlab-host",
        help="GitLab host URL",
        default=os.environ.get("GITLAB_URL"),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print variables without uploading",
    )
    p.add_argument(
        "--ci-vars-json",
        help="JSON string of variables to upload (list of {key,value,masked})",
        default=None,
    )
    p.add_argument(
        "--ci-vars-file",
        help="Path to JSON or YAML file containing variables to upload",
        default=None,
    )
    return p.parse_args()


def get_existing_variables(gitlab_host, project_id, api_token):
    """Get list of existing CI variable keys."""
    headers = {"PRIVATE-TOKEN": api_token}
    r = requests.get(
        f"{gitlab_host}/api/v4/projects/{project_id}/variables",
        headers=headers,
    )
    if r.status_code == 200:
        return {var["key"] for var in r.json()}
    return set()


def upload_variable(
    gitlab_host, project_id, api_token, key, value, masked=False, exists=False
):
    """Create or update a CI variable."""
    headers = {"PRIVATE-TOKEN": api_token}
    data = {
        "key": key,
        "value": value,
        "masked": str(masked).lower(),
        "protected": "false",
    }

    if exists:
        # Update existing variable
        r = requests.put(
            f"{gitlab_host}/api/v4/projects/{project_id}/variables/{key}",
            headers=headers,
            data=data,
        )
    else:
        # Create new variable
        r = requests.post(
            f"{gitlab_host}/api/v4/projects/{project_id}/variables",
            headers=headers,
            data=data,
        )

    return r


# --- Helper functions (top-level) -------------------------------------------------
def normalize_entry(entry):
    if isinstance(entry, dict):
        key = entry.get("key")
        value = entry.get("value", "")
        masked = bool(entry.get("masked", False))
        return (key, value, masked)
    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
        key = entry[0]
        value = entry[1]
        masked = bool(entry[2]) if len(entry) >= 3 else False
        return (key, value, masked)
    return None


def load_from_json_string(s):
    try:
        parsed = json.loads(s)
    except Exception as exc:
        print(f"Error parsing --ci-vars-json: {exc}")
        sys.exit(2)
    out = []
    for entry in parsed:
        n = normalize_entry(entry)
        if n and n[1]:
            out.append(n)
    return out


def load_from_file(path):
    fp = Path(path)
    if not fp.exists():
        print(f"Error: ci vars file not found: {path}")
        sys.exit(2)
    text = fp.read_text()
    parsed = None
    try:
        parsed = json.loads(text)
    except Exception:
        try:
            import yaml

            parsed = yaml.safe_load(text)
        except Exception:
            print(
                "Error: ci vars file is not valid JSON and PyYAML is not available or file is invalid"
            )
            sys.exit(2)
    if isinstance(parsed, dict):
        parsed = [
            {
                "key": k,
                "value": v.get("value", v) if isinstance(v, dict) else v,
                "masked": v.get("masked", False) if isinstance(v, dict) else False,
            }
            for k, v in parsed.items()
        ]
    out = []
    for entry in parsed or []:
        n = normalize_entry(entry)
        if n and n[1]:
            out.append(n)
    return out


def scan_env_vars():
    out = []
    for env_k, env_v in os.environ.items():
        if env_k.startswith("CI_") and env_v:
            key = env_k[3:]
            masked = any(t in env_k.upper() for t in ("PASSWORD", "TOKEN", "SECRET"))
            out.append((key, env_v, masked))
    return out

# -------------------------------------------------------------------------------


def main():
    args = parser()

    if not args.api_token:
        print("Error: GitLab API token is required.")
        print("Set GITLAB_API_TOKEN environment variable or use --api-token")
        sys.exit(1)

    if not args.project_id or not args.gitlab_host:
        print("Error: Project ID and GitLab host are required.")
        sys.exit(1)

    print(f"GitLab Host: {args.gitlab_host}")
    print(f"Project ID: {args.project_id}")
    print()

    # Get existing variables
    existing_vars = get_existing_variables(
        args.gitlab_host, args.project_id, args.api_token
    )
    print(f"Found {len(existing_vars)} existing variables in project")
    print()
    # Collect variables using modular functions
    if args.ci_vars_json:
        variables_to_upload = load_from_json_string(args.ci_vars_json)
    elif args.ci_vars_file:
        variables_to_upload = load_from_file(args.ci_vars_file)
    else:
        variables_to_upload = scan_env_vars()

    if args.dry_run:
        print("DRY RUN - Would upload the following variables:")
        for key, value, masked in variables_to_upload:
            display_value = (
                "****" if masked else value[:50] + "..." if len(value) > 50 else value
            )
            action = "UPDATE" if key in existing_vars else "CREATE"
            print(f"  [{action}] {key} = {display_value}")
        return

    # Upload variables
    created = 0
    updated = 0
    failed = 0

    for key, value, masked in variables_to_upload:
        exists = key in existing_vars
        action = "Updating" if exists else "Creating"
        print(f"{action} {key}...", end=" ")

        r = upload_variable(
            args.gitlab_host,
            args.project_id,
            args.api_token,
            key,
            value,
            masked,
            exists,
        )

        if r.status_code in [200, 201]:
            print("OK")
            if exists:
                updated += 1
            else:
                created += 1
        else:
            print(f"FAILED ({r.status_code}: {r.text})")
            failed += 1

    print()
    print(f"Summary: {created} created, {updated} updated, {failed} failed")


if __name__ == "__main__":
    main()
