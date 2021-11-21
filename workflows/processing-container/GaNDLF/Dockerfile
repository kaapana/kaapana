FROM  python:3.7
ENV http_proxy http://www-int2.dkfz-heidelberg.de:80
ENV https_proxy http://www-int2.dkfz-heidelberg.de:80


LABEL IMAGE="gandlf-workflow"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="True"

RUN apt update -y
RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN apt upgrade -y
WORKDIR /
#COPY files/run_tests.py /

RUN apt-get install git -y
RUN git clone https://github.com/CBICA/GaNDLF.git
RUN pip3 install pydicom
RUN pip3 install requests
RUN pip3 install torch==1.10.0+cpu torchvision==0.11.1+cpu torchaudio==0.10.0+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html
#RUN cd GaNDLF/
COPY files/run_tests.py GaNDLF/
RUN pip install -e GaNDLF/
#RUN cd GaNDLF/
#CMD ["/bin/bash", "-c" "pytest "]
#CMD ["/bin/bash", "/run.sh"]
#RUN ./run.sh
WORKDIR '/GaNDLF'
#COPY ../run_tests.py .
CMD ["python3","-u", "run_tests.py"]

#RUN ["/bin/bash", "-c","pytest > output.txt"]
#cd
#CMD ["/bin/bash", "-c" "pytest"]