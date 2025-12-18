export interface Label {
    key: string
    value: string
}

export interface Dataset {
    name: string
    time_created: string
    time_updated: string
    username: string
    identifiers: string[]
}

export enum WorkflowRunStatus {
    CREATED = "Created",
    PENDING = "Pending",
    SCHEDULED = "Scheduled",
    RUNNING = "Running",
    ERROR = "Error",
    COMPLETED = "Completed",
    CANCELED = "Canceled",
}

export enum TaskRunStatus {
    CREATED = "Created",
    PENDING = "Pending",
    SCHEDULED = "Scheduled",
    RUNNING = "Running",
    ERROR = "Error",
    COMPLETED = "Completed",
    SKIPPED = "Skipped",
}

// ##########################
// #### UI Forms #############
// ##########################
export type BaseUIForm = {
    type: string;
    title: string;
    description: string;
    help?: string;
    required?: boolean;
    default?: any;
};

export interface BooleanUIForm extends BaseUIForm {
    type: "bool";
    true_label?: string;
    false_label?: string;
}

export interface IntegerUIForm extends BaseUIForm {
    type: "int";
    minimum?: number;
    maximum?: number;
}

export interface FloatUIForm extends BaseUIForm {
    type: "float";
    minimum?: number;
    maximum?: number;
}

export interface ListUIForm extends BaseUIForm {
    type: "list";
    options?: string[];
    multiselectable?: boolean;
}

export interface StringUIForm extends BaseUIForm {
    type: "str";
    regex_pattern: string;
}

export interface DatasetUIForm extends BaseUIForm {
    type: "dataset";
}

export interface DataEntitiesUIForm extends BaseUIForm {
    type: "data_entity";
    query: string;
    limit: number;
    pagination: boolean;
}

export interface FileUIForm extends BaseUIForm {
    type: "file";
    accept?: string | null;
    multiple?: boolean;
}

export interface TermsUIForm extends BaseUIForm {
    type: "terms";
    terms_text: string;
}

// Union for discriminated UIForm
export type UIForm =
    | BooleanUIForm
    | IntegerUIForm
    | FloatUIForm
    | ListUIForm
    | StringUIForm
    | DatasetUIForm
    | DataEntitiesUIForm
    | FileUIForm
    | TermsUIForm;

// ##########################
// #### WorkflowParameter ###
// ##########################
export interface WorkflowParameter {
    task_title: string;
    env_variable_name: string;
    ui_form: UIForm;
}

// ##########################
// ########## Task ##########
// ##########################
export interface TaskBase {
    display_name?: string
    title: string
    type?: string
}

export interface TaskCreate extends TaskBase {
    downstream_task_titles: string[]
}

export interface Task extends TaskBase {
    id: number
    workflow_id: number
    downstream_task_ids: number[]
}

// ##########################
// ######## Task Run ########
// ##########################

export interface TaskRunBase {
    task_title: string
    lifecycle_status: TaskRunStatus
    external_id: string
}

export interface TaskRunCreate extends TaskRunBase {
    workflow_run_id: number
    task_id: number
}

export interface TaskRun extends TaskRunBase {
    id: number
    task_id: number
    workflow_run_id: number
}

export interface TaskRunUpdate extends TaskRunBase{}

// ##########################
// ######## Workflow ########
// ##########################

export interface WorkflowBase {
    title: string
    definition: string
    workflow_engine: string
    workflow_parameters?: WorkflowParameter[]
    labels: Label[]
}

export interface WorkflowCreate extends WorkflowBase { }

export interface Workflow extends WorkflowBase {
    id: number
    version: number
    created_at: string
}

// ##########################
// ###### Workflow Run ######
// ##########################
export interface WorkflowRef {
    title: string
    version: number
}

export interface WorkflowRunBase {
    workflow: WorkflowRef
    labels: Label[]
    workflow_parameters?: WorkflowParameter[]
}

export interface WorkflowRunUpdate extends WorkflowRunBase { }
export interface WorkflowRunCreate extends WorkflowRunBase { }

export interface WorkflowRun extends WorkflowRunBase {
    id: number
    external_id?: string
    created_at: string
    lifecycle_status: WorkflowRunStatus
    task_runs: TaskRun[]
    updated_at: string
}

