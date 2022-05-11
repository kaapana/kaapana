FROM local-only/base-python-alpine:0.1.0 as build-stage

LABEL IMAGE="kaapana-documentation"
LABEL VERSION="0.1.2"
LABEL CI_IGNORE="False"

COPY ./ /src
WORKDIR /src

# Has to stay!
RUN apk add --update alpine-sdk zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev

RUN python3 -m pip install --no-cache-dir -r requirements.txt
RUN make html

###############################
######### Production ##########
###############################
FROM nginx:1.19.3-alpine

COPY --from=build-stage /src/build/html/ /usr/share/nginx/html/
