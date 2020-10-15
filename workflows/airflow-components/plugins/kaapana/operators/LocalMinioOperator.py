
from minio import Minio
import os
import glob
import uuid
from zipfile import ZipFile
import datetime
from datetime import timedelta

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.blueprints.kaapana_utils import generate_minio_credentials
from kaapana.operators.HelperMinio import HelperMinio

class LocalMinioOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        conf = kwargs['dag_run'].conf
        print('conf', conf)
        ###################
        # TODO: Can't be used like this, since token expires, we should use presigned_urls, which should be generated when the airflow is triggered 
        # if 'conf' in conf:
        #     if 'x_auth_token' in conf['conf']:
        #         access_key, secret_key, session_token = generate_minio_credentials(conf['conf']['x_auth_token'])
        #     else:
        #         access_key = os.environ.get('MINIOUSER'),
        #         secret_key = os.environ.get('MINIOPASSWORD')
        #         session_token = None
        ###################
        
        access_key = os.environ.get('MINIOUSER')
        secret_key = os.environ.get('MINIOPASSWORD')
        session_token = None
        
        # Todo: actually should be in pre_execute, however, when utilizing Airflow PythonOperator pre_execute seems to have no effect...
        if 'Key' in conf:
            self.bucket_name = conf['Key'].split('/')[0]
            self.object_name= "/".join(conf['Key'].split('/')[1:])
            print(f'Setting bucket name to {self.bucket_name} and object name to {self.object_name}')
        
        minioClient = Minio(self.minio_host+":"+self.minio_port,
                            access_key=access_key,
                            secret_key=secret_key,
                            session_token=session_token,
                            secure=False)


        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]
        print(batch_folder)
        
        if self.bucket_name is None:
            print("No BUCKETID env set!")
            self.bucket_name = kwargs['dag'].dag_id
            print(("Generated Bucket-Id: %s" % self.bucket_name))
         
        object_dirs = []
        # Get contents from run_dir
        object_dirs = object_dirs + self.action_operator_dirs
        for action_operator in self.action_operators:
            object_dirs.append(action_operator.operator_out_dir)
            
        # Get contents from batch_elements
        for batch_element_dir in batch_folder:
            for operator_dir in self.action_operator_dirs:
                object_dirs.append(os.path.relpath(os.path.join(batch_element_dir, operator_dir), run_dir))
            for action_operator in self.action_operators:
                object_dirs.append(os.path.relpath(os.path.join(batch_element_dir, action_operator.operator_out_dir), run_dir))

        # Files to apply action
        # Add object_names
        object_names = []
        object_names = object_names + self.action_files
        # Add relative file paths from operators
        for object_dir in object_dirs:
            for action_file in self.action_files:
                object_names.append(os.path.join(object_dir, action_file))
        

        if self.zip_files:
            timestamp = (datetime.datetime.now() + timedelta(hours=2)).strftime("%y-%m-%d-%H:%M:%S%f")
            target_dir = os.path.join(run_dir, self.operator_out_dir)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                
            zip_object_name = f"{kwargs['dag'].dag_id}_{timestamp}.zip"
            zip_file_path = os.path.join(target_dir, zip_object_name)
            with ZipFile(zip_file_path, 'w') as zipObj:
                if not object_dirs:
                    print(f'Zipping everything from {run_dir}')
                    object_dirs = ['']
                else:
                    print(f'Zipping everything from {", ".join(object_dirs)}')
                for object_dir in object_dirs:
                    for path, _, files in os.walk(os.path.join(run_dir, object_dir)):
                        for name in files:
                            file_path = os.path.join(path, name)
                            rel_dir = os.path.relpath(path, run_dir)
                            rel_dir = '' if rel_dir== '.' else rel_dir
                            if rel_dir == self.operator_out_dir:
                                print('Skipping files in {rel_dir}, due to recursive zipping!')
                                continue
                            object_name =os.path.join(rel_dir, name)
                            zipObj.write(os.path.join(path, name), object_name)
            
            HelperMinio.apply_action_to_file(minioClient, 'put', self.bucket_name, zip_object_name, zip_file_path, self.file_white_tuples)
            return
                            
        if object_names:
            print(f'Applying action "{self.action}" to files {object_names}')
            HelperMinio.apply_action_to_object_names(minioClient, self.action, self.bucket_name, run_dir, object_names, self.file_white_tuples)
        else:
            if not object_dirs:
                print(f'Applying action to whole bucket')
            else:
                print(f'Applying action "{self.action}" to files in: {object_dirs}')
                
            HelperMinio.apply_action_to_object_dirs(minioClient, self.action, self.bucket_name, run_dir, object_dirs, self.file_white_tuples)
        
        return

    def __init__(self,
        dag,
        action='get',
        bucket_name=None,
        action_operators=None,
        action_operator_dirs=None,
        action_files=None,
        minio_host='minio-service.store.svc',
        minio_port='9000',
        file_white_tuples=None,
        zip_files=False,
        *args, **kwargs
        ):
    
        if action not in ['get', 'remove', 'put']:
            raise AssertionError('action must be get, remove or put')
        
        if action == 'put':
            file_white_tuples = file_white_tuples or ('.json', '.mat', '.py', '.zip', '.txt', '.gz', '.csv', 'pdf', 'png', 'jpg')

        self.action = action
        self.bucket_name = bucket_name
        self.action_operator_dirs = action_operator_dirs or []
        self.action_operators = action_operators or []
        self.action_files = action_files or []
        self.minio_host = minio_host
        self.minio_port = minio_port
        self.file_white_tuples = file_white_tuples
        self.zip_files = zip_files
        
        super(LocalMinioOperator, self).__init__(
           dag,
           name=f'minio-actions-{action}',
           python_callable=self.start,
           execution_timeout=timedelta(minutes=30),
           *args,
           **kwargs
        )