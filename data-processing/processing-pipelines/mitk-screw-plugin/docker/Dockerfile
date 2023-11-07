FROM local-only/no-vnc-base-ubuntu22.04:latest
#FROM local-only/base-python-gpu:latest
LABEL IMAGE="mitk-screw-plugin"
LABEL VERSION="2023-01-24"
LABEL CI_IGNORE="False"
# RUN apk add build-base python-dev py-pip jpeg-dev zlib-dev
# ENV LIBRARY_PATH=/lib:/usr/lib
# libnspr4 libnss3-tools
WORKDIR /
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip && pip3 install --upgrade pip

WORKDIR /mitk
RUN mkdir -p /mitk  
RUN curl https://hub.dkfz.de/s/e87pCA2cJqfbsyB/download/mitk.tar.gz --compressed -o /mitk/mitk.tar.gz
RUN tar -xzf /mitk/mitk.tar.gz --strip 1 -C /mitk/ && rm -rf /mitk/mitk.tar.gz
COPY /files/requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt


# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /root/Desktop/
RUN chmod 0777 /root/Desktop/startMITK.sh

# Download public model from zenodo
RUN mkdir /kaapana/models && mkdir /kaapana/models/mitk-screw-plugin && mkdir /kaapana/models/mitk-screw-plugin/verse && mkdir /kaapana/models/mitk-screw-plugin/screws
RUN touch /kaapana/models/mitk-screw-plugin/screws/nnUNet.zip && touch /kaapana/models/mitk-screw-plugin/screws/Dataset999_Thoracic_Lumbar_Screws.zip
RUN curl https://hub.dkfz.de/s/iQEFRxXFseEJfLq/download/nnUNet.zip --compressed -o /kaapana/models/mitk-screw-plugin/verse/nnUNet.zip
RUN curl https://hub.dkfz.de/s/pwpLCeAsHYaRHwx/download/Dataset999_Thoracic_Lumbar_Screws.zip --compressed -o /kaapana/models/mitk-screw-plugin/screws/Dataset999_Thoracic_Lumbar_Screws.zip
RUN unzip /kaapana/models/mitk-screw-plugin/verse/nnUNet.zip -d /kaapana/models/mitk-screw-plugin/verse/
RUN unzip /kaapana/models/mitk-screw-plugin/screws/Dataset999_Thoracic_Lumbar_Screws.zip -d /kaapana/models/mitk-screw-plugin/screws/
RUN rm /kaapana/models/mitk-screw-plugin/verse/nnUNet.zip & rm /kaapana/models/mitk-screw-plugin/screws/Dataset999_Thoracic_Lumbar_Screws.zip


#RUN apt install -y libnss3 libglib2.0-0 libfreetype6 libfontconfig
#RUN apt install -y libx11-6 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxi6 libxtst6 libasound2 libdbus-1-3 libgl1
#libx11-xcb1 '^libxcb.*-dev' libx11-xcb-dev libglu1-mesa-dev libxrender-dev libxi-dev libxkbcommon-dev libxkbcommon-x11-dev
#RUN apt install -y '^libxcb.*-dev' libx11-xcb-dev libglu1-mesa-dev libxrender-dev libxi-dev libxkbcommon-dev libxkbcommon-x11-dev

#RUN mkdir /opt/data
#RUN mkdir /opt/models

# A supervisord config is used to make the application managed
#COPY files/supervisord.conf /etc/supervisor/conf.d/

#CMD ["/kaapanasrc/MitkWorkbench.sh"]
