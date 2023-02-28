import glob
import os
import pydicom
import json

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperOpensearch import HelperOpensearch

class LocalDeleteFromMetaOperator(KaapanaPythonBaseOperator):
    """
    Operator to remove series from OpenSearch's index.

    This operator removes either selected series or whole studies from OpenSearch's index for the functional unit Meta.
    The operator relies on OpenSearch's "delete_by_query" function.

    **Inputs:**

    * Input data which should be removed is given via input parameter: delete_operator.
    """

    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        if 'form_data' in conf and conf['form_data'] is not None and 'delete_complete_study' in conf['form_data']:
                self.delete_complete_study = conf['form_data']['delete_complete_study']
                print('Delete entire study set to ', self.delete_complete_study)
        if self.delete_all_documents:
            print("Delting all documents from META ...")
            query = {"query": {"match_all": {}}}
            HelperOpensearch.delete_by_query(query)
        else:
            run_dir = os.path.join(self.airflow_workflow_dir, kwargs['dag_run'].run_id)
            batch_folder = [f for f in glob.glob(os.path.join(run_dir, self.batch_name, '*'))]

            dicoms_to_delete = []
            for batch_element_dir in batch_folder:
                dcm_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"), recursive=True))
                if len(dcm_files) > 0:
                    incoming_dcm = pydicom.dcmread(dcm_files[0])
                    series_uid = incoming_dcm.SeriesInstanceUID
                    study_uid = incoming_dcm.StudyInstanceUID
                    if self.delete_complete_study:
                        dicoms_to_delete.append(study_uid)
                    else:
                        dicoms_to_delete.append(series_uid)
                else:
                    json_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.json*"), recursive=True))
                    for meta_files in json_files:
                        with open(meta_files) as fs:
                            metadata = json.load(fs)
                            dicoms_to_delete.append({
                                'study_uid': metadata['0020000D StudyInstanceUID_keyword'],
                                'series_uid':  metadata['0020000E SeriesInstanceUID_keyword']
                        })

            if self.delete_complete_study:
                query = {"query": {"terms": {"0020000D StudyInstanceUID_keyword": dicoms_to_delete}}}
            else:
                query = {"query": {"terms": {"_id": dicoms_to_delete}}}

            HelperOpensearch.delete_by_query(query)

    def __init__(self,
                 dag,
                 delete_operator=None,
                 delete_all_documents=False,
                 delete_complete_study=False,
                 **kwargs):
        """
        :param delete_operator:
        :param delete_all_documents: Specifies the amount of removed data to all documents.
        :param delete_complete_study: Specifies the amount of removed data to all series of a specified study.
        """
    
        self.delete_all_documents = delete_all_documents
        self.delete_complete_study = delete_complete_study

        super().__init__(
            dag=dag,
            name='delete-meta',
            python_callable=self.start,
            **kwargs
        )
