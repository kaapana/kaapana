FROM local-only/base-python-cpu:latest AS build-stage

LABEL IMAGE="kaapana-documentation"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

COPY ./ /src
WORKDIR /src

# RUN apk add --update alpine-sdk zlib-dev jpeg-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev

RUN python3 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r requirements.txt
RUN make html


###############################
######### Production ##########
###############################
FROM nginxinc/nginx-unprivileged:1.27.2-alpine
WORKDIR /app

COPY --from=build-stage /src/build/html/ /app/docs
COPY files/nginx.conf /etc/nginx/nginx.conf

USER 1000