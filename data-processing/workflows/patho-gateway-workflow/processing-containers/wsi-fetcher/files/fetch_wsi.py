#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_WSI_INPUT_DIR = Path("/object-store")
SUPPORTED_EXTENSIONS = [".svs", ".dcm"]

try:
    from kaapanapy.logger import get_logger

    logger = get_logger(__name__)
except Exception:
    logger = None


def log(message):
    if logger:
        logger.info(message)
    else:
        print(message, flush=True)


def fail(message):
    raise RuntimeError(message)


def load_workflow_conf():
    try:
        from kaapanapy.helper import load_workflow_config

        return load_workflow_config()
    except Exception as exc:
        log(f"Could not load Kaapana workflow config via helper: {exc}")

    # Local/offline execution fallback. Kaapana normally provides
    # WORKFLOW_DIR/conf/conf.json and kaapanapy.helper.load_workflow_config().
    for env_name in ("WORKFLOW_CONFIG_PATH", "KAAPANA_WORKFLOW_CONFIG"):
        value = os.getenv(env_name)
        if value and Path(value).is_file():
            with Path(value).open() as f:
                return json.load(f)

    workflow_dir = os.getenv("WORKFLOW_DIR")
    if workflow_dir:
        config_path = Path(workflow_dir) / "conf" / "conf.json"
        if config_path.is_file():
            with config_path.open() as f:
                return json.load(f)

    return {}


def get_conf_value(conf, key, default=None):
    if key in conf:
        return conf[key]
    workflow_form = conf.get("workflow_form") or {}
    if key in workflow_form:
        return workflow_form[key]
    upper_key = key.upper()
    if upper_key in workflow_form:
        return workflow_form[upper_key]
    return os.getenv(upper_key, default)


def parse_slide_ids(value):
    if value is None:
        fail("Required DagRun conf field 'slide_ids' is missing.")
    if isinstance(value, str):
        slide_ids = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        slide_ids = [str(item).strip() for item in value if str(item).strip()]
    else:
        fail("'slide_ids' must be either a non-empty list or a comma-separated string.")
    if not slide_ids:
        fail("Required DagRun conf field 'slide_ids' is empty.")
    return slide_ids


def detect_format(path):
    suffix = path.suffix.lower().lstrip(".")
    if suffix == "dicom":
        return "dicom"
    return suffix


def write_manifest(output_dir, items):
    report_path = output_dir / "manifest.json"
    with report_path.open("w") as f:
        json.dump({"items": items}, f, indent=2)
    return report_path


