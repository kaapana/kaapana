FROM docker.elastic.co/kibana/kibana-oss:6.8.12

LABEL IMAGE="kibana-kaapana"
LABEL VERSION="6.8.12"
LABEL CI_IGNORE="False"

WORKDIR /usr/share/kibana/

USER root

ADD files/workflow_trigger-0.0.2.zip /workflow_trigger-0.0.2.zip
RUN bin/kibana-plugin install file:///workflow_trigger-0.0.2.zip

USER kibana

COPY files/replace_files/ui_app.pug /usr/share/kibana/src/ui/ui_render/views/ui_app.pug
COPY files/replace_files/logo.png /usr/share/kibana/optimize/bundles/logo.png
COPY files/replace_files/commons.style.css /usr/share/kibana/optimize/bundles/commons.style.css
COPY files/replace_files/index.css /usr/share/kibana/built_assets/css/plugins/kibana/index.css

