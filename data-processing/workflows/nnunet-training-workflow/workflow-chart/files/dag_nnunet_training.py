from datetime import timedelta

from airflow.models import DAG
from airflow.utils.trigger_rule import TriggerRule
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    INSTANCE_NAME,
    KAAPANA_BUILD_VERSION,
)
from task_api.processing_container import pc_models
from task_api_operators.KaapanaTaskOperator import IOMapping, KaapanaTaskOperator

args = {
    "ui_visible": True,
    "owner": "kaapana",
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}


with DAG("{{ dag_id }}", default_args=args) as dag:
    # download the input seg / rtstruct dataset from kaapana-backend
    download_input = KaapanaTaskOperator(
        task_id="download_input",
        image=f"{DEFAULT_REGISTRY}/get-dicom:{KAAPANA_BUILD_VERSION}",
        taskTemplate="dicom-download",
    )

    # download the ct / mr series referenced by each input seg / rtstruct
    download_ref = KaapanaTaskOperator(
        task_id="download_ref",
        image=f"{DEFAULT_REGISTRY}/get-dicom:{KAAPANA_BUILD_VERSION}",
        taskTemplate="reference-series",
        env=[
            pc_models.BaseEnv(name="SEARCH_POLICY", value="reference_uid"),
            pc_models.BaseEnv(name="PARALLEL_DOWNLOADS", value="5"),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=download_input,
                upstream_output_channel="downloads",
                input_channel="dicom",
            ),
        ],
    )

    # convert dcmseg to nifti using the reference ct / mr for spatial info
    seg_to_nifti = KaapanaTaskOperator(
        task_id="seg_to_nifti",
        image=f"{DEFAULT_REGISTRY}/dcm-mask-converter:{KAAPANA_BUILD_VERSION}",
        taskTemplate="seg-to-nifti",
        iochannel_maps=[
            IOMapping(
                upstream_operator=download_input,
                upstream_output_channel="downloads",
                input_channel="dicom",
            ),
            IOMapping(
                upstream_operator=download_ref,
                upstream_output_channel="downloads",
                input_channel="reference",
            ),
        ],
    )

    # keep or ignore specific labels in the nifti masks
    filter_masks = KaapanaTaskOperator(
        task_id="filter_masks",
        image=f"{DEFAULT_REGISTRY}/mask-processing:{KAAPANA_BUILD_VERSION}",
        taskTemplate="filter-labels",
        env=[
            pc_models.BaseEnv(name="LABEL_FILTER", value=""),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=seg_to_nifti,
                upstream_output_channel="nifti",
                input_channel="masks",
            ),
        ],
    )

    # fuse selected labels into a single new label
    fuse_masks = KaapanaTaskOperator(
        task_id="fuse_masks",
        image=f"{DEFAULT_REGISTRY}/mask-processing:{KAAPANA_BUILD_VERSION}",
        taskTemplate="merge-masks",
        env=[
            pc_models.BaseEnv(name="MERGE_MODE", value="fuse"),
            pc_models.BaseEnv(name="FUSE_LABELS", value=""),
            pc_models.BaseEnv(name="FUSED_LABEL_NAME", value=""),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=filter_masks,
                upstream_output_channel="masks",
                input_channel="masks",
            ),
        ],
        trigger_rule=TriggerRule.ALL_DONE,
    )

    # rename segmentation label names
    rename_labels = KaapanaTaskOperator(
        task_id="rename_labels",
        image=f"{DEFAULT_REGISTRY}/mask-processing:{KAAPANA_BUILD_VERSION}",
        taskTemplate="rename-labels",
        env=[
            pc_models.BaseEnv(name="OLD_LABELS", value=""),
            pc_models.BaseEnv(name="NEW_LABELS", value=""),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=fuse_masks,
                upstream_output_channel="masks",
                input_channel="masks",
            ),
        ],
        trigger_rule=TriggerRule.ALL_DONE,
    )

    # convert the reference dicom series to nifti
    ref_to_nifti = KaapanaTaskOperator(
        task_id="ref_to_nifti",
        image=f"{DEFAULT_REGISTRY}/mitk-tools:{KAAPANA_BUILD_VERSION}",
        taskTemplate="convert-to-nifti",
        env=[
            pc_models.BaseEnv(name="OUTPUT_FORMAT", value="nii.gz"),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=download_ref,
                upstream_output_channel="downloads",
                input_channel="dicom",
            ),
        ],
    )

    # validate masks against the reference nifti (overlap, resampling, label IDs).
    seg_check = KaapanaTaskOperator(
        task_id="seg_check",
        image=f"{DEFAULT_REGISTRY}/seg-check:{KAAPANA_BUILD_VERSION}",
        taskTemplate="seg-check",
        env=[
            pc_models.BaseEnv(name="MAX_OVERLAP_PERCENTAGE", value="0.003"),
            pc_models.BaseEnv(name="FAIL_IF_OVERLAP", value="false"),
            pc_models.BaseEnv(name="FAIL_IF_LABEL_ALREADY_PRESENT", value="false"),
            pc_models.BaseEnv(name="FAIL_IF_LABEL_ID_NOT_EXTRACTABLE", value="false"),
            pc_models.BaseEnv(name="FORCE_SAME_LABELS", value="false"),
            pc_models.BaseEnv(name="DELETE_MERGED_DATA", value="true"),
            pc_models.BaseEnv(name="PARALLEL_PROCESSES", value="3"),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=rename_labels,
                upstream_output_channel="masks",
                input_channel="masks",
            ),
            IOMapping(
                upstream_operator=ref_to_nifti,
                upstream_output_channel="nifti",
                input_channel="reference",
            ),
        ],
    )

    # build the nnunet dataset and run planning + integrity check
    nnunet_preprocess = KaapanaTaskOperator(
        task_id="nnunet_preprocess",
        image=f"{DEFAULT_REGISTRY}/nnunet:{KAAPANA_BUILD_VERSION}",
        taskTemplate="preprocess",
        env=[
            pc_models.BaseEnv(name="PREP_MODALITIES", value="CT"),
            pc_models.BaseEnv(
                name="PLAN_NETWORK_PLANNER", value="nnUNetPlannerResEncM"
            ),
            pc_models.BaseEnv(name="PREP_PREPROCESS", value="True"),
            pc_models.BaseEnv(name="PREP_CHECK_INTEGRITY", value="True"),
            pc_models.BaseEnv(name="PREP_USE_NIFTI_LABELS", value="False"),
            pc_models.BaseEnv(name="PREP_COPY_DATA", value="True"),
            pc_models.BaseEnv(name="PREP_EXIT_ON_ISSUE", value="True"),
            pc_models.BaseEnv(name="INSTANCE_NAME", value=INSTANCE_NAME),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=ref_to_nifti,
                upstream_output_channel="nifti",
                input_channel="images",
            ),
            IOMapping(
                upstream_operator=seg_check,
                upstream_output_channel="checked-masks",
                input_channel="labels",
            ),
        ],
        trigger_rule=TriggerRule.NONE_FAILED,
    )

    # train the nnunet model on the prepared dataset
    nnunet_train = KaapanaTaskOperator(
        task_id="nnunet_train",
        image=f"{DEFAULT_REGISTRY}/nnunet:{KAAPANA_BUILD_VERSION}",
        taskTemplate="train",
        env=[
            pc_models.BaseEnv(name="MODEL", value="3d_fullres"),
            pc_models.BaseEnv(
                name="PLAN_NETWORK_PLANNER", value="nnUNetPlannerResEncM"
            ),
            pc_models.BaseEnv(name="TRAIN_NETWORK_TRAINER", value="nnUNetTrainer"),
            pc_models.BaseEnv(name="TRAIN_FOLD", value="all"),
            pc_models.BaseEnv(name="TRAIN_MAX_EPOCHS", value="1000"),
            pc_models.BaseEnv(name="NUM_BATCHES_PER_EPOCH", value="250"),
            pc_models.BaseEnv(name="NUM_VAL_BATCHES_PER_EPOCH", value="50"),
            pc_models.BaseEnv(name="INITIAL_LEARNING_RATE", value="0.01"),
            pc_models.BaseEnv(name="WEIGHT_DECAY", value="3e-5"),
            pc_models.BaseEnv(name="OVERSAMPLE_FOREGROUND_PERCENT", value="0.33"),
            pc_models.BaseEnv(name="ENABLE_DEEP_SUPERVISION", value="True"),
            pc_models.BaseEnv(name="DISABLE_CHECKPOINTING", value="True"),
            pc_models.BaseEnv(name="INSTANCE_NAME", value=INSTANCE_NAME),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=nnunet_preprocess,
                upstream_output_channel="dataset",
                input_channel="dataset",
            ),
        ],
    )

    # fetch the report-generator notebook from the data api
    get_notebook = KaapanaTaskOperator(
        task_id="get_notebook",
        image=f"{DEFAULT_REGISTRY}/kaapana-data-api:{KAAPANA_BUILD_VERSION}",
        taskTemplate="get",
        env=[
            pc_models.BaseEnv(name="FILE", value="run_generate_nnunet_report.ipynb"),
        ],
    )

    # populate the notebook and produce html & pdf
    generate_report = KaapanaTaskOperator(
        task_id="generate_report",
        image=f"{DEFAULT_REGISTRY}/jupyterlab-reporting:{KAAPANA_BUILD_VERSION}",
        taskTemplate="run-notebook",
        env=[
            pc_models.BaseEnv(
                name="NOTEBOOK_FILENAME", value="run_generate_nnunet_report.ipynb"
            ),
            pc_models.BaseEnv(name="OUTPUT_FORMAT", value="html,pdf"),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=nnunet_train,
                upstream_output_channel="model",
                input_channel="data",
            ),
            IOMapping(
                upstream_operator=get_notebook,
                upstream_output_channel="files",
                input_channel="notebook",
            ),
        ],
    )

    # upload the trained model to the data api
    upload_artifacts = KaapanaTaskOperator(
        task_id="upload_artifacts",
        image=f"{DEFAULT_REGISTRY}/kaapana-data-api:{KAAPANA_BUILD_VERSION}",
        taskTemplate="put",
        env=[],
        iochannel_maps=[
            IOMapping(
                upstream_operator=nnunet_train,
                upstream_output_channel="model",
                input_channel="model",
            ),
        ],
    )

    # upload the report under the "staticwebsiteresults" prefix for the UI page
    upload_report = KaapanaTaskOperator(
        task_id="upload_report",
        image=f"{DEFAULT_REGISTRY}/kaapana-data-api:{KAAPANA_BUILD_VERSION}",
        taskTemplate="put",
        env=[
            pc_models.BaseEnv(name="KEY_PREFIX", value="staticwebsiteresults"),
            pc_models.BaseEnv(name="WHITELISTED_FILE_EXTENSIONS", value=".html,.pdf"),
        ],
        iochannel_maps=[
            IOMapping(
                upstream_operator=generate_report,
                upstream_output_channel="report",
                input_channel="report",
            ),
        ],
    )


# mask preprocessing
(
    download_input
    >> download_ref
    >> seg_to_nifti
    >> filter_masks
    >> fuse_masks
    >> rename_labels
    >> seg_check
)

# ref image conversion
download_ref >> ref_to_nifti >> seg_check

# training
seg_check >> nnunet_preprocess >> nnunet_train

# report export
(
    nnunet_train
    >> get_notebook
    >> generate_report
    >> upload_report
    # >> pdf_to_dicom
    # >> send_pdf_dicom
)

# model export
(
    nnunet_train
    >> upload_artifacts
    # >> binary_to_dicom
    # >> send_model_dicom
)
