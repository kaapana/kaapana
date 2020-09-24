import os

from sqlalchemy import or_

from airflow import models
from airflow.models import TaskFail, DagModel
from airflow.utils.db import provide_session
from airflow.exceptions import DagFileExists, DagNotFound


@provide_session
def delete_dag(dag_id: str, keep_records_in_log: bool = True, session=None) -> int:
    """
    :param dag_id: the dag_id of the DAG to delete
    :param keep_records_in_log: whether keep records of the given dag_id
        in the Log table in the backend database (for reasons like auditing).
        The default value is True.
    :param session: session used
    :return count of deleted dags
    """
    dag = session.query(DagModel).filter(DagModel.dag_id == dag_id).first()
    if dag is None:
        raise DagNotFound("Dag id {} not found".format(dag_id))

    if dag.fileloc and os.path.exists(dag.fileloc):
        raise DagFileExists("Dag id {} is still in DagBag. "
                            "Remove the DAG file first: {}".format(dag_id, dag.fileloc))

    count = 0

    # noinspection PyUnresolvedReferences,PyProtectedMember
    for model in models.base.Base._decl_class_registry.values():  # pylint: disable=protected-access
        if hasattr(model, "dag_id"):
            if keep_records_in_log and model.__name__ == 'Log':
                continue
            cond = or_(model.dag_id == dag_id, model.dag_id.like(dag_id + ".%"))
            count += session.query(model).filter(cond).delete(synchronize_session='fetch')
    if dag.is_subdag:
        parent_dag_id, task_id = dag_id.rsplit(".", 1)
        for model in models.DagRun, TaskFail, models.TaskInstance:
            count += session.query(model).filter(model.dag_id == parent_dag_id,
                                                 model.task_id == task_id).delete()

    return count
