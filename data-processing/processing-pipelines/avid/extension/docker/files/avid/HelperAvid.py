import os.path
import stat

from airflow.models import BaseOperator
from avid.actions import ActionBatchGenerator
from avid.common.cliConnector import default_artefact_url_extraction_delegate
from avid.common import osChecker, AVIDUrlLocater
from avid.common.artefact import ensureValidPath, generateArtefactEntry, ensureSimilarityRelevantProperty, addArtefactToWorkflowData, findSimilarArtefact
from avid.common.artefact.defaultProps import FORMAT_VALUE_DCM, TYPE_VALUE_RESULT
from avid.selectors import SelectorBase, ActionTagSelector, KeyValueSelector
from avid.common.artefact.crawler import DirectoryCrawler
from avid.common.workflow import initSession



from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator
import logging

from pydicom.filereader import dcmread

PROP_NAME_PATIENT_ID = 'patientID'
PROP_NAME_PATIENT_NAME = 'patientName'
PROP_NAME_MODALITY = 'modality'
PROP_NAME_SERIES_UID = 'seriesUID'
PROP_NAME_STUDY_UD = 'studyUID'
PROP_NAME_DATE_TIME = 'dcmDateTime'

ensureSimilarityRelevantProperty(PROP_NAME_MODALITY)
ensureSimilarityRelevantProperty(PROP_NAME_SERIES_UID)
ensureSimilarityRelevantProperty(PROP_NAME_PATIENT_ID)
ensureSimilarityRelevantProperty(PROP_NAME_PATIENT_NAME)

DCM_MODALITY_MR_SELECTOR = KeyValueSelector(key=PROP_NAME_MODALITY, value='MR')
DCM_MODALITY_CT_SELECTOR = KeyValueSelector(key=PROP_NAME_MODALITY, value='CT')
DCM_MODALITY_PET_SELECTOR = KeyValueSelector(key=PROP_NAME_MODALITY, value='PT')
DCM_MODALITY_US_SELECTOR = KeyValueSelector(key=PROP_NAME_MODALITY, value='MR')
DCM_MODALITY_SEG_SELECTOR = KeyValueSelector(key=PROP_NAME_MODALITY, value='SEG')

AVID_SESSION_DEFAULT_DIR = 'avid'


def deduce_dag_run_dir(workflow_dir, dag_run_id):
    return os.path.join(os.path.sep, workflow_dir, dag_run_id)


def deduce_avid_dir(workflow_dir, dag_run_id):
    return ensureValidPath(os.path.join(os.path.sep, workflow_dir, dag_run_id, AVID_SESSION_DEFAULT_DIR))


def deduce_session_dir(workflow_dir, dag_run_id):
    return ensureValidPath(os.path.join(os.path.sep, workflow_dir, dag_run_id, AVID_SESSION_DEFAULT_DIR, "session.avid"))


def convert_to_selector(operator):
    """Helper that converts tha passed object to an avid selector.
    If it is not convertible None is returned."""
    if isinstance(operator, BaseOperator):
        return ActionTagSelector(operator.task_id)
    elif isinstance(operator, SelectorBase):
        return operator
    else:
        return None


def _extract_relevant_date_time_string(dcm_dataset):
    if (0x0008,0x002A) in dcm_dataset:
        return dcm_dataset[0x0008,0x002A].value #AcquisitionDateTime"
    else:
        extracted_date = ""
        extracted_time = ""
        if (0x0008,0x0022) in dcm_dataset:
            extracted_date = dcm_dataset[0x0008,0x0022].value # AcquesitionDate
        elif (0x0008,0x0021) in dcm_dataset:
            extracted_date = dcm_dataset[0x0008,0x0021].value # SeriesDate
        elif (0x0008,0x0023) in dcm_dataset:
            extracted_date = dcm_dataset[0x0008,0x0023].value #ContentDate
        elif (0x0008,0x0020)  in dcm_dataset:
            extracted_date = dcm_dataset[0x0008,0x0020].value # StudyDate

        if (0x0008,0x0032) in dcm_dataset:
            extracted_time = dcm_dataset[0x0008,0x0032].value # AcquisitionTime
        elif (0x0008,0x0031) in dcm_dataset:
            extracted_time = dcm_dataset[0x0008,0x0031].value # SeriesTime
        elif (0x0008,0x0033) in dcm_dataset:
            extracted_time = dcm_dataset[0x0008,0x0033].value # ContentTime
        elif (0x0008,0x0030) in dcm_dataset:
            extracted_time = dcm_dataset[0x0008,0x0030].value # StudyTime

        result = extracted_date
        if len(extracted_date)!=0 and len(extracted_time)!=0:
            result+=' '
        result+=extracted_time
        
        return result


