# use base python CPU image since pyradiomics doesn't utilize GPU
FROM local-only/base-python-cpu:latest

# name and version of the processing container image
LABEL IMAGE="pyradiomics-extract-features"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

# set working dir inside container
WORKDIR /app

# copy files into the container
COPY requirements.txt .
COPY extract_features.py .

# install required python packages
RUN pip install --no-cache-dir -r requirements.txt

# run the script
CMD ["python", "extract_features.py"]
