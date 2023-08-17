FROM node:lts-alpine as build-stage

LABEL IMAGE="kaapana-persistence-importer"
LABEL VERSION="1.0.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

RUN git clone --single-branch git@github.com:lucaskulla/react-spreadsheet-import.git
RUN npm ci --silent
RUN npm run build

###############################
######### Production ##########
###############################
FROM docker.io/nginx:1.23.3-alpine

WORKDIR /kaapana/app

EXPOSE 80

COPY --from=build-stage kaapana/app/build /usr/share/nginx/html

CMD ["nginx", "-g", "daemon off;"]
