import sys, os
import glob
import json
from medpy.io import load, save
from datetime import datetime

# For local testng

# os.environ["WORKFLOW_DIR"] = "<your data directory>"
# os.environ["BATCH_NAME"] = "batch"
# os.environ["OPERATOR_IN_DIR"] = "initial-input"
# os.environ["OPERATOR_OUT_DIR"] = "output"

# From the template
batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

for batch_element_dir in batch_folders:
    
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    # The processing algorithm
    print(f'Checking {element_input_dir} for dcm files and writing results to {element_output_dir}')
    nrrd_files = sorted(glob.glob(os.path.join(element_input_dir, "*.nrrd*"), recursive=True))

    if len(nrrd_files) == 0:
        print("No dicom file found!")
        exit(1)
    else:
        print(("Normalizing image: %s" % nrrd_files))

        image, hdr = load(nrrd_files[0])
        mean_img = image.mean()
        std_img = image.std()
        norm_image = (image - mean_img) / std_img

        print('Mean: {}'.format(mean_img))
        print('Std: {}'.format(std_img))

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
