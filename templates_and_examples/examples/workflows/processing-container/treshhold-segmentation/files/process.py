import SimpleITK as sitk  # pip install SimpleITK

import sys, os
import glob

batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

for batch_element_dir in batch_folders:
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])

    print('Here you find the files you want to work with on a batch element level')
    print(element_input_dir)
    nrrd_files = sorted(glob.glob(os.path.join(element_input_dir, "*.nrrd*"), recursive=True))

    assert len(nrrd_files) == 1
    img = sitk.ReadImage(nrrd_files[0])
    seg = sitk.OtsuThreshold(img, 0, 1)

    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    print('Here you should write the files that you generate on a batch element level')
    print(element_output_dir)
    
    sitk.WriteImage(seg, os.path.join(element_output_dir, 'entire_body.nrrd'), useCompression=True)


