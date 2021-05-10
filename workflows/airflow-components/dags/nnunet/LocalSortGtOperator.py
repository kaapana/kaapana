import os
from os.path import join, exists, basename, dirname
from glob import glob
import json
import shutil
import pydicom
from pydicom.uid import generate_uid
from pathlib import Path
from shutil import copy2, move, rmtree

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import WORKFLOW_DIR

class LocalSortGtOperator(KaapanaPythonBaseOperator):
    def start(self, ds, **kwargs):
        print("Starting LocalSortGtOperator ...")
        print(kwargs)

        run_dir = join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_dirs = [f for f in glob(join(run_dir, self.batch_name, '*'))]

        print(f"# Found {len(batch_dirs)} batch elements...")
        base_images_list = {}
        for batch_element_dir in batch_dirs:
            print(f"# Processing: {batch_element_dir}")
            batch_el_dcm_files = sorted(glob(join(batch_element_dir, self.operator_in_dir, "*.dcm"), recursive=True))
            assert len(batch_el_dcm_files) > 0

            for seg_dicom_path in batch_el_dcm_files:
                incoming_dcm = pydicom.dcmread(seg_dicom_path)
                assert (0x0008, 0x1115) in incoming_dcm

                for ref_series in incoming_dcm[0x0008, 0x1115]:
                    assert (0x0020, 0x000E) in ref_series
                    ref_ct_id = str(ref_series[0x0020, 0x000E].value)

                    if ref_ct_id not in base_images_list:
                        print(f"#### Adding new base_image: {ref_ct_id}")
                        base_images_list[ref_ct_id] = []
                    else:
                        print(f"#### base_image: {ref_ct_id} already exists in list ...")
                    base_images_list[ref_ct_id].append(seg_dicom_path)
        
        for base_image,corr_batch_elements in base_images_list.items():
            print(f"# Found base_image with {len(corr_batch_elements)} corresponding segmentation...")
            assert len(corr_batch_elements) != 0
            
            if len(corr_batch_elements) == 1:
                corr_seg_file = corr_batch_elements[0]
                org_input_dir = dirname(corr_seg_file)
                new_batch_element_name = join(run_dir, self.batch_name,base_image,self.operator_in_dir)

                print(f"# Only one corresponding image -> change batch_element name to base_id ..")
                print(f"# {org_input_dir} -> {new_batch_element_name}")
                move(org_input_dir,new_batch_element_name)
                print(f"#")
                print(f"#")
            else:
                print(f"# Merging started...")
                target_series_batch = join(run_dir, self.batch_name,f"{base_image}_merged",self.operator_in_dir)
                Path(target_series_batch).mkdir(parents=True, exist_ok=True)
                for corr_image in corr_batch_elements:
                    target_seg_path = join(target_series_batch,basename(corr_image))
                    print(f"# copy {corr_image} -> {target_seg_path}")
                    move(src=corr_image,dst=target_seg_path)
            print(f"#")
        
        print(f"# Merging done.")
        print(f"#")
                
        for base_image,corr_batch_elements in base_images_list.items():
            for corr_image in corr_batch_elements:
                org_batch_element_dir = dirname(dirname(corr_image))
                print(f"# Removing outdated batch-dir: {org_batch_element_dir}")
                rmtree(path=org_batch_element_dir,ignore_errors=True)
                print(f"# ")
        print(f"# Done.")




    def __init__(self,
                 dag,
                 name='sort-gt',
                 *args, **kwargs):

        super().__init__(
            dag,
            name=name,
            python_callable=self.start,
            *args, **kwargs
        )
