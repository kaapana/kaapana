import sys, os
import glob
import json
from medpy.io import load, save
from datetime import datetime
import numpy as np

# For local testng

# os.environ["WORKFLOW_DIR"] = '/home/kleina/Documents/blubb/aa-myeloma-radiomics-210624144757451535'
# os.environ["BATCH_NAME"] = "batch"
# os.environ["OPERATOR_IN_DIR"] = "dcm-converter"
# os.environ["MASK_OPERATOR_DIR"] = "dcmseg2nrrd"
# os.environ["OPERATOR_OUT_DIR"] = "output"

# From the template
batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

for batch_element_dir in batch_folders:
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    element_mask_dir = os.path.join(batch_element_dir, os.environ['MASK_OPERATOR_DIR'])
    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    # The processing algorithm
    print(f'Checking {element_input_dir} for images and {element_mask_dir} for reference tissue. Writing results to {element_output_dir}')
    nrrd_files = sorted(glob.glob(os.path.join(element_input_dir, "*.nrrd*"), recursive=True))
    mask_files = sorted(glob.glob(os.path.join(element_mask_dir, "*.nrrd*"), recursive=True))

    mask_k_file = ''
    mask_m_file = ''
    for mask in mask_files:
        if mask.endswith('4--ref_k@pelvis.nrrd'):
            mask_k_file = mask
        if mask.endswith('5--ref_m@pelvis.nrrd'):
            mask_m_file = mask
            
    if len(nrrd_files) == 0:
        print("No dicom file found!")
        exit(1)
    else:
        print(("Normalizing image: %s" % nrrd_files))

        image, hdr = load(nrrd_files[0])

        mask_muscle, hdr_m = load(mask_m_file)
        mask_knochen, hdr_k = load(mask_k_file)

        mask_muscle[mask_muscle>1] = 1
        mask_knochen[mask_knochen>1] = 1
        masked_img_muscle = image * mask_muscle
        mean_muscle = masked_img_muscle[np.nonzero(masked_img_muscle)].mean()
        masked_img_knochen = image * mask_knochen
        mean_knochen = masked_img_knochen[np.nonzero(masked_img_knochen)].mean()
        norm_image = (image - mean_muscle) / (mean_knochen - mean_muscle)

        if not os.path.exists(element_output_dir):
            os.makedirs(element_output_dir)

        norm_file_path = os.path.join(element_output_dir, "{}.nrrd".format(os.path.basename(batch_element_dir)))
        print(("Saving normalized image to: %s" % norm_file_path))
        try:
            save(norm_image, norm_file_path, hdr)
        except Exception as inst:
            print('Exception during io.save')
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)  
