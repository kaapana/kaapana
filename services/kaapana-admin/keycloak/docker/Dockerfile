# Stage 1: Adapt the proxy settings in settings.xml
FROM local-only/base-python-cpu:latest AS settings

RUN apt-get update && apt-get install -y curl xmlstarlet

ARG http_proxy="false"

ENV HTTP_PROXY=$http_proxy

ADD files/settings.xml /tmp/settings.xml
ADD files/change_settings.sh .

RUN bash change_settings.sh

# Stage 2: Build the Maven project
FROM maven:3.8.1-openjdk-17 AS maven-builder

COPY --from=settings /tmp/settings.xml /root/.m2/settings.xml

ADD projects-token-mapper /app/projects-token-mapper
ADD rights-token-mapper /app/rights-token-mapper
ADD admin-mapper /app/admin-mapper

WORKDIR /app/projects-token-mapper
RUN mvn clean package

WORKDIR /app/rights-token-mapper
RUN mvn clean package

WORKDIR /app/admin-mapper
RUN mvn clean package

# Stage 3: Clone the Keycloak repo and adjust the theme
FROM local-only/base-python-cpu:latest AS builder

WORKDIR /app
RUN git clone --single-branch --depth 1 --branch 23.0.4 https://github.com/keycloak/keycloak.git /app/keycloak-repo
RUN cp -r /app/keycloak-repo/themes/src/main/resources/theme/keycloak/ /app/kaapana
COPY files/login.css /app/kaapana/login/resources/css/login.css
COPY files/login.jpg /app/kaapana/login/resources/img/kaapana-bg.png
COPY files/template.ftl /app/kaapana/login/template.ftl

## Fix for update to 23.0.4 -> https://github.com/keycloak/keycloak/issues/12719#issuecomment-1858575991
## Paths changed after 26.0.6 -> https://www.keycloak.org/docs/26.0.0/upgrading/#paths-for-common-theme-resources-have-changed
RUN sed -i '/^stylesCommon=/c\stylesCommon=vendor/patternfly-v4/patternfly.min.css vendor/patternfly-v3/css/patternfly.min.css vendor/patternfly-v3/css/patternfly-additions.min.css lib/pficon/pficon.css' /app/kaapana/login/theme.properties

# Stage 4: Build the final Keycloak image with the custom theme and provider
FROM quay.io/keycloak/keycloak:26.0.6
LABEL IMAGE="keycloak"
LABEL VERSION="26.0.6"
LABEL BUILD_IGNORE="False"

COPY --from=builder /app/kaapana /opt/keycloak/themes/kaapana
COPY --from=maven-builder /app/rights-token-mapper/target/kaapana-rights-token-mapper-1.0.jar /opt/keycloak/providers/kaapana-rights-token-mapper-1.0.jar
COPY --from=maven-builder /app/projects-token-mapper/target/kaapana-projects-token-mapper-1.0.jar /opt/keycloak/providers/kaapana-projects-token-mapper-1.0.jar
COPY --from=maven-builder /app/admin-mapper/target/kaapana-admin-mapper-1.0.jar /opt/keycloak/providers/kaapana-admin-mapper-1.0.jar


RUN /opt/keycloak/bin/kc.sh build
