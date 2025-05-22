import glob
import os
from liver_segmentation_workflow import execute

if __name__ == '__main__':
    batch_folders = sorted(
        [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

    for batch_element_dir in batch_folders:
        element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
        element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])

        output_file = os.path.join(element_output_dir, "{}.nii.gz".format(os.path.basename(batch_element_dir)))

        if not os.path.exists(element_output_dir):
            os.makedirs(element_output_dir)

        nrrd_files = sorted(glob.glob(os.path.join(element_input_dir, "*.nii.gz"), recursive=True))

        if len(nrrd_files) == 0:
            print("No nii file found!")
            exit(1)
        else:
            for file in nrrd_files:
                execute(file, output_file)
