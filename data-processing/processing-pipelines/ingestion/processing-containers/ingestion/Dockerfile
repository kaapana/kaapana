FROM local-only/base-python-cpu:latest

LABEL IMAGE="extractorlib"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

RUN echo "git+ssh://git@codebase.helmholtz.cloud:philipp.schader/extractors.git@integration#egg=extractorlib" > requirements.txt && \
	echo "git+ssh://git@codebase.helmholtz.cloud:philipp.schader/extractors.git@integration#egg=extractorlib-plugin-dicom" >> requirements.txt && \
	echo "git+ssh://git@codebase.helmholtz.cloud:philipp.schader/extractors.git@integration#egg=extractorlib-plugin-minio" >> requirements.txt
RUN pip install --no-cache-dir -r requirements.txt