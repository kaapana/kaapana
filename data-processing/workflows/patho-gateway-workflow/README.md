# Patho Gateway Workflow

Task-API workflow for pathology WSI gateway processing. The workflow fetches WSI files for SlideIDs supplied in the Airflow / Kaapana DagRun conf object, ensures the data is DICOM, keeps a placeholder step for slide label removal, pseudonymizes DICOM metadata, and exports the pseudonymized data to a downstream target.

## DAG

```text
wsi-fetcher
  -> svs-to-dicom
  -> slide-label-remover-dummy
  -> dicom-pseudonymizer
  -> dsf-exporter
```

There is no `slide-id-receiver` task. `wsi-fetcher` reads SlideIDs directly from workflow conf.

## Required Conf

```json
{
  "slide_ids": ["SLIDE_001", "SLIDE_002"]
}
```

The equivalent comma-separated format is also supported:

```json
{
  "slide_ids": "SLIDE_001,SLIDE_002"
}
```

## Optional Conf

```json
{
  "wsi_source": "object-storage",
  "wsi_input_dir": "/object-store",
  "object_storage_endpoint": "object-store.example.org:9000",
  "object_storage_bucket": "pathology-wsi",
  "object_storage_prefix": "",
  "object_storage_access_key": "",
  "object_storage_secret_key": "",
  "object_storage_secure": true,
  "ims_base_url": "https://ims.example.org",
  "ims_get_endpoint": "/get",
  "ims_auth_token": "",
  "pseudonym_mapping_file": "/kaapana/mounted/mapping/mapping.csv",
  "export_target": "/kaapana/mounted/export"
}
```

## Tasks

`wsi-fetcher`

Reads `slide_ids` from DagRun conf, validates that the list is present and non-empty, fetches the requested WSI files, and writes `manifest.json` to the Task-API `wsi` output channel. The default source is `object-storage`, meaning an external S3-compatible object store, not Kaapana's internal MinIO. Each SlideID may resolve to either a file such as `SLIDE_001.svs` or a folder such as `SLIDE_001/`. `REST-ENDPOINT` calls an HTTPS `/get?slide_id=...` endpoint and accepts a direct `.svs`/`.dcm` response or a ZIP containing supported files. `filesystem` is kept for offline tests and local development.

`svs-to-dicom`

Reads `/kaapana/input/wsi` and writes `/kaapana/output/dicom`. SVS files are converted using `wsidicomizer`. Existing DICOM files are moved to the output directory, with copy-and-delete fallback if move fails. Writes `conversion_report.json`.

`slide-label-remover-dummy`

Reads `/kaapana/input/dicom` and writes `/kaapana/output/dicom-label-removed`. This task does not modify DICOM files. It passes DICOM files through unchanged, preferring move over copy, and writes `label_removal_report.json`.

`dicom-pseudonymizer`

Reads `/kaapana/input/dicom-label-removed` and writes `/kaapana/output/dicom-psn`. It uses a mapping CSV with `slide_id,pseudonym` columns and updates DICOM identifiers to the pseudonym. Private tags are removed by default. Writes `pseudonymization_report.json`.

`dsf-exporter`

Reads `/kaapana/input/dicom-psn`, exports files to `export_target`, and writes `/kaapana/output/export-report/export_report.json`.

## Output Reports

- `manifest.json`
- `conversion_report.json`
- `label_removal_report.json`
- `pseudonymization_report.json`
- `export_report.json`

## Offline Tests

The `wsi-fetcher` task can be tested without Airflow or a running Kaapana workflow:

```bash
python3 data-processing/workflows/patho-gateway-workflow/tests/test_fetch_wsi.py
```

The tests use stdlib `unittest`, import `fetch_wsi.py` directly, pass a synthetic output path plus workflow conf object to `main(output, conf)`, and use temporary directories or a mocked external object-store client.

Task API CLI tests are also available:

```bash
python3 data-processing/workflows/patho-gateway-workflow/tests/test_fetch_wsi_task_api_cli.py
```

They validate `processing-container.json` and a generated `task.json` with `python3 -m task_api.cli validate` when the local Task API CLI dependencies are installed. The Docker run test is optional and skipped unless `WSI_FETCHER_IMAGE` points to a built `wsi-fetcher` image:

```bash
WSI_FETCHER_IMAGE=wsi-fetcher:test \
python3 data-processing/workflows/patho-gateway-workflow/tests/test_fetch_wsi_task_api_cli.py
```

## Failure Cases

The workflow fails clearly when:

- `slide_ids` is missing or empty
- a requested SlideID cannot be resolved to a WSI file
- an input file format is unsupported
- SVS conversion fails
- the pseudonym mapping file is missing
- the pseudonym mapping does not contain a SlideID
- DICOM reading fails
- DICOM writing fails
- export fails

## Open TODOs

- production IMS authentication and retry policy
- production object-storage credential and retry policy
- THS / OMI pseudonymization
- real slide-label / barcode removal
- DICOMweb export
- DSF API integration
- final metadata policy for SlideID, nPSN, accession number, and private tags