def _extract_dicom_tags(tags, file_name=None, data_set=None):
    if data_set is None:
        if file_name is None:
            raise ValueError('Invalid function call. Either file_name or data_set must be set.')
        data_set = dcmread(file_name, stop_before_pixels=True)

    result = dict()
    for tagname in tags:
        try:
            result[tagname] = data_set[tags[tagname]].value
        except Exception:
            result[tagname] = None

    return result


def _extract_task_id(path_parts, series_UID):
    """Extracts the task id given the defauls 'classical' path layout for KaapanaOperators.
       Assumes that the following classical kaapana directory layout is used:
       data/<series>/<task_id>/..."""
    if len(path_parts) == 0:
        return None
            # series_UID and <series> divert in case of a reference image (e.g. segmentation)
    return path_parts[-1]
    #last_was_series = False
    #for part in path_parts:
    #    if last_was_series:
    #        return part
    #    last_was_series = part == series_UID

    #return None


class DefaultKaapanaDataCrawlCallable(object):
    """Assumes that the following classical kaapana directory layout is used:
    data/<series>/<task_id>/..."""
    def __init__(self):
        pass

    def __call__(self, path_parts, file_name, full_path):
        if AVID_SESSION_DEFAULT_DIR not in path_parts:
            name, ext = os.path.splitext(file_name)

            try:
                ds = dcmread(full_path, stop_before_pixels=True)
                relevantDCMTags = {PROP_NAME_PATIENT_ID: (0x0010,0x0020),
                                   PROP_NAME_PATIENT_NAME: (0x0010,0x0010),
                                   PROP_NAME_MODALITY:(0x0008, 0x0060),
                                   PROP_NAME_SERIES_UID:(0x0020, 0x000e),
                                   PROP_NAME_STUDY_UD:(0x0020,0x000d)}
                dcmProps = _extract_dicom_tags(data_set=ds,tags=relevantDCMTags)

                datetime = _extract_relevant_date_time_string(ds)

                dcmProps[PROP_NAME_DATE_TIME] = datetime

                taskID = _extract_task_id(path_parts=path_parts, series_UID=dcmProps[PROP_NAME_SERIES_UID])

                if taskID is None:
                    raise RuntimeError('Cannot deduce task id from file path: {}'.format(full_path))

                caseID = 'unkown'
                if dcmProps[PROP_NAME_PATIENT_NAME] is not None:
                    caseID = dcmProps[PROP_NAME_PATIENT_NAME]
                elif dcmProps[PROP_NAME_PATIENT_ID] is not None:
                    caseID = dcmProps[PROP_NAME_PATIENT_ID]

                return generateArtefactEntry(case=caseID, caseInstance=None, timePoint=0,
                                             actionTag=taskID, artefactType=TYPE_VALUE_RESULT,
                                             artefactFormat=FORMAT_VALUE_DCM, url = full_path,
                                             **dcmProps)
            except Exception:
                pass

        return None


def update_artefacts(destination_list, source_list, update_existing=False):
    for artefact in source_list:
        if findSimilarArtefact(destination_list,artefact) is None or update_existing:
            addArtefactToWorkflowData(destination_list,artefact, removeSimelar=True)


