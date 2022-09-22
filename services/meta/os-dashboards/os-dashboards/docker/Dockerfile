FROM opensearchproject/opensearch-dashboards:2.2.0

LABEL IMAGE="os-dashboards"
LABEL VERSION="2.2.0"
LABEL CI_IGNORE="False"

WORKDIR /usr/share/opensearch-dashboards/

ADD files/workflowTrigger-2.2.0.zip /workflowTrigger-2.2.0.zip
RUN bin/opensearch-dashboards-plugin install file:///workflowTrigger-2.2.0.zip

ADD files/kaapana.svg /usr/share/opensearch-dashboards/src/core/server/core_app/assets/kaapana.svg
ADD files/kaapana_mono.svg /usr/share/opensearch-dashboards/src/core/server/core_app/assets/kaapana_mono.svg
ADD files/kaapana_mono_2.svg /usr/share/opensearch-dashboards/src/core/server/core_app/assets/kaapana_mono_2.svg
ADD files/loading.png /usr/share/opensearch-dashboards/src/core/server/core_app/assets/loading.png

RUN /usr/share/opensearch-dashboards/bin/opensearch-dashboards-plugin remove securityDashboards
# COPY --chown=opensearch-dashboards:opensearch-dashboards opensearch_dashboards.yml /usr/share/opensearch-dashboards/config/

