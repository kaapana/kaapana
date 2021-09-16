FROM python:3.9-alpine3.12 as build-stage

LABEL IMAGE="kaapana-documentation"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

COPY ./ /src
WORKDIR /src

RUN apk add --update alpine-sdk zlib-dev jpeg-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev

RUN python3 -m pip install --no-cache-dir -r requirements.txt
RUN make html


###############################
######### Production ##########
###############################
FROM nginx:1.19.3-alpine

COPY --from=build-stage /src/build/html/ /usr/share/nginx/html/
