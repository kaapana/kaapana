from typing import Optional, List
import requests
import json
import copy
from fastapi import APIRouter, UploadFile, Response, File, Header, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.dependencies import get_db

from app.experiments import crud
from app.experiments import schemas
from app.experiments.utils import get_dag_list, get_dataset_list


router = APIRouter(tags=["workflow-forms"])

def get_schema(dag_id, ui_form_key, ui_form, ui_dag_info, filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):
    # if ui_form != '$schema':
    default_properties = {}
    if ui_form_key=='workflow_form' and dag_id == 'nnunet-predict':
        ui_form["oneOf"] = []
        selection_properties = {}
        base_properties = {}
        for p_k, p_v in ui_form['properties'].items():
            if 'dependsOn' in p_v:
                p_v.pop('dependsOn')
                selection_properties[p_k] = p_v
            else:
                base_properties[p_k] = p_v
        base_properties.pop('task')   
        
        for task in ui_form['properties']['task']['enum']:
            task_selection_properties = copy.deepcopy(selection_properties)
            for p_k, p_v in task_selection_properties.items():
                p_v['default'] = ui_dag_info[task][p_k]
            task_selection_properties.update({
                "task":
                {
                    "type": "string",
                    "const": task
                }
            })
            ui_form["oneOf"].append({
                "type": 'object',
                "title": task,
                "properties": task_selection_properties})
        ui_form["properties"] = base_properties

    if ui_form_key=='publication_form':
        pass
    if ui_form_key=='opensearch_form':
        if filter_kaapana_instances.remote is False:
            datasets = get_dataset_list(unique_sets=True)
        else:
            db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=filter_kaapana_instances)
            datasets = set.intersection(*map(set,[json.loads(ki.allowed_datasets) for ki in db_remote_kaapana_instances]))
        default_properties = {
            "dataset": {
                "type": "string",
                "title": "Dataset tag",
                "enum": [""] + list(datasets)
            },
            "index": {
                "type": "string",
                "title": "Index",
                "default": "meta-index",
                "readOnly": True,
            },
            "cohort_limit": {
                "type": "integer",
                "title": "Cohort Limit"
            },
            "single_execution": {
                "type": "boolean",
                "title": "Single execution",
                "description": "Whether your report is execute in single mode or not"
            }
        }
    if ui_form_key == 'external_schema_federated_form':
        default_properties = {
            "federated_bucket": {
                "type": "string",
                "title": "Federated bucket",
                "description": "Bucket to which the files should be saved to",
                "readOnly": True
            },
            "federated_dir": {
                "type": "string",
                "title": "Federated directory",
                "description": "Directory to which the files should be saved to",
                "readOnly": True
            },
            "federated_operators": {
                "type": "array",
                "title": "Operators for which the results should be saved",
                "items": {
                    "type": "string"
                },
                "readOnly": True
            },
            "skip_operators": {
                "type": "array",
                "title": "Operators that should not be executed",
                "items": {
                    "type": "string"
                },
                "readOnly": True
            },
            "federated_round": {
                "type": "integer",
                "title": "Federated round",
                "readOnly": True
            },
            "federated_total_rounds": {
                "type": "integer",
                "title": "Federated total rounds"
            }
        }
    if 'properties' in ui_form:
        for k, v in ui_form['properties'].items():
            if v == "$default":
                ui_form['properties'][k] = default_properties[k]
    return ui_form

   

@router.post("/get-ui-form-schemas")
async def ui_form_schemas(filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):
    dag_id = filter_kaapana_instances.dag_id
    schema_data = {}
    if dag_id is None: 
        return JSONResponse(content=schema_data)
    if filter_kaapana_instances.remote is False:
        dags = get_dag_list(only_dag_names=False)
        # datasets = get_dataset_list(unique_sets=True)
    else:
        db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=filter_kaapana_instances)
        # datasets = set.intersection(*map(set,[json.loads(ki.allowed_datasets) for ki in db_remote_kaapana_instances]))
        in_common_dags_set = set.intersection(*map(set, [[k for k, v in json.loads(ki.allowed_dags).items()] for ki in db_remote_kaapana_instances ]))
        dags = {}
        for el in in_common_dags_set:
            dags.update({el: json.loads(db_remote_kaapana_instances[0].allowed_dags)[el]})

    if dag_id not in dags:
        raise HTTPException(status_code=404, detail=f"Dag {dag_id} is not part of the allowed dags, please add it!")
    dag = dags[dag_id]
    if 'ui_forms' in dag:
        for ui_form_key, ui_form in dag['ui_forms'].items():
            ui_dag_info = dag['ui_dag_info'] if 'ui_dag_info' in dag else None
            schema_data[ui_form_key] = get_schema(dag_id, ui_form_key, ui_form, ui_dag_info, filter_kaapana_instances, db)
    return JSONResponse(content=schema_data)


# @router.post("/get-opensearch-schema")
# async def opensearch_schema(filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):
#     return JSONResponse(content=get_schema('opensearch', filter_kaapana_instances, db))

# @router.post("/get-federated-schema")
# async def federated_schema(filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):
#     if filter_kaapana_instances.remote is False:
#         datasets = get_dataset_list(unique_sets=True)
#     else:
#         db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=filter_kaapana_instances)
#         datasets = set.intersection(*map(set,[json.loads(ki.allowed_datasets) for ki in db_remote_kaapana_instances]))

#     return JSONResponse(content={
#       "type": "object",
#       "properties": {
#         "dataset": {
#             "type": "string",
#             "title": "Dataset tag",
#             "enum": [""] + list(datasets)
#         },
#         "index": {
#           "type": "string",
#           "title": "Index",
#           "default": "meta-index",
#           "readOnly": True,
#         },
#         "cohort_limit": {
#           "type": "integer",
#           "title": "Cohort Limit"
#         }
#       }
#     })

# @router.post("/get-workflow-schema")
# async def workflow_schema(filter_kaapana_instances: schemas.FilterKaapanaInstances = None, db: Session = Depends(get_db)):
#     return JSONResponse(content=get_schema('workflow', filter_kaapana_instances, db))
