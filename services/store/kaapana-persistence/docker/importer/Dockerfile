FROM node:lts-alpine as build-stage

LABEL IMAGE="kaapana-persistence-importer"
LABEL VERSION="1.0.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

# Install Git
RUN apk update && apk add git

# Clone the specified repository
RUN git clone --single-branch git@github.com:lucaskulla/SpreadSheetImporter.git

RUN npm ci --silent
RUN npm run build

###############################
######### Production ##########
###############################
FROM docker.io/nginx:1.23.3-alpine

WORKDIR /kaapana/app

EXPOSE 80

# Copy built assets from the build stage
COPY --from=build-stage /kaapana/app/build /usr/share/nginx/html

CMD ["nginx", "-g", "daemon off;"]
