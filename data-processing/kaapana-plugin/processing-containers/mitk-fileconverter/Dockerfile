FROM local-only/mitk-base:latest

LABEL IMAGE="mitk-fileconverter"
LABEL VERSION="2024-08-08"
LABEL BUILD_IGNORE="False"

ENV BATCHES_INPUT_DIR /input
ENV OPERATOR_IN_DIR initial-input
ENV OPERATOR_OUT_DIR mitk-fileconverter

# nrrd nii nii.gz
ENV CONVERTTO nrrd 
ENV CONVERTFROM dcm
ENV FORCE_SINGLE_FILE false
ENV FILECONVERTER /kaapana/app/apps/MitkFileConverter.sh

COPY files/mitk_fileconverter.py /kaapana/app/
CMD ["python3","-u", "/kaapana/app/mitk_fileconverter.py"]
