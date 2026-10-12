FROM docker.io/node:20-bookworm-slim AS frontend-build

WORKDIR /app
COPY files/frontend/package.json files/frontend/package-lock.json* ./
RUN npm install --legacy-peer-deps --prefer-offline --no-audit --progress=false
COPY files/frontend .
RUN npm run build


FROM docker.io/node:20-bookworm-slim

LABEL IMAGE="split-viewer"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

# No TotalSegmentator/dcmqi/dcm2niix here - segmentation runs through the
# auto-segmentation-pipeline Airflow DAG instead of inline in this container
# (see files/server/server.js), so none of that tooling is needed anymore.
WORKDIR /app
COPY files/server/package.json files/server/package-lock.json* ./
RUN npm install --omit=dev
COPY files/server/server.js ./
COPY --from=frontend-build /app/dist ../dist

ENV PORT=3001
EXPOSE 3001
CMD ["node", "server.js"]
