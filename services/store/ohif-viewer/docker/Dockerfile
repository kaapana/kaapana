FROM docker.io/node:26-alpine3.23 AS build

LABEL IMAGE="ohif"
LABEL VERSION="v3.13.4"
LABEL BUILD_IGNORE="False"

RUN apk add --no-cache ca-certificates git

# Kept in lockstep with the checked out commit: upstream declares it in packageManager.
RUN npm install -g pnpm@11.5.2

RUN git clone https://github.com/OHIF/Viewers.git /src && cd /src && git checkout e1cf19a210b745c81d281b77cb94666654ee70b1

WORKDIR /src

COPY files/kaapana.js /src/platform/app/public/config/kaapana.js

ENV HTML_TEMPLATE="index.html"
ENV PUBLIC_URL="/ohif/"
ENV APP_CONFIG="config/kaapana.js"

COPY files/customization.patch /src/
RUN git apply --ignore-whitespace customization.patch

RUN pnpm install --frozen-lockfile
RUN pnpm run build

FROM docker.io/nginx:1.31-alpine AS production-stage

RUN apk update && apk upgrade libxml2

COPY --from=build /src/platform/app/dist/ /usr/share/nginx/html/ohif/

# The generated manifest points its icons at /assets, which is not served below the
# /ohif/ subpath. This one carries the prefixed paths.
COPY files/manifest.json /usr/share/nginx/html/ohif/manifest.json

# The build minifies the app config onto one line. Serving the source keeps the
# deployed DICOMweb root and project prefix readable.
COPY files/kaapana.js /usr/share/nginx/html/ohif/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
