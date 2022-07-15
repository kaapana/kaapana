import SimpleITK as sitk  # pip install SimpleITK
import os
import glob

# os.environ["WORKFLOW_DIR"] = "/home/l597s/Projects/MICCAI-Hackathon/example-utsos-method/data" #"<your data directory>"
# os.environ["BATCH_NAME"] = "batch"
# os.environ["OPERATOR_IN_DIR"] = "get-input-data"
# os.environ["OPERATOR_OUT_DIR"] = "output"

# From the template
batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

print(batch_folders)
for batch_element_dir in batch_folders:

    print(batch_element_dir)
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    print('input-dir:',element_input_dir)
    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)


    nddr_files = sorted(glob.glob(os.path.join(element_input_dir, "*.nrrd"), recursive=True))
    print(os.path.join(element_input_dir, "*.nrrd"))
    print("files",nddr_files)
    for file in nddr_files:

        img = sitk.ReadImage(file)
        seg = sitk.OtsuThreshold(img, 0, 1)

        output_file = os.path.join(element_output_dir, "{}.nrrd".format(os.path.basename(batch_element_dir)))
        sitk.WriteImage(seg, output_file, useCompression=True)
