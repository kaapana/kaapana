
from datetime import datetime
from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from kaapana.blueprints.kaapana_global_variables import DEFAULT_REGISTRY, KAAPANA_BUILD_VERSION

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
    def __init__(self,
                 dag,
                 name="nrrd2dcmseg",
                 segmentation_in_dir=None,
                 segmentation_operator=None,
                 config_file=None,
                 input_type='single_label_segs',
                 alg_name= None,
                 creator_name="kaapana",
                 alg_type="AUTOMATIC",
                 single_label_seg_info=None,
                 create_multi_label_dcm_from_single_label_segs=False,
                 multi_label_seg_info_json=None,          
                 multi_label_seg_name=None,
                 series_description=None,
                 skip_empty_slices=False,
                 env_vars=None,
                 execution_timeout=timedelta(minutes=90),
                 **kwargs):
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

        """

        if env_vars is None:
            env_vars = {}

        envs = {
            "INPUT_TYPE": input_type,  # multi_label_seg or single_label_segs
            # Relevant if input is single label seg objects or multiple single label seg objects
            "SINGLE_LABEL_SEG_INFO": single_label_seg_info, # SINGLE_LABEL_SEG_INFO must be either "from_file_name" or a e.g. "right@kidney"
            "CREATE_MULIT_LABEL_DCM_FROM_SINGLE_LABEL_SEGS": str(create_multi_label_dcm_from_single_label_segs), # true or false
            # Relevant if input is multilabel seg object
            "MULTI_LABEL_SEG_INFO_JSON": multi_label_seg_info_json, # name of json file inside OPERATOR_IMAGE_LIST_INPUT_DIR that contains the organ seg infos e.g. {"seg_info": ["spleen", "right@kidney"]}
            # Always relevant:
            "MULTI_LABEL_SEG_NAME": multi_label_seg_name,  # Name used for multi-label segmentation object, if it will be created
            # "OPERATOR_IMAGE_LIST_INPUT_DIR":  segmentation_operator.operator_out_dir, # directory that contains segmentaiton objects
            "SERIES_DISCRIPTION": "{}".format(series_description or alg_name or 'UNKOWN SEGMENTATION ALGORITHM'),
            "ALGORITHM_NAME": f'{alg_name or "kaapana"}',
            "CREATOR_NAME": creator_name,
            "ALGORITHM_TYPE": alg_type,
            "SERIES_NUMBER": "300",
            "INSTANCE_NUMBER": "1",
            "SKIP_EMPTY_SLICES": f"{skip_empty_slices}",
            "DCMQI_COMMAND": 'itkimage2segimage'
        }
        env_vars.update(envs)

        if segmentation_operator is None and segmentation_in_dir is not None:
            env_vars['OPERATOR_IMAGE_LIST_INPUT_DIR'] = str(segmentation_in_dir)
        else:
            if segmentation_operator is not None and segmentation_in_dir is None:
                env_vars['OPERATOR_IMAGE_LIST_INPUT_DIR'] = str(segmentation_operator.operator_out_dir)
            else:
                raise NameError('Either segmentation_operator or operator_in_dir has to be set.')
        if config_file:
            env_vars['config_file'] = config_file

        super().__init__(
            dag=dag,
            image=f"{DEFAULT_REGISTRY}/dcmqi:{KAAPANA_BUILD_VERSION}",
            name=name,
            env_vars=env_vars,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            ram_mem_mb=6000,
            ram_mem_mb_lmt=12000,
            **kwargs
            )
