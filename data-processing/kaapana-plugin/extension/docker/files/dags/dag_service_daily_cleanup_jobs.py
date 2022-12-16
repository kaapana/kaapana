from kaapana.operators.LocalServiceSyncDagsDbOperator import LocalServiceSyncDagsDbOperator
from kaapana.operators.LocalCleanUpExpiredWorkflowDataOperator import LocalCleanUpExpiredWorkflowDataOperator
from kaapana.operators.LocalCtpQuarantineCheckOperator import LocalCtpQuarantineCheckOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from datetime import timedelta
import logging
import os
import jinja2
from airflow.configuration import conf
from airflow.models import DAG, Variable
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago


log = LoggingMixin().log


START_DATE = days_ago(-1)

args = {
    'ui_visible': False,
    'owner': 'system',
    'depends_on_past': False,
    'start_date': START_DATE,
    'retries': 0,
    'retry_delay': timedelta(minutes=1)
}

dag = DAG(
    dag_id='service-daily-cleanup-jobs',
    default_args=args,
    schedule_interval="@daily",
    start_date=args["start_date"],
    concurrency=1,
    max_active_runs=1,
    tags=['service'],
    template_undefined=jinja2.Undefined
)

remove_delete_dags = LocalServiceSyncDagsDbOperator(dag=dag, retries=3, retry_delay=timedelta(minutes=2))
remove_delete_dags

clean_up = LocalCleanUpExpiredWorkflowDataOperator(dag=dag, expired_period=timedelta(days=14))
clean_up
check_ctp_quarantine = LocalCtpQuarantineCheckOperator(dag=dag)
check_ctp_quarantine

# airflow-log-cleanup
"""
A maintenance workflow that you can deploy into Airflow to periodically clean
out the task logs to avoid those getting too big.
airflow trigger_dag --conf '[curly-braces]"maxLogAgeInDays":30[curly-braces]' airflow-log-cleanup
--conf options:
    maxLogAgeInDays:<INT> - Optional
https://github.com/teamclairvoyant/airflow-maintenance-dags/blob/master/log-cleanup/airflow-log-cleanup.py
---
following changes: Only clean scheduler logs:
    1. removed BASE_LOG_FOLDER from DIRECTORIES_TO_DELETE = []
    2 ENABLE_DELETE_CHILD_LOG = Variable.get("airflow_log_cleanup__enable_delete_child_log", "True"
    3 set             pool='default_pool',
            executor_config={
                "cpu_millicores": 100,
                "ram_mem_mb": 50,
                "gpu_mem_mb": 0
            },
)
"""
"""
A maintenance workflow that you can deploy into Airflow to periodically clean
out the task logs to avoid those getting too big.
airflow trigger_dag --conf '[curly-braces]"maxLogAgeInDays":30[curly-braces]' airflow-log-cleanup
--conf options:
    maxLogAgeInDays:<INT> - Optional
"""
DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
try:
    BASE_LOG_FOLDER = conf.get("core", "BASE_LOG_FOLDER").rstrip("/")
except Exception as e:
    BASE_LOG_FOLDER = conf.get("logging", "BASE_LOG_FOLDER").rstrip("/")
# How often to Run. @daily - Once a day at Midnight
SCHEDULE_INTERVAL = "@daily"
# List of email address to send email alerts to if this job fails
ALERT_EMAIL_ADDRESSES = []
# Length to retain the log files if not already provided in the conf. If this
# is set to 30, the job will remove those files that are 30 days old or older
DEFAULT_MAX_LOG_AGE_IN_DAYS = Variable.get(
    "airflow_log_cleanup__max_log_age_in_days", 30
)
# Whether the job should delete the logs or not. Included if you want to
# temporarily avoid deleting the logs
ENABLE_DELETE = True
# The number of worker nodes you have in Airflow. Will attempt to run this
# process for however many workers there are so that each worker gets its
# logs cleared.
NUMBER_OF_WORKERS = 1
DIRECTORIES_TO_DELETE = []
ENABLE_DELETE_CHILD_LOG = Variable.get(
    "airflow_log_cleanup__enable_delete_child_log", "True"
)
LOG_CLEANUP_PROCESS_LOCK_FILE = "/tmp/airflow_log_cleanup_worker.lock"
logging.info("ENABLE_DELETE_CHILD_LOG  " + ENABLE_DELETE_CHILD_LOG)

