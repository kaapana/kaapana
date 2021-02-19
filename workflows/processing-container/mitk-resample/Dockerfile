FROM local-only/mitk-phenotyping:2021-02-18-vdev as build_container

LABEL IMAGE="mitk-resample"
LABEL VERSION="2021-02-18-vdev"
LABEL CI_IGNORE="False"

ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV ORIGINAL_IN_DIR ""
ENV FORMAT "nii.gz"
ENV OPERATOR_OUT_DIR mitk-resample
#0=linear (default), 1=nearest neighbor, 2=sinc (optional), (default: 0), Type: Int
ENV INTERPOLATOR 1 
ENV ORG_IMG_IN_DIR ""

ENV EXECUTABLE /src/MitkCLResampleImageToReference.sh

COPY files/start.sh /start.sh
CMD ["/bin/bash", "/start.sh"]

# root@cd72f914f1cd:/opt# ./MitkCLResampleImageToReference.sh 
# Running Command Line Utility *Resample Image To Reference*
# Command Line Utility *Resample Image To Reference* in Category *Classification Tools*
# Resamples an image (moving) to an given image (fix) without additional registration.
# German Cancer Research Center (DKFZ)

# Use --xml to generate an XML description parsable as a CTK Command Line Module Plugin.
# Use --version to print MITK revision information.
#   -f, --fix, fixed image file, Type: Image, Channel: input
#   -m, --moving, moving image file, Type: File, Channel: output
#   -o, --output, output image, Type: File, Channel: output
#   --interpolator, interpolator type: 0=linear (default), 1=nearest neighbor, 2=sinc (optional), (default: 0), Type: Int
