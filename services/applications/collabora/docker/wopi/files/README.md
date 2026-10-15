# Collabora WOPI backend

FastAPI service in the `kaapana-wopi` image. It serves the documents UI
(`ui/`, see `ui/README.md`), lists a project's office documents in MinIO and
implements the WOPI host that Collabora Online reads and saves them through.

WOPI (Web Application Open Platform Interface) is the protocol browser
office editors use to open and save files kept elsewhere: the editor, here
Collabora, is the WOPI client, and the service owning the files is the WOPI
host. That role gives the image its name, although it also serves the
document list and the UI.

The Collabora pod runs three containers: `collabora` (the editor), `nginx`
(the proxy in front of it that adds the user's token) and `wopi` (this
service). The UI shares the `wopi` container on purpose, so it has the same
origin as the `documents/` and `ws` endpoints it calls.

## Request flow

1. The UI requests `documents/` under `/project/<short_id>/collabora-wopi/`.
   auth-backend adds the `Project` header, and the backend lists the project's
   `s3_bucket` with MinIO credentials it assumes from the user's access token
   (STS `AssumeRoleWithWebIdentity`). MinIO's project policies decide what the
   user may read and write.
2. Each entry links to Collabora with
   `WOPISrc=<WOPI_API_ENDPOINT>/wopi/files/<file_id>`. The file id is the
   url-safe base64 of `<bucket>/<path>`, so it needs no server-side state and
   is unique across buckets.
3. The nginx sidecar of the Collabora pod adds the user's token as
   `access_token` to the editor URL. Collabora calls the WOPI endpoints with it
   directly on the `collabora-chart-wopi` service, and the backend again
   assumes MinIO credentials from that token.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/documents/` | Documents of the project bucket that Collabora can open |
| WebSocket | `/ws` | `{"type": "update"}` to the views of a project after a save |
| `GET` | `/wopi/files/{file_id}` | WOPI CheckFileInfo |
| `GET` | `/wopi/files/{file_id}/contents` | WOPI GetFile, streamed |
| `POST` | `/wopi/files/{file_id}/contents` | WOPI PutFile; `409` with `COOLStatusCode` 1010 if the document changed since Collabora opened it |
| `GET` | `/wopi-discovery/apps` | Apps and actions found by the Collabora discovery |
| `POST` | `/wopi-discovery/apps/update` | Repeat the discovery now |

The discovery runs in the background: every 5 s until Collabora answers, then
every 60 s. A missing or rejected token answers `401`, a bucket the token may
not access `403`.

CheckFileInfo reports `UserCanWrite` the way MinIO decides it: the token's
`policy` claim must hold `consoleAdmin` or `admin_project_<project id>` of the
project that owns the bucket, resolved through AII. Otherwise Collabora opens
the document read-only.

## Configuration

| Variable | Default | |
| --- | --- | --- |
| `COLLABORA_URL` | required | Collabora base URL for the discovery |
| `WOPI_API_ENDPOINT` | `localhost:5000` | WOPI host as Collabora reaches it, without scheme (see `../../collabora/collabora-code-patched`) |
| `MINIO_URL` | required | MinIO host and port, without scheme |
| `AII_URL` | required | Resolves the project of a bucket |
| `DOCUMENT_PATH_IGNORE_REGEX` | `(.*\.minio\.sys)\|(.*thumbnail)` | Object paths to leave out |
| `DEV_MODE` | `false` | Debug logging and permissive CORS |

## Tests

```bash
pip install -r tests/requirements.txt
pytest tests
```

The suite runs in CI as the `collabora-wopi` entry of the `service_tests`
matrix. MinIO is replaced by an in-memory fake.
