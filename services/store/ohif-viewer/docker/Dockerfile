FROM docker.io/node:20.18.1-slim AS build

LABEL IMAGE="ohif"
LABEL VERSION="v3.10.4-ohif-ai"
LABEL BUILD_IGNORE="False"

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git build-essential python3 \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable && corepack prepare yarn@1.22.22 --activate
RUN yarn config set workspaces-experimental true

# Fetch PRISTINE upstream OHIF at the OHIF-AI fork's exact base commit (2 trivial commits
# behind tag v3.10.4). No OHIF source is committed to this repo; it is fetched at build time.
# To upgrade OHIF: bump OHIF_COMMIT and re-validate patches/ + node-module-patches/.
ARG OHIF_COMMIT=d383be7c720ec61f5bb1262ebe70893873718951
RUN git init /src \
    && cd /src \
    && git remote add origin https://github.com/OHIF/Viewers.git \
    && git fetch --depth 1 origin ${OHIF_COMMIT} \
    && git checkout -q FETCH_HEAD

WORKDIR /src

# 1) OHIF-AI fork source delta, split by concern, applied to pristine in filename order.
#    Includes package.json/resolutions changes so dependency resolution matches the fork.
#    Combined result is identical to the historical single ohif-ai.patch. See patches/README.md.
COPY patches /src/patches
RUN for p in patches/*.patch; do echo "==> applying $p"; git apply --ignore-whitespace "$p" || exit 1; done

# 1b) Drop workspace packages the fork removed, so the fork yarn.lock applies cleanly.
RUN rm -rf platform/cli extensions/test-extension modes/basic-dev-mode modes/basic-test-mode

# 1c) Pin EXACTLY the fork's resolved dependency tree (Cornerstone 3.33.5, react-router 6.30.4, ...).
#     Critical: the node-module-patches applied below are version-specific to this tree.
COPY yarn.lock /src/yarn.lock

# 2) Fork-only build inputs: our plugin config and app config.
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

# Sanity: the node-module patches target these exact versions; fail early if resolution drifted.
RUN V=$(node -e "console.log(JSON.parse(require('fs').readFileSync('node_modules/@cornerstonejs/tools/package.json','utf8')).version)") \
    && echo "Resolved @cornerstonejs/tools: $V" \
    && case "$V" in 3.33.*) ;; *) echo "ERROR: expected Cornerstone 3.33.x (node-module-patches target it), got $V"; exit 1;; esac

# 4) Apply the OHIF-AI Cornerstone/vtk runtime modifications as readable, version-named
# patch-package diffs (the prompt tools + labelmap update path used by nnInteractive). These
# REPLACE the former opaque backup/ file overwrites. patch-package fails loudly if a target
# package's installed version drifts from the patch filename. The dcmjs override was dropped
# (it carried no nnInteractive changes; stock dcmjs already provides SegmentDescription).
COPY node-module-patches /src/node-module-patches
RUN npx --yes patch-package --patch-dir node-module-patches

RUN yarn run build

# Preserve OSS notices from the OHIF source tree + node_modules in the distributable image.
RUN mkdir -p /src/vendor-licenses/ohif-ai-viewers \
    && find /src -path '*/LICENSE' -type f -exec sh -c '\
        for license_file do \
            rel_path="${license_file#/src/}"; \
            mkdir -p "/src/vendor-licenses/ohif-ai-viewers/$(dirname "${rel_path}")"; \
            cp "${license_file}" "/src/vendor-licenses/ohif-ai-viewers/${rel_path}"; \
        done' sh {} +

FROM docker.io/nginx:1.31-alpine AS production-stage

RUN apk update && apk upgrade libxml2

COPY --from=build /src/platform/app/dist/ /usr/share/nginx/html/ohif/
COPY --from=build /src/vendor-licenses/ /usr/share/nginx/html/ohif/vendor-licenses/

COPY files/ /usr/share/nginx/html/
COPY files/kaapana.js /usr/share/nginx/html/ohif/app-config.js

COPY conf /etc/nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
