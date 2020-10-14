FROM lassoan/slicer-notebook:2020-05-15-89b6bb5

LABEL IMAGE="slicer-jl"
LABEL VERSION="2020-05-15-89b6bb5"
LABEL CI_IGNORE="False"


RUN jupyter notebook --generate-config \
 && sed -i "s/^.*NotebookApp.token.*$/c.NotebookApp.token = ''/g" /home/sliceruser/.jupyter/jupyter_notebook_config.py

RUN git clone https://github.com/Slicer/SlicerNotebooks.git /home/sliceruser/work/examples
COPY files/jupyterlab.sh /home/sliceruser/

CMD ["/bin/bash", "/home/sliceruser/jupyterlab.sh"]

