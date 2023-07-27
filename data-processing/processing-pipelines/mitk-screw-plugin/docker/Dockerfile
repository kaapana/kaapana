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
COPY /src/mitk.tar.gz /src/
RUN mkdir -p /mitk
RUN tar -xzf /src/mitk.tar.gz --strip 1 -C /mitk/ && rm -rf /src/mitk.tar.gz
COPY /files/requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt


# Application start definition, here a shell script is used to start the application
COPY files/startMITK.sh /root/Desktop/
RUN chmod 0777 /root/Desktop/startMITK.sh

# Download public model from zenodo
RUN mkdir /kaapana/models && mkdir /kaapana/models/mitk-screw-plugin && mkdir /kaapana/models/mitk-screw-plugin/verse && mkdir /kaapana/models/mitk-screw-plugin/screws
RUN touch /kaapana/models/mitk-screw-plugin/screws/nnUNet.zip && touch /kaapana/models/mitk-screw-plugin/screws/Dataset999_Thoracic_Lumbar_Screws.zip
RUN curl 'https://hub.dkfz.de/remote.php/webdav/Documents/AIHProject/models/nnUNet.zip' \
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
  -H 'Accept-Language: en-US,en;q=0.9' \
  -H 'Connection: keep-alive' \
  -H 'Cookie: oc_sessionPassphrase=sHnUYWpTLL8ZN0qTwDK2fZtPJg6LP0sBRerJKsP1iGt58CZgxkR%2BteiJMP8OR1ZIDmJDQMArnA%2BPlcUBsDjBOs1ZSDOu%2Bc8hJqC61lxKe9MkFS3daYe8HBp2PRVO6Gu3; __Host-nc_sameSiteCookielax=true; __Host-nc_sameSiteCookiestrict=true; ocnmipoirsic=b57do4joe5qsncdv8b7go4edkq; nc_username=6678DDF7-A414-47A9-8F9E-B93561C9D8DB; nc_token=20au%2BJNsVzKAWpYzoAY8ZaPjoEzO2QBY; nc_session_id=b57do4joe5qsncdv8b7go4edkq' \
  -H 'Sec-Fetch-Dest: document' \
  -H 'Sec-Fetch-Mode: navigate' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'Sec-Fetch-User: ?1' \
  -H 'Upgrade-Insecure-Requests: 1' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Linux"' \
  --compressed -o /kaapana/models/mitk-screw-plugin/verse/nnUNet.zip
RUN curl 'https://hub.dkfz.de/s/pwpLCeAsHYaRHwx/download/Dataset999_Thoracic_Lumbar_Screws.zip' \
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
  -H 'Accept-Language: en-US,en;q=0.9' \
  -H 'Connection: keep-alive' \
  -H 'Cookie: oc_sessionPassphrase=sHnUYWpTLL8ZN0qTwDK2fZtPJg6LP0sBRerJKsP1iGt58CZgxkR%2BteiJMP8OR1ZIDmJDQMArnA%2BPlcUBsDjBOs1ZSDOu%2Bc8hJqC61lxKe9MkFS3daYe8HBp2PRVO6Gu3; __Host-nc_sameSiteCookielax=true; __Host-nc_sameSiteCookiestrict=true; ocnmipoirsic=b57do4joe5qsncdv8b7go4edkq; nc_username=6678DDF7-A414-47A9-8F9E-B93561C9D8DB; nc_token=20au%2BJNsVzKAWpYzoAY8ZaPjoEzO2QBY; nc_session_id=b57do4joe5qsncdv8b7go4edkq' \
  -H 'Sec-Fetch-Dest: document' \
  -H 'Sec-Fetch-Mode: navigate' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'Sec-Fetch-User: ?1' \
  -H 'Upgrade-Insecure-Requests: 1' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Linux"' \
  --compressed -o /kaapana/models/mitk-screw-plugin/screws/Dataset999_Thoracic_Lumbar_Screws.zip

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
