#!/bin/sh
set -eu -o pipefail

buildah bud \
  --isolation=chroot \
  --no-cache \
  -t "${BUILD_DESTINATION}" \
  --root /storage \
  --runroot /storage/run/containers/storage \
  --tls-verify=false \
  "${BUILD_CONTEXT}"


buildah push \
  --root /storage \
  --runroot /storage/run/containers/storage \
  --tls-verify=false \
  "${BUILD_DESTINATION}"
