FROM docker.io/node:20.18.1-slim AS build

ARG OHIF_VERSION=3.10.4
ARG OHIF_COMMIT=d383be7c720ec61f5bb1262ebe70893873718951

LABEL IMAGE="ohif"
LABEL VERSION="v${OHIF_VERSION}-nninteractive"
LABEL BUILD_IGNORE="False"

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git build-essential python3 \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable && corepack prepare yarn@1.22.22 --activate
RUN yarn config set workspaces-experimental true

# Fetch pristine upstream OHIF. No OHIF source is committed to this repo; it is fetched at build time.
# To upgrade OHIF: bump OHIF_COMMIT and re-validate patches/ + node-module-patches/.
RUN git init /src \
    && cd /src \
    && git remote add origin https://github.com/OHIF/Viewers.git \
    && git fetch --depth 1 origin ${OHIF_COMMIT} \
    && git checkout -q FETCH_HEAD

WORKDIR /src

RUN printf '{\n  "version": "%s",\n  "commit": "%s"\n}\n' "$OHIF_VERSION" "$OHIF_COMMIT" > version.json \
    && printf '%s\n' "$OHIF_VERSION" > version.txt \
    && printf '%s\n' "$OHIF_COMMIT" > commit.txt

# 1) Kaapana source patches, split by concern, applied to pristine OHIF in filename order.
#    Includes package.json/resolutions changes so dependency resolution matches yarn.lock.
#    See patches/README.md for ownership and upgrade rules.
COPY patches /src/patches
RUN for p in patches/*.patch; do echo "==> applying $p"; git apply --ignore-whitespace "$p" || exit 1; done

# 1b) Drop workspace packages not used by this image, so the frozen yarn.lock applies cleanly.
RUN rm -rf platform/cli extensions/test-extension modes/basic-dev-mode modes/basic-test-mode

# 1c) Pin exactly the resolved dependency tree (Cornerstone 3.33.5, react-router 6.30.4, ...).
#     Critical: the node-module-patches applied below are version-specific to this tree.
COPY yarn.lock /src/yarn.lock

# 2) Kaapana-owned extension/mode packages plus app config.
COPY packages/extension-nninteractive /src/extensions/nninteractive
COPY packages/mode-nninteractive /src/modes/nninteractive
COPY pluginConfig.json /src/platform/app/pluginConfig.json
COPY files/kaapana.js /src/platform/app/public/config/kaapana.js

ENV HTML_TEMPLATE="index.html"
ENV PUBLIC_URL="/ohif/"
ENV APP_CONFIG="config/kaapana.js"

# 3) Kaapana customization patch (embedding toggles, auto-hydrate, robustness).
COPY files/customization.patch /src/
RUN git apply --ignore-whitespace customization.patch

RUN yarn install --frozen-lockfile

# Sanity: node-module-patches target these exact package versions; fail early if resolution drifted.
RUN node -e "const fs=require('fs'); const expected={'@cornerstonejs/core':'3.33.5','@cornerstonejs/tools':'3.33.5','@kitware/vtk.js':'32.12.0'}; for (const [name, version] of Object.entries(expected)) { const actual=JSON.parse(fs.readFileSync('node_modules/' + name + '/package.json', 'utf8')).version; console.log('Resolved ' + name + ': ' + actual); if (actual !== version) { console.error('ERROR: expected ' + name + ' ' + version + ' (node-module-patches target it), got ' + actual); process.exit(1); } }"

# 4) Apply Cornerstone/vtk runtime fixes as readable, version-named patch-package diffs.
#    patch-package fails loudly if a target package's installed version drifts from the patch filename.
COPY node-module-patches /src/node-module-patches
RUN npx --yes patch-package --patch-dir node-module-patches

RUN yarn run build

# Preserve OSS notices from the OHIF source tree + node_modules in the distributable image.
RUN mkdir -p /src/vendor-licenses/ohif-viewer \
    && find /src -path '*/LICENSE' -type f -exec sh -c '\
        for license_file do \
            rel_path="${license_file#/src/}"; \
            mkdir -p "/src/vendor-licenses/ohif-viewer/$(dirname "${rel_path}")"; \
            cp "${license_file}" "/src/vendor-licenses/ohif-viewer/${rel_path}"; \
        done' sh {} +

FROM docker.io/nginx:1.31-alpine AS production-stage

ARG OHIF_VERSION=3.10.4
ARG OHIF_COMMIT=d383be7c720ec61f5bb1262ebe70893873718951

LABEL IMAGE="ohif"
LABEL VERSION="v${OHIF_VERSION}-nninteractive"
LABEL BUILD_IGNORE="False"
LABEL OHIF_VERSION="${OHIF_VERSION}"
LABEL OHIF_COMMIT="${OHIF_COMMIT}"

RUN apk update && apk upgrade libxml2

COPY --from=build /src/platform/app/dist/ /usr/share/nginx/html/ohif/
COPY --from=build /src/vendor-licenses/ /usr/share/nginx/html/ohif/vendor-licenses/
COPY --from=build /src/version.json /usr/share/nginx/html/ohif/version.json
COPY --from=build /src/version.txt /usr/share/nginx/html/ohif/version.txt
COPY --from=build /src/commit.txt /usr/share/nginx/html/ohif/commit.txt

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
