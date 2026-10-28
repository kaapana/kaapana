"""Prepares the training folds of a run before the scheduler sees them.

Kaapana's job scheduler reserves executor_config["gpu_mem_mb"] of a task instance on a GPU before the task
starts, and reads it from the database, not from the DAG file. A DAG can only set one value per task, so this
task runs before the folds and sets the value of this run's fold task instances from the form (default: what
the selected plans need, recorded by nnunetv2-plan-preprocess). Folds that are not selected are skipped here,
so they never wait for a GPU only to skip themselves.
"""

from airflow.models import Pool
from airflow.utils.session import provide_session
from airflow.utils.state import TaskInstanceState


@provide_session
def prepare_folds(session=None, **context):
    form = (context["dag_run"].conf or {}).get("workflow_form") or {}
    selected = {str(f) for f in form.get("folds") or []}
    gb = form.get("gpu_memory_gb")
    mb = int(float(gb) * 1024) if gb else None
    if mb:
        _check_gpu_memory(mb, session)

    folds = {t.task_id: str(t.fold) for t in context["dag"].tasks if getattr(t, "fold", None) is not None}
    for ti in context["dag_run"].get_task_instances(session=session):
        if ti.task_id not in folds:
            continue
        if folds[ti.task_id] not in selected:
            ti.set_state(TaskInstanceState.SKIPPED, session=session)
        elif mb and (ti.executor_config or {}).get("gpu_mem_mb"):  # without GPU support: nothing to reserve
            ti.executor_config = {**ti.executor_config, "gpu_mem_mb": mb}
            session.merge(ti)
    session.commit()
    print(f"Folds {', '.join(sorted(selected))}, each reserves {gb or 'the default'} GB of GPU memory.")


def _check_gpu_memory(mb, session):
    """Fail now instead of letting the folds wait forever for a GPU that can never have this much free."""
    # the job scheduler keeps one pool per GPU with its memory in MB as slots
    capacities = [p.slots for p in session.query(Pool).filter(Pool.pool.like("NODE_GPU_%_MEM"))]
    if capacities and mb > max(capacities):
        raise ValueError(
            f"A fold needs {mb // 1024} GB of GPU memory, but the largest GPU has {max(capacities) // 1024} GB. "
            "Lower 'GPU memory per fold' to try anyway."
        )
    # a task only starts when a GPU has the memory free right now; memory in use on a GPU without Kaapana
    # tasks belongs to programs outside Kaapana, which never free it
    try:
        from kaapana.kubetools.prometheus_query import get_node_gpu_infos
        from kaapana.kubetools.utilization_service import UtilService

        gpus = get_node_gpu_infos()
        _, active = UtilService.get_active_gpu_reservations(session=session)
    except Exception as e:  # without the metrics, scheduling simply waits as before
        print(f"Free GPU memory not checked: {e}")
        return
    if not gpus or any(active[UtilService.get_gpu_reservation_key(g)] or g["free"] >= mb for g in gpus):
        return
    best = max(gpus, key=lambda g: g["free"])
    raise ValueError(
        f"A fold needs {mb // 1024} GB of GPU memory, but at most {best['free'] // 1024} GB are free: other "
        f"programs use {best['used'] // 1024} GB of the GPU ({best['gpu_name']}). Free the GPU or lower "
        "'GPU memory per fold'."
    )
