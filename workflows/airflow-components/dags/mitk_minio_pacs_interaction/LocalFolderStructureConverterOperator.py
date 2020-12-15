import os
import glob
import shutil
import pydicom
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from dicomweb_client.api import DICOMwebClient

class LocalFolderStructureConverterOperator(KaapanaPythonBaseOperator):

    def convert_to(self, **kwargs):
        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_dir = os.path.join(run_dir, BATCH_NAME)
        batch_folder = [f for f in glob.glob(os.path.join(batch_dir, '*'))]
        print('batch_folder: ', batch_folder)
        for structured_item in self.structure:
            for batch_element_dir in batch_folder:
                dcm_files = sorted(
                    glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"), recursive=True))
                if len(dcm_files) == 0:
                    print("no input files")
                    exit(1)
                file_object = self.construct_path(structured_item, dcm_files[0], None)
                file_object = file_object.encode("ascii", errors="ignore").decode() #strip non ascii
                output_folder = os.path.join(run_dir)
                target = os.path.join(output_folder, file_object)

                if not os.path.exists(target):
                    os.makedirs(target)
                if "empty_dir" in structured_item and structured_item["empty_dir"] is True:
                    print("adding directory")
                    file_id = os.path.join(target, ".keep")
                    with open(file_id, 'w'):
                        pass
                    continue
                dcm_path = os.path.dirname(dcm_files[0])
                print("COPY!")
                print("SRC: {}".format(dcm_path))
                print("TARGET: {}".format(target))

                for dcm_file in dcm_files:
                    shutil.copy(dcm_file, target)

        print("remove batch dir, after reordering all data!")
        shutil.rmtree(batch_dir)

    def replace_folder_in_path(self, target, replace_part, folder_part):
        old_tail = ""
        new_path = ""
        while True:
            head, tail = os.path.split(target)
            tail_lower = tail.lower()
            if not tail:
                print(folder_part, " not found in path")
                break
            if folder_part in tail_lower:
                new_path = os.path.join(head, replace_part)
                break
            if old_tail:
                old_tail = os.path.join(tail, old_tail)
            else:
                old_tail = tail
            target = head

        new_path = os.path.join(new_path, old_tail)
        print(new_path)
        return new_path

    def start(self, **kwargs):
        self.convert_to(**kwargs)
        # todo: implement backwards
        # if self.convert_backwards:
        #   self.convert_back(**kwargs)
        # else:
        #   self.convert_to(**kwargs)

    def construct_path(self, structlevel, dcm_file, parent_path):
        ds = pydicom.dcmread(dcm_file)
        structlevel_name = ""
        value = structlevel["value"]
        for pos in value:
            if pos["type"] == "string":
                structlevel_name += pos["value"]
                print(structlevel_name)
            elif pos["type"] == "dicom_tag":
                if pos["value"] in ds:
                    tag_value = ds[pos["value"]].value
                    if isinstance(tag_value, str):
                        structlevel_name += tag_value
                else:
                    print("dicom tag  not found! - skiping tag")
            if value.index(pos) + 1 < len(value):
                structlevel_name += "_"
        structlevel_name = structlevel_name.replace(" ", "_")
        if parent_path:
            path = os.path.join(parent_path, structlevel_name)
        else:
            path = structlevel_name
        if "children" in structlevel:
            structlevel = structlevel["children"]
            if structlevel:
                return self.construct_path(structlevel, dcm_file, path)
            else:
                return path
        else:
            return path

    def __init__(self,
                 dag,
                 name='folderStructureConverter',
                 push_operators=None,
                 structure=None,
                 *args, **kwargs):


        self.push_operators = push_operators
        self.structure = structure

        super(LocalFolderStructureConverterOperator, self).__init__(
            dag,
            name=name,
            python_callable=self.start,
            *args,
            **kwargs,
        )
