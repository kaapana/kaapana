import os
import sys
from  glob import glob 
import nibabel as nib
import numpy as np


  
if len(sys.argv) != 2:
    print("please pass the nifti-file-path as argument!")
    exit(1) 
  
nifti = glob(os.path.join(sys.argv[1],'*.nii.gz'))

if len(nifti) != 1:
    print("could not find a single segmentation NIFTI @{}".format(sys.argv[1]))
    print("ABORT")
    exit(1)

img = nib.load(nifti)
if np.max(img.get_fdata()) == 0:
    print("Could not find any label in {}!".format(nifti))
    print("ABORT")
    exit(1)
else:
    print("Label found -> ok !")
    exit(0)