"""
Shared by dag_auto_segmentation_pipeline.py and dag_wsi_mapping.py - both are
"thin orchestration DAGs" that trigger another DAG with a conf only known
after one of their own earlier tasks has run (e.g. an inferred/forced body
part), so plain LocalDagTriggerOperator's DAG-parse-time-fixed extra_conf
doesn't work for either of them.
"""
from kaapana.operators.LocalDagTriggerOperator import LocalDagTriggerOperator


class DynamicConfDagTriggerOperator(LocalDagTriggerOperator):
    """
    LocalDagTriggerOperator whose extra_conf is resolved from XCom right
    before triggering, instead of being fixed at DAG-parse time.

    LocalDagTriggerOperator itself reads kwargs["dag_run"].conf fresh at
    execute time (its trigger_dag() method), but self.extra_conf is just
    whatever static dict was passed to __init__ at DAG-parse time - there's
    no XCom/Jinja resolution of it. This subclass reuses 100% of
    LocalDagTriggerOperator's own conf-merge/trigger/wait-for-completion
    logic - it just resolves extra_conf one step earlier in the same call.
    """

    def __init__(self, dag, extra_conf_callable, **kwargs):
        self.extra_conf_callable = extra_conf_callable
        super().__init__(dag=dag, extra_conf=None, **kwargs)

    def trigger_dag(self, ds, **kwargs):
        self.extra_conf = self.extra_conf_callable(kwargs)
        return super().trigger_dag(ds, **kwargs)
