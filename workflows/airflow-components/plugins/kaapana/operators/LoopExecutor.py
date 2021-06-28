import glob, os, shutil
from pathlib import Path
from datetime import timedelta
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project


class LoopExecutor(KaapanaBaseOperator):
    def execute(self, context):
        results = []
        for container in range(0, self.number_of_container):
            self.parallel_id = str(container)
            #:param cmds: entrypoint of the container. (templated)
            # The docker images's entrypoint is used if this is not provide.
            # :type cmds: list of str
            # :param arguments: arguments of to the entrypoint. (templated)
            #  The docker image's CMD is used if this is not provided.
            #   :type arguments: list of str
            #   self.cmds=[],
            #   self.arguments=[],
            #   self.env_vars=None,
            self.env_vars.update({
                "CONTAINER_NUMBER": str(container)
            })
            container_return = super().execute(context=context)
            if self.xcom_push:
                results.append(container_return)
        return results

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(minutes=20),
                 *args, **kwargs):

        name = "loop_executor"
        self.number_of_container = 5
        xcom_push = False

        super().__init__(
            dag=dag,
            image="{}{}/dummy_container:0.1.1".format(default_registry, default_project),
            name=name,
            xcom_push=xcom_push,
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            *args, **kwargs
        )
