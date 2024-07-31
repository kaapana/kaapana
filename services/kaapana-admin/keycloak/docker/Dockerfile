# Stage 1: Build the Maven project
FROM maven:3.8.1-openjdk-17 AS maven-builder

ADD projects-token-mapper /app/projects-token-mapper
ADD rights-token-mapper /app/rights-token-mapper
ADD admin-mapper /app/admin-mapper

WORKDIR /app/projects-token-mapper
RUN mvn clean package

WORKDIR /app/rights-token-mapper
RUN mvn clean package

WORKDIR /app/admin-mapper
RUN mvn clean package

# Stage 2: Clone the Keycloak repo and adjust the theme
FROM local-only/base-python-cpu:latest as builder

WORKDIR /app
RUN git clone --single-branch --depth 1 --branch 23.0.4 https://github.com/keycloak/keycloak.git /app/keycloak-repo
RUN cp -r /app/keycloak-repo/themes/src/main/resources/theme/keycloak/ /app/kaapana
COPY files/login.css /app/kaapana/login/resources/css/login.css
COPY files/login.jpg /app/kaapana/login/resources/img/kaapana-bg.png

## Fix for update to 23.0.4 -> https://github.com/keycloak/keycloak/issues/12719#issuecomment-1858575991
RUN sed -i '/^stylesCommon=/c\stylesCommon=node_modules/@patternfly/patternfly/patternfly.min.css node_modules/patternfly/dist/css/patternfly.min.css node_modules/patternfly/dist/css/patternfly-additions.min.css lib/pficon/pficon.css' /app/kaapana/login/theme.properties

# Stage 3: Build the final Keycloak image with the custom theme and provider
FROM quay.io/keycloak/keycloak:23.0.4
LABEL IMAGE="keycloak"
LABEL VERSION="23.0.4"
LABEL BUILD_IGNORE="False"

COPY --from=builder /app/kaapana /opt/keycloak/themes/kaapana
COPY --from=maven-builder /app/rights-token-mapper/target/kaapana-rights-token-mapper-1.0.jar /opt/keycloak/providers/kaapana-rights-token-mapper-1.0.jar
COPY --from=maven-builder /app/projects-token-mapper/target/kaapana-projects-token-mapper-1.0.jar /opt/keycloak/providers/kaapana-projects-token-mapper-1.0.jar
COPY --from=maven-builder /app/admin-mapper/target/kaapana-admin-mapper-1.0.jar /opt/keycloak/providers/kaapana-admin-mapper-1.0.jar


RUN /opt/keycloak/bin/kc.sh build
