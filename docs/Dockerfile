FROM local-only/base-python-cpu:latest

LABEL IMAGE="kaapana-documentation"
LABEL VERSION="0.1.2"
LABEL BUILD_IGNORE="False"

COPY ./ /src
WORKDIR /src

# RUN apk add --update alpine-sdk zlib-dev jpeg-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev

RUN python3 -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r requirements.txt
RUN make html


###############################
######### Production ##########
###############################
FROM docker.io/nginx:1.25.4-alpine

COPY --from=build-stage /src/build/html/ /usr/share/nginx/html/
