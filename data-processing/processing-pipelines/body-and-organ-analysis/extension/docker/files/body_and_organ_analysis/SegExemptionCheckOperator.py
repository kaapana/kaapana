from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from airflow.models.taskinstance import TaskInstance
from airflow.models.dagrun import DagRun
from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.utils.state import State
from typing import Dict, Any


class SegExemptionCheckOperator(KaapanaBaseOperator):
    def __init__(self, rule: Dict[str, Any], **kwargs):
        # Trigger after all upstream tasks finish
        super().__init__(trigger_rule="all_done", **kwargs)
        self.rule = rule  # Contains condition and reason

    def execute(self, context: Dict[str, Any]) -> None:
        ti: TaskInstance = context["ti"]
        dag_run: DagRun = context["dag_run"]
        conf: Dict[str, Any] = dag_run.conf or {}

        upstream_task_ids = ti.task.upstream_task_ids

        for upstream_task_id in upstream_task_ids:
            upstream_ti = dag_run.get_task_instance(upstream_task_id)
            upstream_state = upstream_ti.current_state()

            if upstream_state == State.SUCCESS:
                continue  # No problem, task succeeded

            elif upstream_state in {State.FAILED, State.UPSTREAM_FAILED}:
                # Failed — check if this is an allowed exception
                if self.rule["condition"](conf):
                    print(
                        f"[Exemption] Skipping {upstream_task_id}: {self.rule['reason']}"
                    )
                    raise AirflowSkipException("Exempted failure")
                else:
                    print(f"[Exemption] No exemption for {upstream_task_id}")
                    raise AirflowFailException("Non-exempted failure")

        # All upstreams succeeded — continue
        print("[Exemption] All upstream succeeded, continuing.")
        return
