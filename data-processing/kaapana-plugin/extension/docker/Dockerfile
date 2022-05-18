FROM local-only/dag-installer:0.1.0

LABEL IMAGE="kaapana-plugin"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

COPY files/dags/dag_delete_series_from_platform.py /tmp/dags/
COPY files/dags/dag_download_selected_files.py /tmp/dags/
COPY files/dags/dag_service_extract_metadata.py /tmp/dags/
COPY files/dags/dag_collect_metadata.py /tmp/dags/
COPY files/dags/dag_send_dicom.py /tmp/dags/
COPY files/dags/dag_service_process_incoming_dcm.py /tmp/dags/
COPY files/dags/dag_service_minio_dicom_upload.py /tmp/dags/
COPY files/dags/dag_service_reindex_dicom_data.py /tmp/dags/
COPY files/dags/dag_tag_dataset.py /tmp/dags/
COPY files/dags/dag_tag_seg_ct_tuples.py /tmp/dags/
COPY files/dags/dag_tag_train_test_split_dataset.py /tmp/dags/
COPY files/dags/dag_service_extract_metadata_trigger_rule.json /tmp/dags/
COPY files/dags/dag_service_daily_cleanup_jobs.py /tmp/dags


COPY files/plugin/ /tmp/plugins