if not BASE_LOG_FOLDER or BASE_LOG_FOLDER.strip() == "":
    raise ValueError(
        "BASE_LOG_FOLDER variable is empty in airflow.cfg. It can be found "
        "under the [core] (<2.0.0) section or [logging] (>=2.0.0) in the cfg file. "
        "Kindly provide an appropriate directory path."
    )

if ENABLE_DELETE_CHILD_LOG.lower() == "true":
    try:
        CHILD_PROCESS_LOG_DIRECTORY = conf.get(
            "scheduler", "CHILD_PROCESS_LOG_DIRECTORY"
        )
        if CHILD_PROCESS_LOG_DIRECTORY != ' ':
            DIRECTORIES_TO_DELETE.append(CHILD_PROCESS_LOG_DIRECTORY)
    except Exception as e:
        logging.exception(
            "Could not obtain CHILD_PROCESS_LOG_DIRECTORY from " +
            "Airflow Configurations: " + str(e)
        )

if hasattr(dag, 'doc_md'):
    dag.doc_md = __doc__
if hasattr(dag, 'catchup'):
    dag.catchup = False

start = DummyOperator(
    task_id='start',
    dag=dag)

log_cleanup = """

echo "Getting Configurations..."
BASE_LOG_FOLDER="{{params.directory}}"
WORKER_SLEEP_TIME="{{params.sleep_time}}"

sleep ${WORKER_SLEEP_TIME}s

MAX_LOG_AGE_IN_DAYS="{{dag_run.conf.maxLogAgeInDays}}"
if [ "${MAX_LOG_AGE_IN_DAYS}" == "" ]; then
    echo "maxLogAgeInDays conf variable isn't included. Using Default '""" + str(DEFAULT_MAX_LOG_AGE_IN_DAYS) + """'."
    MAX_LOG_AGE_IN_DAYS='""" + str(DEFAULT_MAX_LOG_AGE_IN_DAYS) + """'
fi
ENABLE_DELETE=""" + str("true" if ENABLE_DELETE else "false") + """
echo "Finished Getting Configurations"
echo ""

echo "Configurations:"
echo "BASE_LOG_FOLDER:      '${BASE_LOG_FOLDER}'"
echo "MAX_LOG_AGE_IN_DAYS:  '${MAX_LOG_AGE_IN_DAYS}'"
echo "ENABLE_DELETE:        '${ENABLE_DELETE}'"

cleanup() {
    echo "Executing Find Statement: $1"
    FILES_MARKED_FOR_DELETE=`eval $1`
    echo "Process will be Deleting the following File(s)/Directory(s):"
    echo "${FILES_MARKED_FOR_DELETE}"
    echo "Process will be Deleting `echo "${FILES_MARKED_FOR_DELETE}" | \
    grep -v '^$' | wc -l` File(s)/Directory(s)"     \
    # "grep -v '^$'" - removes empty lines.
    # "wc -l" - Counts the number of lines
    echo ""
    if [ "${ENABLE_DELETE}" == "true" ];
    then
        if [ "${FILES_MARKED_FOR_DELETE}" != "" ];
        then
            echo "Executing Delete Statement: $2"
            eval $2
            DELETE_STMT_EXIT_CODE=$?
            if [ "${DELETE_STMT_EXIT_CODE}" != "0" ]; then
                echo "Delete process failed with exit code \
                    '${DELETE_STMT_EXIT_CODE}'"

                echo "Removing lock file..."
                rm -f """ + str(LOG_CLEANUP_PROCESS_LOCK_FILE) + """
                if [ "${REMOVE_LOCK_FILE_EXIT_CODE}" != "0" ]; then
                    echo "Error removing the lock file. \
                    Check file permissions.\
                    To re-run the DAG, ensure that the lock file has been \
                    deleted (""" + str(LOG_CLEANUP_PROCESS_LOCK_FILE) + """)."
                    exit ${REMOVE_LOCK_FILE_EXIT_CODE}
                fi
                exit ${DELETE_STMT_EXIT_CODE}
            fi
        else
            echo "WARN: No File(s)/Directory(s) to Delete"
        fi
    else
        echo "WARN: You're opted to skip deleting the File(s)/Directory(s)!!!"
    fi
}


if [ ! -f """ + str(LOG_CLEANUP_PROCESS_LOCK_FILE) + """ ]; then

    echo "Lock file not found on this node! \
    Creating it to prevent collisions..."
    touch """ + str(LOG_CLEANUP_PROCESS_LOCK_FILE) + """
    CREATE_LOCK_FILE_EXIT_CODE=$?
    if [ "${CREATE_LOCK_FILE_EXIT_CODE}" != "0" ]; then
        echo "Error creating the lock file. \
        Check if the airflow user can create files under tmp directory. \
        Exiting..."
        exit ${CREATE_LOCK_FILE_EXIT_CODE}
    fi

    echo ""
    echo "Running Cleanup Process..."

    FIND_STATEMENT="find ${BASE_LOG_FOLDER}/*/* -type f -mtime \
     +${MAX_LOG_AGE_IN_DAYS}"
    DELETE_STMT="${FIND_STATEMENT} -exec rm -f {} \;"

    cleanup "${FIND_STATEMENT}" "${DELETE_STMT}"
    CLEANUP_EXIT_CODE=$?

    FIND_STATEMENT="find ${BASE_LOG_FOLDER}/*/* -type d -empty"
    DELETE_STMT="${FIND_STATEMENT} -prune -exec rm -rf {} \;"

    cleanup "${FIND_STATEMENT}" "${DELETE_STMT}"
    CLEANUP_EXIT_CODE=$?

    FIND_STATEMENT="find ${BASE_LOG_FOLDER}/* -type d -empty"
    DELETE_STMT="${FIND_STATEMENT} -prune -exec rm -rf {} \;"

    cleanup "${FIND_STATEMENT}" "${DELETE_STMT}"
    CLEANUP_EXIT_CODE=$?

    echo "Finished Running Cleanup Process"

    echo "Deleting lock file..."
    rm -f """ + str(LOG_CLEANUP_PROCESS_LOCK_FILE) + """
    REMOVE_LOCK_FILE_EXIT_CODE=$?
    if [ "${REMOVE_LOCK_FILE_EXIT_CODE}" != "0" ]; then
        echo "Error removing the lock file. Check file permissions. To re-run the DAG, ensure that the lock file has been deleted (""" + str(LOG_CLEANUP_PROCESS_LOCK_FILE) + """)."
        exit ${REMOVE_LOCK_FILE_EXIT_CODE}
    fi

else
    echo "Another task is already deleting logs on this worker node. \
    Skipping it!"
    echo "If you believe you're receiving this message in error, kindly check \
    if """ + str(LOG_CLEANUP_PROCESS_LOCK_FILE) + """ exists and delete it."
    exit 0
fi

"""

for log_cleanup_id in range(1, NUMBER_OF_WORKERS + 1):

    for dir_id, directory in enumerate(DIRECTORIES_TO_DELETE):

        log_cleanup_op = BashOperator(
            task_id='log_cleanup_worker_num_' +
            str(log_cleanup_id) + '_dir_' + str(dir_id),
            bash_command=log_cleanup,
            params={
                "directory": str(directory),
                "sleep_time": int(log_cleanup_id)*3},
            pool='default_pool',
            executor_config={
                "cpu_millicores": 100,
                "ram_mem_mb": 50,
                "gpu_mem_mb": None
            },
            dag=dag)

        log_cleanup_op.set_upstream(start)
