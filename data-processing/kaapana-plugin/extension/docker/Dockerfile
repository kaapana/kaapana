FROM local-only/dag-installer:latest

LABEL IMAGE="kaapana-plugin"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

COPY files/dags/dag_delete_series_from_platform.py /temp/dags/
COPY files/dags/dag_download_selected_files.py /temp/dags/
COPY files/dags/dag_service_extract_metadata.py /temp/dags/
COPY files/dags/dag_collect_metadata.py /temp/dags/
COPY files/dags/dag_send_dicom.py /temp/dags/
COPY files/dags/dag_service_process_incoming_dcm.py /temp/dags/
COPY files/dags/dag_service_minio_dicom_upload.py /temp/dags/
COPY files/dags/dag_service_reindex_dicom_data.py /temp/dags/
COPY files/dags/dag_tag_dataset.py /temp/dags/
COPY files/dags/dag_tag_seg_ct_tuples.py /temp/dags/
COPY files/dags/dag_tag_train_test_split_dataset.py /temp/dags/
COPY files/dags/dag_service_extract_metadata_trigger_rule.json /temp/dags/
COPY files/dags/dag_service_daily_cleanup_jobs.py /temp/dags/
COPY files/dags/dag_service_segmentation_thumbnail_trigger_rule.json /temp/dags/
COPY files/dags/dag_service_segmentation_thumbnail.py /temp/dags/

COPY files/mounted_scripts/ /temp/mounted_scripts

COPY files/plugin/ /temp/plugins