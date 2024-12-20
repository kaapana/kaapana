import os
from glob import glob

def findTarFiles(root_folder):
    # List to store the parent folder and file names
    result = []

    # Use glob to find all .tar files in the root_folder and its subdirectories
    tar_files = glob(f"{root_folder}/**/*.tar", recursive=True)

    # Iterate through the list of .tar files found
    for file_path in tar_files:
        # Extract the parent folder's name
        parent_folder_name = os.path.basename(os.path.dirname(file_path))

        # Append the parent folder and file name to the list
        result.append(os.path.join(parent_folder_name, os.path.basename(file_path)))

    return result

def getCheckpoints():
    checkpoints = findTarFiles("/kaapana/mounted/workflows/models/classification-training-workflow")
#    checkpoints = [f.removesuffix(".pth.tar") for f in tar_files]
    return checkpoints
