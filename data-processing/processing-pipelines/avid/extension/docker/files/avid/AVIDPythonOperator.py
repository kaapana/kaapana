import os
import time
import json
import requests
from datetime import timedelta

from avid.actions.pythonAction import PythonNaryBatchActionV2
from avid.common.artefact.crawler import DirectoryCrawler
from avid.common.artefact.fileHelper import saveArtefactList_xml
from avid.common.workflow import initSession
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from .HelperAvid import ensure_operator_session, compile_operator_splitters, compile_operator_sorters, check_input_name_consistency, initialize_inputs

class AVIDPythonOperator(KaapanaPythonBaseOperator):
    """
    :param op_args: arguments that should be passed to the python callable
    :param op_kwargs: keyword arguments that should be passed to the python callable
    :param output_indicator_callable
    """

    def __init__(self,
                 dag,
                 name,
                 python_callable,
                 input_operator=None,
                 op_kwargs=None,
                 output_indicator_callable=None,
                 additional_inputs = None,
                 linkers = None,
                 dependentLinkers = None,
                 input_splitter=None,
                 splitters = None,
                 input_sorter=None,
                 sorters = None,
                 input_alias=None,
                 avid_pass_only_URLs=True,
                 output_default_extension='nrrd',
                 avid_session=None,
                 avid_session_dir=None,
                 avid_artefact_crawl_callable=None,
                 avid_additional_action_props=None,
                 avid_prop_inheritance_dict=None,
                 *args, **kwargs):

        self.output_generate_callable = python_callable
        self.output_indicator_callable= output_indicator_callable
        self.avid_pass_only_URLs=avid_pass_only_URLs
        self.output_default_extension=output_default_extension

        self.avid_session=avid_session
        self.avid_session_dir=avid_session_dir
        if avid_session is not None and avid_session_dir is not None:
            raise RuntimeError('It is invalid to set both, avid_session and avid_session_dir! '
                               'Specify only one if needed.')

        self.avid_additional_action_props=avid_additional_action_props
        self.avid_prop_inheritance_dict=avid_prop_inheritance_dict
        self.avid_artefact_crawl_callable=avid_artefact_crawl_callable

        self.additional_kwargs = op_kwargs

        initialize_inputs(avid_operator=self, input_operator=input_operator, additional_inputs=additional_inputs)

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

        self.input_alias = input_alias

        self.input_operator = input_operator

        self.avid_action = None

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.run_avid_action,
            operator_out_dir=None,
            input_operator=input_operator,
            operator_in_dir=None,
            *args, **kwargs
        )

    @staticmethod
    def run_avid_action(action, **kwargs):
        action.do()

    def pre_execute(self, context):
        ensure_operator_session(avid_operator=self,context=context)

        splitters = compile_operator_splitters(avid_operator=self)
        sorters = compile_operator_sorters(avid_operator=self)

        self.avid_action = PythonNaryBatchActionV2(actionTag=self.task_id, primaryInputSelector=self.input_selector,
                                                   primaryAlias=self.input_alias,
                                                   additionalInputSelectors=self.additional_selectors,
                                                   linker=self.linkers, splitter=splitters,
                                                   sorter=sorters, dependentLinker=self.dependentLinkers,
                                                   session=self.avid_session,
                                                   additionalActionProps=self.avid_additional_action_props,
                                                   propInheritanceDict=self.avid_prop_inheritance_dict,
                                                   additionalArgs=self.additional_kwargs,
                                                   defaultoutputextension=self.output_default_extension,
                                                   indicateCallable=self.output_indicator_callable,
                                                   generateCallable=self.output_generate_callable,
                                                   alwaysDo=True)

        self.op_kwargs={'action':self.avid_action}

    def post_execute(self, context, result=None):
        if self.avid_session is not None:
            saveArtefactList_xml(self.avid_session.lastStoredLocationPath, self.avid_session.artefacts,
                                 self.avid_session.rootPath, savePathsRelative=False)

