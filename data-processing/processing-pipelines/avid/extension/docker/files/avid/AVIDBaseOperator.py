import os
import time
import json
import requests
from datetime import timedelta

from airflow.utils.state import State
from avid.actions import BatchActionBase
from avid.actions.pythonAction import PythonNaryBatchActionV2
from avid.common.artefact.fileHelper import saveArtefactList_xml
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
from avid_operator.HelperAvid import ensure_operator_session, compile_operator_splitters, compile_operator_sorters, check_input_name_consistency, initialize_inputs, deduce_dag_run_dir, KaapanaCLIConnector
from airflow import AirflowException
class AVIDBaseOperator(KaapanaBaseOperator):
    """
    :param op_args: arguments that should be passed to the python callable
    :param op_kwargs: keyword arguments that should be passed to the python callable
    :param output_indicator_callable
    """

    def __init__(self,
                 dag,
                 name,
                 executable_url: str = None,
                 actionID: str = None,
                 image=None,
                 input_operator=None,
                 #AVID
                 image_avid_class_file=None,
                 batch_action_class=None,
                 action_class=None,
                 action_kwargs=None,
                 action_cli_path=None,
                 additional_inputs: dict() = None,
                 linkers = None,
                 dependentLinkers = None,
                 input_splitter=None,
                 splitters = None,
                 input_sorter=None,
                 sorters = None,
                 input_alias=None,
                 avid_session=None,
                 avid_session_dir=None,
                 avid_artefact_crawl_callable=None,
                 additionalActionProps=None,
                 envs=None,
                 **kwargs):
        
        if actionID is not None:
            self.actionID = actionID
        else:
            self.actionID = name
        self.executable_url = executable_url
        self.avid_session=avid_session
        self.avid_session_dir=avid_session_dir
        if avid_session is not None and avid_session_dir is not None:
            raise RuntimeError('It is invalid to set both, avid_session and avid_session_dir! '
                               'Specify only one if needed.')

        self.avid_artefact_crawl_callable=avid_artefact_crawl_callable

        initialize_inputs(avid_operator=self, input_operator=input_operator, additional_inputs=additional_inputs)
        self.input_alias = input_alias
        if input_alias is None:
            self.input_alias = 'primaryInputSelector'
        check_input_name_consistency(components=linkers, avid_operator=self, component_name='linkers')
        self.linkers = linkers

        check_input_name_consistency(components=dependentLinkers, avid_operator=self, component_name='dependentLinkers')
        self.dependentLinkers = dependentLinkers

        self.input_splitter = input_splitter
        check_input_name_consistency(components=splitters, avid_operator=self, component_name='splitters')
        self.splitters = splitters

        self.input_sorter = input_sorter
        check_input_name_consistency(components=sorters, avid_operator=self, component_name='sorters')
        self.sorters = sorters

        self.input_operator = input_operator

        self.image_avid_class_file = image_avid_class_file
        self.action_class=action_class
        self.batch_action_class = batch_action_class

        self.action_kwargs=action_kwargs
        if action_kwargs is None:
            self.action_kwargs = {}

        self.avid_action = None
        self.cli_connector = None
        self.additionalActionProps = additionalActionProps

        env_vars = {}
        if envs:
            env_vars.update(envs)


        super().__init__(
            dag=dag,
            name=name,
            image=image,
            operator_out_dir=None,
            input_operator=input_operator,
            operator_in_dir=None,
            env_vars=env_vars,
            **kwargs
        )

    def pre_execute(self, context):

        ensure_operator_session(avid_operator=self,context=context)

        splitters = compile_operator_splitters(avid_operator=self)
        sorters = compile_operator_sorters(avid_operator=self)
        
        self.cli_connector = KaapanaCLIConnector(mount_map={'/data':deduce_dag_run_dir(workflow_dir=os.path.join(os.path.sep,self.workflow_dir), dag_run_id=context['run_id'])},
                                                 kaapana_operator=self, context=context, executable_url=self.executable_url)

 
        self.avid_session.actionTools[self.actionID] = self.executable_url

        all_action_kwargs = self.action_kwargs.copy()

        all_action_kwargs['actionTag'] = self.task_id
        if self.linkers is not None:
            all_action_kwargs['linker'] = self.linkers
        if self.splitters is not None:
            all_action_kwargs['splitter'] = splitters
        if self.sorters is not None:
            all_action_kwargs['sorter'] = sorters
        if self.dependentLinkers is not None:
            all_action_kwargs['dependentLinker'] = self.dependentLinkers
        all_action_kwargs['session'] = self.avid_session
        all_action_kwargs['cli_connector'] = self.cli_connector
        all_action_kwargs['alwaysDo'] = True
        all_action_kwargs['additionalActionProps'] = self.additionalActionProps

        batch_action_class = None
        if not self.batch_action_class is None and not self.batch_action_class.__name__ == 'BatchActionBase':
            batch_action_class = self.batch_action_class
            all_action_kwargs[self.input_alias] = self.input_selector
            if self.additional_selectors is not None:
                all_action_kwargs.update(self.additional_selectors) 
        elif not self.action_class is None:
                batch_action_class = BatchActionBase
                all_action_kwargs['actionClass'] = self.action_class
                all_action_kwargs['primaryInputSelector'] = self.input_selector
                all_action_kwargs['primaryAlias'] = self.input_alias
                all_action_kwargs['additionalInputSelectors'] = self.additional_selectors
                all_action_kwargs['actionID'] = self.actionID
        else:
            raise NotImplementedError('Feature to get class from container image is not implemented yet.')

        self.avid_action = batch_action_class(**all_action_kwargs)
        print("pre-execute done!")

    def execute(self, context):
        action_result = self.avid_action.do()
        result = State.SUCCESS
        if action_result.isFailure():
            result = State.FAILED
            raise AirflowException("AVID raised fail: ", result)
        return result

    def post_execute(self, context, result=None):
        if self.avid_session is not None:
            saveArtefactList_xml(self.avid_session.lastStoredLocationPath, self.avid_session.artefacts,
                                 self.avid_session.rootPath, savePathsRelative=False)

