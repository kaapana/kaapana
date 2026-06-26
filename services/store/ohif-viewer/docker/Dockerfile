FROM docker.io/node:20.18.1-slim AS build

LABEL IMAGE="ohif"
LABEL VERSION="v3.10.4-ohif-ai"
LABEL BUILD_IGNORE="False"

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git build-essential python3 \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable && corepack prepare yarn@1.22.22 --activate
RUN yarn config set workspaces-experimental true

COPY vendor/ohif-ai-viewers /src

WORKDIR /src

COPY files/kaapana.js /src/platform/app/public/config/kaapana.js

ENV HTML_TEMPLATE="index.html"
ENV PUBLIC_URL="/ohif/"
ENV APP_CONFIG="config/kaapana.js"

COPY files/customization.patch /src/
RUN git apply --ignore-whitespace customization.patch

RUN yarn install

# OHIF-AI carries patched Cornerstone/dcmjs/vtk runtime files that enable the
# prompt tools and labelmap update path used by nnInteractive.
RUN rm -f node_modules/@cornerstonejs/tools/dist/esm/tools/base/AnnotationTool.js \
    node_modules/@cornerstonejs/tools/dist/esm/tools/annotation/ProbeTool.js \
    node_modules/@cornerstonejs/tools/dist/esm/tools/annotation/RectangleROITool.js \
    node_modules/@cornerstonejs/tools/dist/esm/tools/annotation/PlanarFreehandROITool.js \
    node_modules/@cornerstonejs/tools/dist/esm/tools/annotation/planarFreehandROITool/renderMethods.js \
    node_modules/@cornerstonejs/tools/dist/esm/tools/annotation/planarFreehandROITool/drawLoop.js \
    node_modules/@cornerstonejs/tools/dist/esm/tools/displayTools/Labelmap/labelmapDisplay.js \
    node_modules/@cornerstonejs/tools/dist/esm/tools/displayTools/Labelmap/addLabelmapToElement.js \
    node_modules/@cornerstonejs/tools/dist/esm/tools/displayTools/Labelmap/removeLabelmapFromElement.js \
    node_modules/@cornerstonejs/tools/dist/esm/cursors/elementCursor.js \
    node_modules/@cornerstonejs/tools/dist/esm/stateManagement/segmentation/SegmentationRenderingEngine.js \
    node_modules/@cornerstonejs/tools/dist/esm/stateManagement/segmentation/helpers/clearSegmentValue.js \
    node_modules/@cornerstonejs/tools/dist/esm/utilities/segmentation/getSegmentLargestBidirectional.js \
    node_modules/@cornerstonejs/tools/dist/esm/utilities/segmentation/findLargestBidirectional.js \
    node_modules/@cornerstonejs/tools/dist/esm/workers/computeWorker.js \
    node_modules/@cornerstonejs/tools/dist/esm/utilities/segmentation/getOrCreateImageVolume.js \
    node_modules/@cornerstonejs/core/dist/esm/utilities/VoxelManager.js \
    node_modules/dcmjs/build/dcmjs.es.js \
    node_modules/@kitware/vtk.js/Filters/General/ImageMarchingSquares.js \
    && cp backup/esm/AnnotationTool.js node_modules/@cornerstonejs/tools/dist/esm/tools/base/ \
    && cp backup/esm/ProbeTool.js node_modules/@cornerstonejs/tools/dist/esm/tools/annotation/ \
    && cp backup/esm/RectangleROITool.js node_modules/@cornerstonejs/tools/dist/esm/tools/annotation/ \
    && cp backup/esm/PlanarFreehandROITool.js node_modules/@cornerstonejs/tools/dist/esm/tools/annotation/ \
    && cp backup/esm/renderMethods.js node_modules/@cornerstonejs/tools/dist/esm/tools/annotation/planarFreehandROITool/ \
    && cp backup/esm/drawLoop.js node_modules/@cornerstonejs/tools/dist/esm/tools/annotation/planarFreehandROITool/ \
    && cp backup/esm/labelmapDisplay.js node_modules/@cornerstonejs/tools/dist/esm/tools/displayTools/Labelmap/labelmapDisplay.js \
    && cp backup/esm/addLabelmapToElement.js node_modules/@cornerstonejs/tools/dist/esm/tools/displayTools/Labelmap/addLabelmapToElement.js \
    && cp backup/esm/removeLabelmapFromElement.js node_modules/@cornerstonejs/tools/dist/esm/tools/displayTools/Labelmap/removeLabelmapFromElement.js \
    && cp backup/esm/performStackLabelmapUpdate.js node_modules/@cornerstonejs/tools/dist/esm/eventListeners/segmentation/labelmap/performStackLabelmapUpdate.js \
    && cp backup/esm/elementCursor.js node_modules/@cornerstonejs/tools/dist/esm/cursors/elementCursor.js \
    && cp backup/esm/SegmentationRenderingEngine.js node_modules/@cornerstonejs/tools/dist/esm/stateManagement/segmentation/ \
    && cp backup/esm/clearSegmentValue.js node_modules/@cornerstonejs/tools/dist/esm/stateManagement/segmentation/helpers/ \
    && cp backup/esm/getSegmentLargestBidirectional.js node_modules/@cornerstonejs/tools/dist/esm/utilities/segmentation/getSegmentLargestBidirectional.js \
    && cp backup/esm/findLargestBidirectional.js node_modules/@cornerstonejs/tools/dist/esm/utilities/segmentation/findLargestBidirectional.js \
    && cp backup/esm/computeWorker.js node_modules/@cornerstonejs/tools/dist/esm/workers/computeWorker.js \
    && cp backup/esm/getOrCreateImageVolume.js node_modules/@cornerstonejs/tools/dist/esm/utilities/segmentation/getOrCreateImageVolume.js \
    && cp backup/esm/VoxelManager.js node_modules/@cornerstonejs/core/dist/esm/utilities/VoxelManager.js \
    && cp backup/dcmjs/dcmjs.es.js node_modules/dcmjs/build/dcmjs.es.js \
    && cp backup/vtkjs/ImageMarchingSquares.js node_modules/@kitware/vtk.js/Filters/General/ImageMarchingSquares.js

RUN yarn run build

# Preserve vendored OSS notices in the distributable image.
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
