from app import  schemas



def validate_task():


    return True

def workflow(workflow: schemas.WorkflowCreate):
    # validated tasks
    for task in workflow.definition:
        #is_valid = validate_task(task)
        is_valid = validate_task()
        #could also create tasks based on workflow.definition??

    # validate definitions e.g. requiered fields etc.
    return True

def workflow_ui(workflow: schemas.Workflow, ui_schema: schemas.WorkflowUISchemaCreate):
    # validate tasks requiered fields are in ui schema
    #could use taks definition, if tasks are created?
    # or use workflow.definition

    return True

def workflow_run(workflow: schemas.Workflow, ui_schema: schemas.WorkflowUISchema, workflow_run: schemas.WorkflowRunCreate):




    return True
