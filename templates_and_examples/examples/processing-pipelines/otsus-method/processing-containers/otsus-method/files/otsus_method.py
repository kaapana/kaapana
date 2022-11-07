import SimpleITK as sitk
import os
import glob

### For local testing you can uncomment the following lines
# os.environ["WORKFLOW_DIR"] = "<your data directory>"
# os.environ["BATCH_NAME"] = "batch"
# os.environ["OPERATOR_IN_DIR"] = "get-input-data"
# os.environ["OPERATOR_OUT_DIR"] = "output"

### From the template
batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

for batch_element_dir in batch_folders:

    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])

    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)


    nddr_files = sorted(glob.glob(os.path.join(element_input_dir, "*.nrrd"), recursive=True))

    if len(nddr_files) == 0:
        print("No nrrd file found!")
        exit(1)
    else:
        for file in nddr_files:
            print(("Applying Otsus method to: %s" % file))

            ### Load image
            img = sitk.ReadImage(file)

            ### Apply Otsus method
            seg = sitk.OtsuThreshold(img, 0, 1)

            ### Save the segmentation as .nrrd file
            output_file = os.path.join(element_output_dir, "{}.nrrd".format(os.path.basename(batch_element_dir)))
            sitk.WriteImage(seg, output_file, useCompression=True)