import os
import glob
import json
import datetime

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalConcatJsonOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        print("Starting moule LocalConcatJsonOperator...")
        print(kwargs)

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_dirs = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]
        timestamp=datetime.datetime.utcnow()
        json_output_path=os.path.join(run_dir,self.operator_out_dir,"{}-{}.json".format(timestamp, self.name))
        if not os.path.exists(os.path.dirname(json_output_path)):
            os.makedirs(os.path.dirname(json_output_path))

        json_files=[]
        for batch_element_dir in batch_dirs:
            batch_el_json_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir,"**","*.json*"),recursive=True))
            for json_file in batch_el_json_files:
                with open(json_file) as data_file:    
                    json_dict = json.load(data_file)
                json_files.append(json_dict)


        with open(json_output_path, "w", encoding='utf-8') as jsonData:
            json.dump(json_files, jsonData, indent=4, sort_keys=True)


    def __init__(self,
                 dag,
                 name='concatenated',
                 *args, **kwargs):

        super().__init__(
            dag,
            name=name,
            python_callable=self.start,
            *args, **kwargs
        )