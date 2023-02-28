import json
import os
import shutil
from pathlib import Path
from typing import List, Dict

import nibabel as nib
import numpy as np

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalCombineMasksOperator(KaapanaPythonBaseOperator):
    """
    Merges multiple nifiti segmentation masks into a single segmentation mask file.
    Expects a seg_info.json file, which contains the following structure:
    >>>{
    >>>    "seg_info": [
    >>>        {
    >>>          "label_int": 1,
    >>>          "label_name": "spleen"
    >>>        },
    >>>        {
    >>>            ...
    >>>        }
    >>>    ]
    >>>}
    The single-mask nifti files are expected to have the same name as the entry in the seg_info.json file, i.e. the
    segmentation mask for spleen is expected to be called spleen.nii.gz
    """

    @staticmethod
    def combine_masks_to_multilabel_file(masks_dir: Path, output_file: Path):
        """
        Given the Path to the directory which contains all the masks, the method will produce a single multi-mask
        nifti.

        :param masks_dir: Path to the directory containing all the masks
        :type masks_dir: Path

        :param output_file: Path to the file, where the single multi-mask segmentation nifti should be stored.
        :type output_file: Path
        """
        masks_dir: Path = Path(masks_dir)
        masks: List[Path] = list(masks_dir.glob('*.nii.gz'))
        ref_img = nib.load(masks[0])
        img_out = np.zeros(ref_img.shape).astype(np.uint8)
        if not (masks_dir / 'seg_info.json').exists():
            print('WARNING: seg_info.json does not exist.')
            class_map = {
                i: mask_path.name.replace('.nii.gz', '')
                for i, mask_path in enumerate(sorted(masks))
            }
        else:
            with open(masks_dir / 'seg_info.json') as f:
                seg_info = json.load(f)['seg_info']
            class_map: Dict[int, str] = {
                entry['label_int']: entry['label_name']
                for entry in seg_info
            }

        for idx, mask in class_map.items():
            if os.path.exists(f"{masks_dir}/{mask}.nii.gz"):
                img = nib.load(f"{masks_dir}/{mask}.nii.gz").get_fdata()
            else:
                print(f"Mask {mask} is missing. Filling with zeros.")
                img = np.zeros(ref_img.shape)
            img_out[img > 0.5] = idx

        nib.save(nib.Nifti1Image(img_out, ref_img.affine), output_file)

    def start(self, ds, **kwargs):
        run_id = kwargs['dag_run'].run_id
        batch_folders = list(Path(self.airflow_workflow_dir, run_id, self.batch_name).glob('*'))

        for batch_element_dir in batch_folders:
            element_input_dir = batch_element_dir / self.operator_in_dir
            element_output_dir = batch_element_dir / self.operator_out_dir

            element_output_dir.mkdir(exist_ok=True)

            # The processing algorithm
            print(
                f'Converting multiple single-mask nifti files from {str(element_input_dir)} to a single multi-mask '
                f'nifti file and writing results to {str(element_output_dir)}'
            )

            LocalCombineMasksOperator.combine_masks_to_multilabel_file(
                element_input_dir,
                (element_output_dir / f'{batch_element_dir.name}.nii.gz').absolute()
            )

            if (element_input_dir / 'seg_info.json').exists():
                shutil.copy(element_input_dir / 'seg_info.json', element_output_dir)

    def __init__(self,
                 dag,
                 name='combine-masks',
                 **kwargs):

        super().__init__(
            dag=dag,
            name=name,
            python_callable=self.start,
            **kwargs
        )
