from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from datetime import timedelta


class SegCheckOperator(KaapanaBaseOperator):
    execution_timeout = timedelta(hours=10)

    def __init__(self,
                 dag,
                 original_img_operator,
                 input_file_extension="*.nii.gz",
                 parallel_processes=1,
                 interpolator=1,  # 0=linear (default), 1=nearest neighbor, 2=sinc (optional), (default: 0), Type: Int
                 max_overlap_percentage=0.003,
                 merge_found_niftis=True,
                 delete_merged_data=True,
                 fail_if_overlap=True,
                 target_dict_operator=None,
                 delete_non_target_labels=False,
                 fail_if_label_already_present=False,
                 fail_if_label_id_not_extractable=False,
                 force_same_labels=False,
                 original_img_batch_name=None,
                 name="seg-check",
                 env_vars={},
                 execution_timeout=execution_timeout,
                 *args,
                 **kwargs
                 ):

        envs = {
            "INPUT_FILE_EXTENSION": str(input_file_extension),
            "ORG_IMG_IN_DIR": str(original_img_operator.operator_out_dir),
            "ORG_IMG_BATCH_NAME": str(original_img_batch_name),
            "THREADS": str(parallel_processes),
            "MAX_OVERLAP": str(max_overlap_percentage),
            "FAIL_IF_OVERLAP": str(fail_if_overlap),
            "FAIL_IF_LABEL_ALREADY_PRESENT": str(fail_if_label_already_present),
            "FAIL_IF_LABEL_ID_NOT_EXTRACTABLE": str(fail_if_label_id_not_extractable),
            "FORCE_SAME_LABELS": str(force_same_labels),
            "DELETE_MERGED_DATA": str(delete_merged_data),
            "MERGE_FOUND_NIFTIS": str(merge_found_niftis),
            "TARGET_DICT_DIR": str(target_dict_operator.operator_out_dir) if target_dict_operator is not None else str(None),
            "DELETE_NON_TARGET_LABELS": str(delete_non_target_labels),
            "INTERPOLATOR": str(interpolator),
        }
        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image=f"{default_registry}/seg-check:0.1.0-vdev",
            name=name,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            env_vars=env_vars,
            ram_mem_mb=40000,
            *args,
            **kwargs
        )
