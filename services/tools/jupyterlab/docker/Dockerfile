FROM nvidia/cuda:10.2-runtime-ubuntu18.04

LABEL IMAGE="jupyterlab"
LABEL VERSION="1.0-vdev"
LABEL CI_IGNORE="False"

# Install Python and basic tools
RUN apt-get update -y && apt-get install -y \
      build-essential \
      curl \
      python3 \
      python3-all-dev \
      python3-pip \
      python3-setuptools \
      python3-venv \
      python3-wheel \
    && pip3 install --upgrade pip

# Install NodeJS: https://askubuntu.com/a/548776
RUN curl -sL https://deb.nodesource.com/setup_13.x | bash - \
 && apt-get install -y nodejs

# Common Python packages
COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

# Disable security token for Jupyter lab
RUN jupyter notebook --generate-config \
 && sed -i "s/^.*NotebookApp.token.*$/c.NotebookApp.token = ''/g" /root/.jupyter/jupyter_notebook_config.py
 #&& sed -i "s/^.*NotebookApp.base_url.*$/c.NotebookApp.base_url = '\/jupyterlab'/g" /root/.jupyter/jupyter_notebook_config.py

# Interactive plotly widgets
RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager \
 && jupyter labextension install jupyterlab-plotly \
 && jupyter labextension install plotlywidget

# Download the default BERT model and store it in the Docker container (in the directory /root/.cache/torch/transformers). This is the easiest solution for now but makes the Docker image unnecessarily large and does not scale well
#RUN python3 -c "FROM transformers import BertModel, BertTokenizer; BertModel.from_pretrained('bert-base-uncased'); BertTokenizer.from_pretrained('bert-base-uncased')"


RUN mkdir -p /appdata
COPY files/jupyterlab.sh /

EXPOSE 8888
ENV INGRESS_PATH /jupyterlab/buh/
#CMD jupyter lab --ip=* --port=8888 --no-browser --notebook-dir=/opt/app/data --allow-root

CMD ["/bin/bash", "/jupyterlab.sh"]

