FROM local-only/base-mitk:latest

LABEL IMAGE="seg-check"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIRS initial-input
ENV ORIGINAL_IN_DIR ""
ENV FORMAT "nii.gz"
ENV OPERATOR_OUT_DIR seg-check
#0=linear (default), 1=nearest neighbor, 2=sinc (optional), (default: 0), Type: Int
ENV INTERPOLATOR 1 
ENV ORG_IMG_IN_DIR ""

ENV EXECUTABLE /kaapana/app/apps/MitkMapImage.sh

COPY files/start.py /kaapana/app/
CMD ["python3","-u","/kaapana/app/start.py"]


# ./MitkMapImage.sh 
# Running Command Line Utility *Map Image*
# Command Line Utility *Map Image* in Category *Registration Tools*
# MiniApp that allows to map a image into a given output geometry by using a given registration.
# MIC, German Cancer Research Center (DKFZ)

# Use --xml to generate an XML description parsable as a CTK Command Line Module Plugin.
# Use --version to print MITK revision information.

# Optional parameters
#   -r, --registration, Path to the registration that should be used. If no registration is specified, an identity transform is assumed. (optional), Type: File, Channel: input
#   -t, --template, File path to an image that serves as template for the output geometry. If no template is specified, the geometry of the input image will be used., Type: File, Channel: input
#   -n, --interpolator, Interpolator used for mapping the images. Default: 2; allowed values: 1: Nearest Neighbour, 2: Linear, 3: BSpline 3, 4: WSinc Hamming, 5: WSinc Welch (optional), (default: 2), Type: Int
#   -p, --padding, Value used for output voxels that are not covered by any input image. (optional), (default: 0), Type: Float
#   -s, --super-sampling, Value used for super sampling of the result. E.g. factor 2 will lead to a doubled resolution compared to the used template. If not specified, no super sampling will be done. (optional), Type: StringList
#   -h, --help, Show this help text (optional), Type: Bool

# Required I/O parameters
#   -i, --input, Path to the input images that should be mapped, Type: File, Channel: input
#   -o, --output, Path to the mapped image., Type: File, Channel: output