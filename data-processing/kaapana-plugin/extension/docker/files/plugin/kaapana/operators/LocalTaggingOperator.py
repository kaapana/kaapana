import os
import json
import glob
import elasticsearch
from enum import Enum
from typing import List
from kaapana.operators.HelperElasticsearch import HelperElasticsearch
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalTaggingOperator(KaapanaPythonBaseOperator):

    class Action(Enum):
        ADD = "add"
        DELETE = "delete"
        ADD_FROM_FILE = "add_from_file"

    def tagging(self, series_instance_uid: str, tags: List[str], tags2add: List[str] = [], tags2delete: List[str] = []):
        print(series_instance_uid)
        print(f"Tags 2 add: {tags2add}")
        print(f"Tags 2 delete: {tags2delete}")
        
        # Read Tags
        es = elasticsearch.Elasticsearch([{'host': self.elastic_host, 'port': self.elastic_port}])
        doc = es.get(index=self.elastic_index, id=series_instance_uid)
        print(doc)
        index_tags = doc["_source"].get(self.tag_field, [])

        final_tags = list(set(tags).union(set(index_tags)).difference(set(tags2delete)).union(set(tags2add)))
        print(f"Final tags: {final_tags}")
 
        # Write Tags back
        body = {"doc": {self.tag_field: final_tags}}
        es.update(index=self.elastic_index, id=series_instance_uid, body=body, doc_type="_doc")
 

    def start(self, ds, **kwargs):
        print("Start tagging")
        tags = []
        action = self.Action.ADD_FROM_FILE
        
        conf = kwargs['dag_run'].conf

        if 'form_data' in conf:
            form_data = conf['form_data']
            if 'tags' in form_data:
                tags = form_data['tags'].split(',')
            if 'action' in form_data:
                action_param = form_data['action'].lower().strip()
                action = self.Action(action_param)
        
        print(f"Action: {action}")
        print(f"Tags from form: {tags}")
        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        for batch_element_dir in batch_folder:
            json_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.json*"), recursive=True))
            for meta_files in json_files:
                print(f"Do tagging for file {meta_files}")
                with open(meta_files) as fs:
                    metadata = json.load(fs)
                    series_uid = metadata['0020000E SeriesInstanceUID_keyword']
                    existing_tags = metadata.get(self.tag_field, [])
                    
                    # Adding tags based on other fields of the file
                    file_tags = []
                    if self.add_tags_from_file:
                        for tag_from_file in self.tags_to_add_from_file:
                            value = metadata.get(tag_from_file)
                            if value:
                                file_tags.extend(value)

                    if action == self.Action.ADD_FROM_FILE:
                        self.tagging(series_uid, tags=existing_tags, tags2add=file_tags)
                    elif action == self.Action.ADD:
                        self.tagging(series_uid, tags=existing_tags, tags2add=tags)
                    elif action == self.Action.DELETE:
                        self.tagging(series_uid, tags=existing_tags, tags2delete=tags)

    def __init__(self,
                 dag,
                 tag_field: str="dataset_tags_keyword",
                 add_tags_from_file: bool=False,
                 tags_to_add_from_file: List[str]=["00120020 ClinicalTrialProtocolID_keyword"],
                 elastic_host='elastic-meta-service.meta.svc',
                 elastic_port=9200,
                 elastic_index="meta-index",
                 *args,
                 **kwargs):
        """
        :param tag_field: the field of the elastic object where the tags are stored
        :param add_tags_from_file: determens if the content of the fileds specified by tags_to_add_from_file are added as tags
        :param tags_to_add_from_file: a list of fields form the input json where the values are added as tags if add_tags_from_file is true
        """

        self.tag_field = tag_field
        self.add_tags_from_file = add_tags_from_file
        self.tags_to_add_from_file = tags_to_add_from_file
        self.elastic_host = elastic_host
        self.elastic_port = elastic_port
        self.elastic_index = elastic_index

        super().__init__(
                dag=dag,
                name="tagging",
                python_callable=self.start,
                **kwargs
            )
