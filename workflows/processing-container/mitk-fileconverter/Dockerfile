FROM local-only/mitk-phenotyping:2021-02-18-vdev

LABEL IMAGE="mitk-fileconverter"
LABEL VERSION="2021-02-18-vdev"
LABEL CI_IGNORE="False"

ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV OPERATOR_OUT_DIR mitk-fileconverter

# nrrd nii nii.gz
ENV CONVERTTO nrrd 
ENV CONVERTFROM dcm
ENV FORCE_SINGLE_FILE false
ENV FILECONVERTER /src/MitkFileConverter.sh

COPY files/mitk_fileconverter.sh /mitk_fileconverter.sh

CMD ["/bin/bash", "/mitk_fileconverter.sh"]

#  docker run --rm -it -e OPERATOR_IN_DIR="" -e CONVERTTO=nifti dktk-jip-registry.dkfz.de/public/mitk-fileconverter
