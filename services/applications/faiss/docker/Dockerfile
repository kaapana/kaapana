FROM local-only/base-python-cpu:latest

LABEL IMAGE="faiss"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app


COPY files/faiss/requirements.txt /kaapana/app/

# Install any needed packages specified in requirements.txt
RUN pip3 install --upgrade pip && pip3 install -r /kaapana/app/requirements.txt

COPY files/faiss /kaapana/app/faiss 

# todo: might has to be adjusted
EXPOSE 5000

# Run app.py when the container launches
CMD ["python", "-u", "/kaapana/app/faiss/app.py"]