def unique_target(output_dir, filename):
    target = output_dir / filename
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    index = 1
    while True:
        candidate = output_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def resolve_filesystem_wsi(input_dir, slide_id):
    exact_candidates = []
    for extension in SUPPORTED_EXTENSIONS:
        exact_candidates.extend(
            [
                input_dir / f"{slide_id}{extension}",
                input_dir / f"{slide_id}{extension.upper()}",
            ]
        )
    for candidate in exact_candidates:
        if candidate.is_file():
            return [candidate]

    slide_dir = input_dir / slide_id
    if slide_dir.is_dir():
        matches = [
            path
            for path in sorted(slide_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if matches:
            return matches

    matches = [
        path
        for path in sorted(input_dir.rglob("*"))
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and (path.stem == slide_id or path.name.startswith(f"{slide_id}."))
    ]
    if not matches:
        fail(
            f"SlideID '{slide_id}' could not be resolved to a WSI file under {input_dir}."
        )
    return matches


def fetch_from_filesystem(slide_ids, conf, output_dir):
    input_dir = Path(get_conf_value(conf, "wsi_input_dir", DEFAULT_WSI_INPUT_DIR))
    log(f"Input directory: {input_dir}")
    if not input_dir.is_dir():
        fail(f"Configured wsi_input_dir does not exist or is not a directory: {input_dir}")

    items = []
    for slide_id in slide_ids:
        for source_file in resolve_filesystem_wsi(input_dir, slide_id):
            target_file = unique_target(output_dir, source_file.name)
            log(f"{slide_id}: fetching {source_file} -> {target_file}")
            shutil.copy2(source_file, target_file)
            items.append(
                {
                    "slide_id": slide_id,
                    "local_filename": target_file.name,
                    "source": "filesystem",
                    "detected_format": detect_format(target_file),
                }
            )
    return items


def get_external_object_store_client(conf):
    try:
        from minio import Minio
    except Exception as exc:
        fail(f"External object-store source requires the minio Python package: {exc}")

    endpoint = get_conf_value(conf, "object_storage_endpoint")
    access_key = get_conf_value(conf, "object_storage_access_key")
    secret_key = get_conf_value(conf, "object_storage_secret_key")
    secure = str(get_conf_value(conf, "object_storage_secure", "true")).lower() == "true"
    if not endpoint or not access_key or not secret_key:
        fail(
            "External object-storage source requires object_storage_endpoint, "
            "object_storage_access_key, and object_storage_secret_key."
        )
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def normalize_prefix(*parts):
    return "/".join(str(part).strip("/") for part in parts if str(part).strip("/"))


def list_minio_objects(client, bucket, prefix):
    return [
        item.object_name
        for item in client.list_objects(bucket, prefix=prefix, recursive=True)
        if not getattr(item, "is_dir", False)
    ]


def resolve_object_keys(client, bucket, prefix, slide_id):
    candidates = []
    for extension in SUPPORTED_EXTENSIONS:
        candidates.append(normalize_prefix(prefix, f"{slide_id}{extension}"))
        candidates.append(normalize_prefix(prefix, f"{slide_id}{extension.upper()}"))

    found = []
    for candidate in candidates:
        try:
            client.stat_object(bucket, candidate)
            found.append(candidate)
        except Exception:
            pass

    folder_prefix = normalize_prefix(prefix, slide_id)
    for object_name in list_minio_objects(client, bucket, folder_prefix):
        name = Path(object_name).name
        if Path(name).suffix.lower() in SUPPORTED_EXTENSIONS and (
            Path(name).stem == slide_id
            or name.startswith(f"{slide_id}.")
            or object_name.startswith(f"{folder_prefix}/")
        ):
            found.append(object_name)

    found = sorted(set(found))
    if not found:
        fail(
            f"SlideID '{slide_id}' could not be resolved in object-storage "
            f"bucket '{bucket}' with prefix '{prefix}'."
        )
    return found


def fetch_from_object_storage(slide_ids, conf, output_dir):
    bucket = get_conf_value(conf, "object_storage_bucket", "pathology-wsi")
    prefix = get_conf_value(conf, "object_storage_prefix", "")
    if not bucket:
        fail("object_storage_bucket is required for object-storage WSI retrieval.")

    client = get_external_object_store_client(conf)
    items = []
    log(f"External object-storage endpoint: {get_conf_value(conf, 'object_storage_endpoint')}")
    log(f"Object-storage bucket: {bucket}")
    log(f"Object-storage prefix: {prefix}")
    for slide_id in slide_ids:
        for object_key in resolve_object_keys(client, bucket, prefix, slide_id):
            target_file = unique_target(output_dir, Path(object_key).name)
            log(f"{slide_id}: downloading s3://{bucket}/{object_key} -> {target_file}")
            client.fget_object(bucket, object_key, str(target_file))
            items.append(
                {
                    "slide_id": slide_id,
                    "local_filename": target_file.name,
                    "source": "object-storage",
                    "detected_format": detect_format(target_file),
                }
            )
    return items


def filename_from_response(response, slide_id):
    content_disposition = response.headers.get("Content-Disposition", "")
    for part in content_disposition.split(";"):
        part = part.strip()
        if part.startswith("filename="):
            return part.split("=", 1)[1].strip('"')

    content_type = response.headers.get("Content-Type", "")
    if "dicom" in content_type.lower():
        return f"{slide_id}.dcm"
    return f"{slide_id}.svs"


def copy_supported_zip_members(zip_path, output_dir, slide_id):
    items = []
    with zipfile.ZipFile(zip_path) as archive:
        members = [
            member
            for member in archive.namelist()
            if not member.endswith("/")
            and Path(member).suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if not members:
            fail(f"IMS response ZIP for SlideID '{slide_id}' contained no supported WSI files.")
        for member in members:
            target_file = unique_target(output_dir, Path(member).name)
            log(f"{slide_id}: extracting {member} -> {target_file}")
            with archive.open(member) as source, target_file.open("wb") as target:
                shutil.copyfileobj(source, target)
            items.append(
                {
                    "slide_id": slide_id,
                    "local_filename": target_file.name,
                    "source": "ims-rest",
                    "detected_format": detect_format(target_file),
                }
            )
    return items


def fetch_from_ims_rest(slide_ids, conf, output_dir):
    base_url = get_conf_value(conf, "ims_base_url")
    endpoint = get_conf_value(conf, "ims_get_endpoint", "/get")
    token = get_conf_value(conf, "ims_auth_token")
    if not base_url:
        fail("ims_base_url is required for ims-rest WSI retrieval.")

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    items = []
    for slide_id in slide_ids:
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}?{urlencode({'slide_id': slide_id})}"
        log(f"{slide_id}: requesting {url}")
        request = Request(url, headers=headers)
        with urlopen(request, timeout=300) as response:
            filename = filename_from_response(response, slide_id)
            with TemporaryDirectory() as tmp_dir:
                tmp_file = Path(tmp_dir) / filename
                with tmp_file.open("wb") as f:
                    shutil.copyfileobj(response, f)

                if zipfile.is_zipfile(tmp_file):
                    items.extend(copy_supported_zip_members(tmp_file, output_dir, slide_id))
                elif tmp_file.suffix.lower() in SUPPORTED_EXTENSIONS:
                    target_file = unique_target(output_dir, tmp_file.name)
                    shutil.move(str(tmp_file), target_file)
                    items.append(
                        {
                            "slide_id": slide_id,
                            "local_filename": target_file.name,
                            "source": "ims-rest",
                            "detected_format": detect_format(target_file),
                        }
                    )
                else:
                    fail(
                        f"IMS response for SlideID '{slide_id}' has unsupported file "
                        f"format: {tmp_file.name}"
                    )
    return items


def fetch_wsi(slide_ids, conf, output_dir):
    source = str(get_conf_value(conf, "wsi_source", "object-storage")).lower()
    if source in ("object-storage", "object_storage", "s3"):
        return fetch_from_object_storage(slide_ids, conf, output_dir)
    if source in ("ims-rest", "rest-endpoint", "rest_endpoint"):
        return fetch_from_ims_rest(slide_ids, conf, output_dir)
    if source == "filesystem":
        return fetch_from_filesystem(slide_ids, conf, output_dir)
    fail(
        f"Unsupported wsi_source '{source}'. Supported values are "
        "object-storage, REST-ENDPOINT, and filesystem."
    )


def main(output, conf=None):
    conf = conf if conf is not None else load_workflow_conf()
    slide_ids = parse_slide_ids(get_conf_value(conf, "slide_ids"))
    output_dir = Path(output)

    log(f"Output directory: {output_dir}")
    log(f"Slide IDs requested: {len(slide_ids)}")
    output_dir.mkdir(parents=True, exist_ok=True)

    items = fetch_wsi(slide_ids, conf, output_dir)
    report_path = write_manifest(output_dir, items)
    log(f"Files found: {len(items)}")
    log(f"Files written: {len(items)}")
    log(f"Final report path: {report_path}")


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(
            description="Fetch WSI files for SlideIDs from the Kaapana workflow conf."
        )
        parser.add_argument(
            "-o",
            "--output",
            required=True,
            help="Output directory for the wsi Task-API channel.",
        )
        args = parser.parse_args()

        main(args.output)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