def ensure_operator_session(avid_operator, context):
    """Helper function that ensures an avid session is available for the given operator and context."""
    if avid_operator.avid_session is None:
        if avid_operator.input_operator is not None:
            try:
                avid_operator.avid_session = avid_operator.input_operator.avid_session
                avid_operator.avid_session_dir = avid_operator.avid_session.lastStoredLocationPath
                avid_operator.log.debug('Reuse AVID session of input_operator.')
            except Exception:
                pass

    if avid_operator.avid_session is None:
        if  avid_operator.avid_session_dir is None:
            avid_operator.avid_session_dir = deduce_session_dir(avid_operator.workflow_dir, context['run_id'])

        avid_operator.log.debug('Initialize AVID session at: {}'.format(avid_operator.avid_session_dir))
        avid_operator.avid_session = initSession(sessionPath=avid_operator.avid_session_dir, expandPaths=True, initLogging=False)
        #rootlogger = logging.getLogger()
        #rootlogger.setLevel("DEBUG")


    if len(avid_operator.avid_session.artefacts) == 0 or avid_operator.avid_artefact_crawl_callable is not None:
        avid_operator.log.debug('Sync AVID session with workflow data.')

        crawlable = avid_operator.avid_artefact_crawl_callable
        if avid_operator.avid_artefact_crawl_callable is None:
            crawlable = DefaultKaapanaDataCrawlCallable()
        else:
            crawlable = UserCrawlCallableWrapper(avid_operator.avid_artefact_crawl_callable)

        crawler = DirectoryCrawler(rootPath=deduce_dag_run_dir(avid_operator.workflow_dir, context['run_id']), fileFunctor=crawlable, ignoreExistingArtefacts=True)
        artefacts = crawler.getArtefacts()
        update_artefacts(destination_list=avid_operator.avid_session.artefacts, source_list=artefacts, update_existing=False)


def compile_operator_splitters(avid_operator):
    splitters = avid_operator.splitters
    if avid_operator.input_splitter is not None:
        if splitters is None:
            splitters = dict()
        else:
            splitters = splitters.copy()
        splitters[ActionBatchGenerator.PRIMARY_INPUT_KEY] = avid_operator.input_splitter

    return splitters


def compile_operator_sorters(avid_operator):
    sorters = avid_operator.sorters
    if avid_operator.input_sorter is not None:
        if sorters is None:
            sorters = dict()
        else:
            sorters = sorters.copy()
        sorters[ActionBatchGenerator.PRIMARY_INPUT_KEY] = avid_operator.input_sorter

    return sorters


def check_input_name_consistency(components, avid_operator, component_name, include_primary=True):
    if components is not None:
        for input_name in components:
            if not input_name in avid_operator.additional_inputs or (include_primary and (not input_name==ActionBatchGenerator.PRIMARY_INPUT_KEY or not input_name==self.input_alias)):
                raise ValueError('Additional {} uses a invalid/nonexistent additional input name. Invalid name: {}.'.format(component_name, input_name))


def initialize_inputs(avid_operator, input_operator, additional_inputs):
    avid_operator.input_selector = convert_to_selector(input_operator)
    if avid_operator.input_selector is None:
        raise TypeError('Input operator must either be an airflow operator or an avid selector!')

    avid_operator.additional_inputs = additional_inputs
    avid_operator.additional_selectors = None
    if avid_operator.additional_inputs is not None:
        avid_operator.additional_selectors = dict()
        for inputName in avid_operator.additional_inputs:
            selector = convert_to_selector(avid_operator.additional_inputs[inputName])
            if selector is None:
                raise TypeError('Additional input must either be an airflow operator or an avid selector! Invalid additional input name {}'.format(inputName))
            avid_operator.additional_selectors[inputName]=selector


class UserCrawlCallableWrapper(object):
    """Helper that ensures that user defined crawl functions always ignore the avid session directories."""
    def __init__(self, callable):
        self.callable = callable

    def __call__(self, path_parts, file, full_path):
        if AVID_SESSION_DEFAULT_DIR not in path_parts:
            return self.callable(path_parts, file, full_path)
        else:
            return None


