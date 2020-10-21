from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime


from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalDagTriggerOperator import LocalDagTriggerOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

from shapemodel.OrganSegmentationOperator import OrganSegmentationOperator
log = LoggingMixin().log

ui_forms = {
    "publication_form": {
        "title": "1",
        "type": "object",
        "properties": {
            "title": {
                "title": "Title",
                "default": "3D Statistical Shape Models Incorporating Landmark-Wise Random Regression Forests for Omni-Directional Landmark Detection",
                "description": "3D Statistical Shape Models Incorporating Landmark-Wise Random Regression Forests for Omni-Directional Landmark Detection",
                "type": "string",
                "readOnly": True,
            },
            "authors": {
                "title": "Authors",
                "default": "Tobias Norajitra; Klaus H. Maier-Hein",
                "description": "Tobias Norajitra; Klaus H. Maier-Hein",
                "type": "string",
                "readOnly": True,
            },
            "doi": {
                "title": "DOI",
                "default": "10.1109/TMI.2016.2600502",
                "description": "DOI",
                "type": "string",
                "readOnly": True,
            },
            "link": {
                "title": "Link",
                "default": "https://ieeexplore.ieee.org/document/7544533",
                "description": "https://ieeexplore.ieee.org/document/7544533",
                "type": "string",
                "readOnly": True,
            },
            "confirmation": {
                "title": "Accept",
                "default": False,
                "description": "I will cite the publication if applicable.",
                "type": "boolean",
                "readOnly": True,
                "required": True,
            }
        }
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "body_part": {
                "title": "Body Part",
                "default": "abdomen",
                "description": "Body part, which needs to be present in the image.",
                "type": "string",
                "readOnly": True,
            },
            "input": {
                "title": "Input",
                "default": "CT",
                "description": "Input-data modality",
                "type": "string",
                "readOnly": True,
            },
            "target": {
                "title": "Targets",
                "default": "Liver, Spleen, Left-Kidney, Right-Kidney",
                "description": "Liver, Spleen, Left-Kidney, Right-Kidney",
                "type": "string",
                "readOnly": True,
            }
        }
    }
}

args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='shapemodel-organ-seg',
    default_args=args,
    schedule_interval=None,
    concurrency=40,
    max_active_runs=30
    )

get_input = LocalGetInputDataOperator(dag=dag)

# Convert DICOM to NRRD
dcm2nrrd = DcmConverterOperator(dag=dag, output_format='nrrd')

# Segment organs
organSeg_unityCS = OrganSegmentationOperator(
    dag=dag, input_operator=dcm2nrrd, mode="unityCS")

organSeg_liver = OrganSegmentationOperator(
    dag=dag, input_operator=organSeg_unityCS, mode="Liver")
organSeg_spleen = OrganSegmentationOperator(
    dag=dag, input_operator=organSeg_unityCS, mode="Spleen")
organSeg_kidney_right = OrganSegmentationOperator(
    dag=dag, input_operator=organSeg_unityCS, mode="RightKidney", spleen_operator=organSeg_spleen)
organSeg_kidney_left = OrganSegmentationOperator(
    dag=dag, input_operator=organSeg_unityCS, mode="LeftKidney", spleen_operator=organSeg_spleen)


# Convert NRRD segmentations to DICOM segmentation objects
alg_name = organSeg_unityCS.image.split("/")[-1]
nrrd2dcmSeg_liver = Itk2DcmSegOperator(dag=dag, segmentation_operator=organSeg_liver, single_label_seg_info="Liver",
                                       parallel_id='liver', alg_name=alg_name, series_description=f'{alg_name} - Liver')
nrrd2dcmSeg_spleen = Itk2DcmSegOperator(dag=dag, segmentation_operator=organSeg_spleen, single_label_seg_info="Spleen",
                                        parallel_id='spleen', alg_name=alg_name, series_description=f'{alg_name} - Spleen')
nrrd2dcmSeg_kidney_right = Itk2DcmSegOperator(dag=dag, segmentation_operator=organSeg_kidney_right,
                                              single_label_seg_info="Right@Kidney", parallel_id='kidney-right',
                                              alg_name=alg_name, series_description=f'{alg_name} - Kidney-Right')
nrrd2dcmSeg_kidney_left = Itk2DcmSegOperator(dag=dag, segmentation_operator=organSeg_kidney_left,
                                             single_label_seg_info="Left@Kidney", parallel_id='kidney-left',
                                             alg_name=alg_name, series_description=f'{alg_name} - Kidney-Left')

# Send DICOM segmentation objects to pacs
dcmseg_send_liver = DcmSendOperator(dag=dag, input_operator=nrrd2dcmSeg_liver)
dcmseg_send_spleen = DcmSendOperator(dag=dag, input_operator=nrrd2dcmSeg_spleen)
dcmseg_send_kidney_right = DcmWebSendOperator(dag=dag, input_operator=nrrd2dcmSeg_kidney_right)
dcmseg_send_kidney_left = DcmWebSendOperator(dag=dag, input_operator=nrrd2dcmSeg_kidney_left)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)

get_input >> dcm2nrrd >> organSeg_unityCS

organSeg_unityCS >> organSeg_liver >> nrrd2dcmSeg_liver >> dcmseg_send_liver >> clean
organSeg_unityCS >> organSeg_spleen >> nrrd2dcmSeg_spleen >> dcmseg_send_spleen >> clean
organSeg_spleen >> organSeg_kidney_right >> nrrd2dcmSeg_kidney_right >> dcmseg_send_kidney_right >> clean
organSeg_spleen >> organSeg_kidney_left >> nrrd2dcmSeg_kidney_left >> dcmseg_send_kidney_left >> clean
