FROM local-only/base-installer:latest

LABEL IMAGE="kaapana-plugin"
LABEL VERSION="0.1.1"
LABEL BUILD_IGNORE="False"

COPY files/dags/dag_clear_validation_results.py /kaapana/tmp/dags/
COPY files/dags/dag_collect_metadata.py /kaapana/tmp/dags/
COPY files/dags/dag_convert_niftis_to_dicoms_and_import_to_pacs.py /kaapana/tmp/dags/
COPY files/dags/dag_delete_series.py /kaapana/tmp/dags/
COPY files/dags/dag_download_selected_files.py /kaapana/tmp/dags/
COPY files/dags/dag_generate_thumbnail.py /kaapana/tmp/dags/
COPY files/dags/dag_import_dicoms_in_zip_to_internal_pacs.py /kaapana/tmp/dags/
COPY files/dags/dag_segmentation_evaluation.py /kaapana/tmp/dags/
COPY files/dags/dag_send_dicom.py /kaapana/tmp/dags/
COPY files/dags/dag_service_daily_cleanup_jobs.py /kaapana/tmp/dags/
COPY files/dags/dag_service_process_incoming_dcm.py /kaapana/tmp/dags/
COPY files/dags/dag_service_reindex_dicom_data.py /kaapana/tmp/dags/
COPY files/dags/dag_service_send_email.py /kaapana/tmp/dags/
COPY files/dags/dag_tag_dataset.py /kaapana/tmp/dags/
COPY files/dags/dag_tag_seg_ct_tuples.py /kaapana/tmp/dags/
COPY files/dags/dag_tag_train_test_split_dataset.py /kaapana/tmp/dags/
COPY files/dags/dag_validate_dicoms.py /kaapana/tmp/dags/
COPY files/dags/dag_project_dicom_transfer.py /kaapana/tmp/dags
COPY files/dags/dag_project_minio_transfer.py /kaapana/tmp/dags

COPY files/mounted_scripts/ /kaapana/tmp/mounted_scripts

COPY files/plugin/ /kaapana/tmp/plugins