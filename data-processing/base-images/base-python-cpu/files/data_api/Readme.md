# data_api — async client SDK for the Kaapana Data API & Storage API

`data_api` is the **single programmatic gate** to the Kaapana Data API for Python
callers (operators, processing containers, backend services). It ships two async
clients built on `httpx.AsyncClient`:

- **`DataClient`** — entities & metadata: query / index / get-entity /
  resolve-dataset-members, plus writes (create entity, register metadata schema,
  attach metadata, upload artifact).
- **`StorageClient`** — store-agnostic bulk download: stream the storage-api tar
  archive and unpack it as `<entity_id>/<files>`, with a completeness check.

## Configuration (environment)

Both clients derive in-cluster defaults from the environment (no kaapanapy
dependency); pass `base_url`/`access_token` explicitly to override.

| Variable | Used for | Default |
|---|---|---|
| `KAAPANA_DATA_API_URL` | Data API base URL | `http://data-api.<ns>.svc/v1` |
| `KAAPANA_STORAGE_API_URL` | Storage API base URL | `http://storage-api.<ns>.svc` |
| `KAAPANA_SERVICES_NAMESPACE` / `SERVICES_NAMESPACE` | `<ns>` above | `services` |

An `access_token` (when given) is sent as `Authorization: Bearer` and
`x-forwarded-access-token` — forward-ready for when the Data API gains auth.

## Usage

```python
import asyncio
from data_api import DataClient, StorageClient

async def main(token):
    async with DataClient(access_token=token) as data, \
               StorageClient(access_token=token) as storage:
        # select entities that carry a model, then materialise them on disk
        ids = await data.query_index(where={
            "type": "filter", "op": "has_key", "field": "metadata.model",
        })
        await storage.download_entities(ids, "/home/kaapana/downloads", data_client=data)

asyncio.run(main(token))
```

Writing entities (e.g. an ingestion operator):

```python
async with DataClient() as data:
    await data.register_metadata_schema("dicom-series", schema)
    await data.create_entity({"id": eid, "storage_coordinates": [...], "metadata": [...]})
    await data.attach_metadata(eid, "permissions", {"project": pid, "owner": None})
    await data.upload_artifact(eid, "dicom-series", "thumbnail", png_bytes,
                               content_type="image/png")
```

Sync callers (Airflow PythonOperator tasks, CLIs) wrap the async entry point with
`asyncio.run(...)`.

## Tests

```bash
pip install -e ".[test]"
pytest data_api
```
