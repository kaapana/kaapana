

# nii.gz opener
import nibabel as nib
import numpy as np

def main(path):
    file = nib.load(path)
    data = file.get_fdata()
    print("data: \n", data)
    print("range: \n", np.unique(data))

# path = "/media/j870n/Data/prostate_mri/BMC/Case05_Segmentation.nii.gz"
# path = "/media/j870n/Data/prostate_mri/RUNMC/Case00_segmentation.nii.gz"
main(path)