class ContainerCLIConnectorBase(object):
    """Base Implementation that allows to execute an action in a container."""

    def __init__(self, mount_map):
        """:param mount_map: Dictionary that contains the mapping between relevant paths
         outside of the container (those stored in the session) and the pathes that will
         be known in the container. Needed to properly convert artefact urls.
         Key of the map is the mount path inside of the container, the value is the respective
         path outside."""
        self.mount_map=mount_map
        pass

    @staticmethod
    def apply_mount_map(mount_map, filepath):
        mappedPath = filepath

        for mountPath in mount_map:
            try:
                if filepath.find(mount_map[mountPath])==0:
                    mappedPath = mappedPath.replace(mount_map[mountPath], mountPath)
                    break
            except Exception:
                pass
        return mappedPath

    def get_artefact_url_extraction_delegate(self, action_extraction_delegate=None):
        """Returns the URL extraction delegate that should be used when working with the connector.
        :param action_extraction_delegate: If the actions specifies its own delegate it can be passed
        and will be wrapped accordingly."""

        if action_extraction_delegate is None:
            action_extraction_delegate = default_artefact_url_extraction_delegate

        def extractionWrapper(arg_name, arg_value):
            results = action_extraction_delegate(arg_name, arg_value)

            mappedResults = list()
            for result in results:
                mappedResults.append(ContainerCLIConnectorBase.apply_mount_map(mount_map=self.mount_map, filepath=result))

            return mappedResults

        return extractionWrapper

    def generate_cli_file(self, file_path_base, content):
        """Function generates the CLI file based on the passed file name base (w/o extension, extension will be added)
         and the content. It returns the full path to the CLI file."""

        file_name = file_path_base + os.extsep + 'sh'

        path = os.path.split(file_name)[0]

        try:
            osChecker.checkAndCreateDir(path)
            with open(file_name, "w") as outputFile:
                if not osChecker.isWindows():
                    content = '#!/bin/bash' + '\n' + content
                outputFile.write(content)
                outputFile.close()

            if not osChecker.isWindows():
                st = os.stat(file_name)
                os.chmod(file_name, st.st_mode | stat.S_IXUSR)

        except Exception:
            raise

        return file_name

    def execute(self, cli_file_path, log_file_path=None, error_log_file_path=None, cwd=None):
        raise NotImplementedError


class KaapanaCLIConnector(ContainerCLIConnectorBase):
    def __init__(self, mount_map, kaapana_operator, context, executable_url=None):
        """:param mount_map: Dictionary that contains the mapping between relevant paths
        outside of the container (those stored in the session) and the pathes that will
        be known in the container. Needed to properly convert artefact urls.
        Key of the map is the mount path inside of the container, the value is the respective
        path outside."""
        super().__init__(mount_map=mount_map)
        self.kaapana_operator = kaapana_operator
        self.context = context
        self._executable_url=executable_url

    def get_executable_url(self, workflow, actionID, actionConfig = None):
        """Returns url+executable for a actionID request that should be used in the cli file. This serves as an
        abstraction, in order to allow the connector to change the deduction strategy for the executable url.
        Default implementation just uses the AVIDUrlLocater.
        :param workflow: session instance that should be used for deducing the executable url
        :param actionID: actionID of the action that requests the URL
        :param actionConfig: actionConfig specifies if a certian configuration of an action should be used."""
        if self._executable_url is None:
            return AVIDUrlLocater.getExecutableURL(workflow=workflow, actionID=actionID, actionConfig=actionConfig)
        else:
            return self._executable_url
        """Implementation that allows to execute a container based on a KaapanaBaseOperator.
        It is used to connect the features of a AVID CLIBatchAction with the KaapanaBaseOperator."""

    def execute(self, cli_file_path, log_file_path=None, error_log_file_path=None, cwd=None):
        logfile = None

        if log_file_path is not None:
            try:
                logfile = open(log_file_path, "w")
            except:
                logfile = None

        errlogfile = None

        if error_log_file_path is not None:
            try:
                errlogfile = open(error_log_file_path, "w")
            except:
                errlogfile = None

        try:
            mapped_cli_file_path = ContainerCLIConnectorBase.apply_mount_map(mount_map=self.mount_map,
                                                                             filepath=cli_file_path)
            self.kaapana_operator.cmds=[mapped_cli_file_path]

            print("Spinning up container in Kaapana Base operator")
            container_return = KaapanaBaseOperator.execute(self=self.kaapana_operator, context=self.context)

            logfile.write(str(container_return))

        finally:
            if logfile is not None:
                logfile.close()
            if errlogfile is not None:
                errlogfile.close()
