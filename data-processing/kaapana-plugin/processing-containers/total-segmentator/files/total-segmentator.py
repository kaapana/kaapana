import glob
import os

# From the template
from subprocess import run, PIPE

batch_folders = sorted(
    [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

for batch_element_dir in batch_folders:

    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    # The processing algorithm
    print(f'Checking {element_input_dir} for nifti files and writing results to {element_output_dir}')
    nifti_files = sorted(glob.glob(os.path.join(element_input_dir, "*.nii.gz"), recursive=True))

    if len(nifti_files) == 0:
        print("No nifti file found!")
        exit(0)
    else:
        for nifti_file in nifti_files:

            print(f"# running total segmentator")
            command = ["TotalSegmentator", f'-i {nifti_file}', f'-o {element_output_dir}']
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=320)

            if output.returncode != 0:
                print("# Could process")
                print(output)
                exit(1)
            else:
                print("# Sucessfully processed")

