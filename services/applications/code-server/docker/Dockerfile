FROM codercom/code-server:3.9.1

LABEL IMAGE="code-server"
LABEL VERSION="3.9.1"
LABEL CI_IGNORE="False"

user root
# ubuntu installations (e.g. Python)
RUN sudo -E apt-get update && sudo -E apt-get install -y \
    python3 \
    python3-pip \
 && sudo rm -rf /var/lib/apt/lists/*
# python requirements
COPY files/requirements.txt /
RUN python3 -m pip install --no-cache-dir -r /requirements.txt && rm /requirements.txt 
user coder
# extensions to code-server
# RUN code-server --install-extension ms-python.python

#v2020.10.332292344 
# RUN curl https://extensions.coder.com/api/publishers/ms-python/vsextensions/python/2020.10.332292344/vspackage --output /tmp/python.vsix \
# RUN curl https://open-vsx.org/api/ms-python/python/2020.10.332292344/file/ms-python.python-2020.10.332292344.vsix --output /tmp/python.vsix \
# RUN curl https://extensions.coder.com/api/publishers/ms-python/vsextensions/python/2021.1.502429796/vspackage --output /tmp/python.vsix \
#     && code-server --install-extension /tmp/python.vsix \
#     && rm -rf /tmp/python.vsix

CMD ["code-server", "--allow-http", "--no-auth"]
