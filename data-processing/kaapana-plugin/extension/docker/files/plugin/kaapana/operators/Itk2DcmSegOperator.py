
from datetime import datetime
from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)

def convert_dict_to_env_safe_str(env_dict: dict):
    """
    Converts a dictionary into a string safe for use as an environment variable value.

    Args:
        env_dict (dict): The dictionary to be converted.

    Returns:
        str: A string safe for use as an environment variable value.

    Example:
        # Sample input dictionary
        env_dict = {
            'key1': ('value1', [1, 2, 3]),
            'key2': ('value2', ['a', 'b', 'c']),
            'key3': ('value3', ['x', 'y', 'z']),
        }

        # Output: 'key1=value1:1,2,3;key2=value2:a,b,c;key3=value3:x,y,z'
        convert_dict_to_env_safe_str(env_dict)
    """
    
    sample_key = list(env_dict.keys())[0]
    
    # Check if the value corresponding to the sample key is a tuple
    if isinstance(env_dict[sample_key], tuple):
        # If it's a tuple, process each key-value pair
        temp_dict = {}
        for key, value in env_dict.items():
            tuple_key = value[0]
            tuple_val = str(value[1])
            if isinstance(value[1], list):
                tuple_val = ','.join(map(str, value[1]))
            # Store the processed tuple value in a temporary dictionary tuple key, value separated by a `:`
            temp_dict[key] = f"{tuple_key}:{tuple_val}"

        env_var_value = ";".join([f"{key}={str(value).replace(' ','')}" for key, value in temp_dict.items()])
    else:
        env_var_value =  ";".join([f"{key}={str(value).replace(' ','')}" for key, value in env_dict.items()])
        
    return env_var_value



class Itk2DcmSegOperator(KaapanaBaseOperator):
    """
    Operator converts segmentation data into .dcm segmentation files.

    This operator takes .nrrd segmentation files and creates .dcm segmentation files.
    The operator uses the dcmqi libary.
    For dcmqi documentation please have a look at https://qiicr.gitbook.io/dcmqi-guide/.

    **Inputs:**
    * .nrrd segmentation file

    **Outputs:**
    * .dcm segmentation file
    """

    def __init__(
        self,
        dag,
        segmentation_in_dir=None,
        segmentation_operator=None,
        name="nrrd2dcmseg",
        input_type="single_label_segs",
        alg_name=None,
        creator_name="kaapana",
        alg_type="AUTOMATIC",
        single_label_seg_info=None,
        create_multi_label_dcm_from_single_label_segs=False,
        multi_label_seg_info_json=None,
        multi_label_seg_name=None,
        series_description=None,
        skip_empty_slices=False,
        fail_on_no_segmentation_found=True,
        env_vars=None,
        execution_timeout=timedelta(minutes=90),
        allow_empty_segmentation=True,
        base_nifti_dir=None,
        empty_segmentation_label=99,
        meta_json_props=None,
        seg_attrs_props=None,
        **kwargs,
    ):
        """
        :param segmentation_operator: Operator object used for segmentation
        :param input_type: "multi_label_seg" or "single_label_segs"
           If "multi_label_seg", a json file inside OPERATOR_IMAGE_LIST_INPUT_DIR must exist containing parts as follows {"seg_info": ["spleen", "right@kidney"]}
        :param alg_name: Name of the algorithm
        :param creator_name: Name of the creator
        :param alg_type: Type of the algorithm. Default: "AUTOMATIC"
        :param single_label_seg_info: "from_file_name" or e.g. "right@kidney" or "abdomen"
        :param create_multi_label_dcm_from_single_label_segs: True or False
        :param multi_label_seg_info_json: name of json file inside OPERATOR_IMAGE_LIST_INPUT_DIR that contains the organ seg infos e.g. {"seg_info": ["spleen", "right@kidney"]}
        :param multi_label_seg_name: Name used for multi-label segmentation object, if it will be created
        :param series_description: Description of the series
        :param skip_empty_slices: Whether empty sclices of the series should be skipped. Default: False
        :param env_vars: Environment variables
        :param execution_timeout: max time allowed for the execution of this task instance, if it goes beyond it will raise and fail
        :param base_nifti_dir: nifti directory before the segmentation operator. In case segmentation fails, this operator will create
            an empty nifti using the base nifti from this directory and create an empty segmentation file.
        :param allow_empty_segmentation: handle empty segmentation or empty nifti files
        :param empty_segmentation_label: if allow_empty_segmentation set to True, it will replace the empty segmentation mask label to 
            provided user given label.
        :param meta_json_props: additional meta data json properties as dictionary, will be appended to the newly created meta data json file.
        :param seg_attrs_props: additional segment attributes properties as dictionary where segment label int as key, will be updated and added to the 
            segment attributes of the newly created meta data json file.

        """

        if env_vars is None:
            env_vars = {}

        meta_props_val = ""
        if meta_json_props and isinstance(meta_json_props, dict):
            meta_props_val =  convert_dict_to_env_safe_str(meta_json_props)

        segment_attr_vals = ""
        if seg_attrs_props and isinstance(seg_attrs_props, dict):
            segment_attr_vals = convert_dict_to_env_safe_str(seg_attrs_props)

        envs = {
            "INPUT_TYPE": input_type,  # multi_label_seg or single_label_segs
            # Relevant if input is single label seg objects or multiple single label seg objects
            "SINGLE_LABEL_SEG_INFO": single_label_seg_info,  # SINGLE_LABEL_SEG_INFO must be either "from_file_name" or a e.g. "right@kidney"
            "CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS": str(
                create_multi_label_dcm_from_single_label_segs
            ),  # true or false
            # Relevant if input is multilabel seg object
            "MULTI_LABEL_SEG_INFO_JSON": multi_label_seg_info_json,  # name of json file inside OPERATOR_IMAGE_LIST_INPUT_DIR that contains the organ seg infos e.g. {"seg_info": ["spleen", "right@kidney"]}
            # Always relevant:
            "MULTI_LABEL_SEG_NAME": multi_label_seg_name,  # Name used for multi-label segmentation object, if it will be created
            "FAIL_ON_NO_SEGMENTATION_FOUND": f"{fail_on_no_segmentation_found}",
            # "OPERATOR_IMAGE_LIST_INPUT_DIR":  segmentation_operator.operator_out_dir, # directory that contains segmentaiton objects
            "SERIES_DISCRIPTION": "{}".format(
                series_description or alg_name or "UNKOWN SEGMENTATION ALGORITHM"
            ),
            "ALGORITHM_NAME": f'{alg_name or "kaapana"}',
            "CREATOR_NAME": creator_name,
            "ALGORITHM_TYPE": alg_type,
            "SERIES_NUMBER": "300",
            "INSTANCE_NUMBER": "1",
            "SKIP_EMPTY_SLICES": f"{skip_empty_slices}",
            "DCMQI_COMMAND": "itkimage2segimage",
            "ALLOW_EMPTY_SEGMENTATION": f"{allow_empty_segmentation}",
            "EMPTY_SEGMENTATION_LABEL": f"{empty_segmentation_label}",
            "ADDITIONAL_META_PROPS": f"{meta_props_val}",
            "SEGMENT_ATTRIBUTES_PROPS": f"{segment_attr_vals}",
        }
        env_vars.update(envs)

        if segmentation_operator is None and segmentation_in_dir is not None:
            env_vars["OPERATOR_IMAGE_LIST_INPUT_DIR"] = str(segmentation_in_dir)
        else:
            if segmentation_operator is not None and segmentation_in_dir is None:
                env_vars["OPERATOR_IMAGE_LIST_INPUT_DIR"] = str(
                    segmentation_operator.operator_out_dir
                )
            else:
                raise NameError(
                    "Either segmentation_operator or operator_in_dir has to be set."
                )
        
        if base_nifti_dir:
            env_vars["BASE_NIFTI_DIR"] = str(base_nifti_dir)

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/dcmqi:{KAAPANA_BUILD_VERSION}",
            name=name,
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=6000,
            ram_mem_mb_lmt=12000,
            **kwargs,
        )
