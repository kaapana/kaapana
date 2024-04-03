#!/bin/sh
ROOT_DIR=/kaapana/app

# Replace env vars in files served by NGINX
for file in $ROOT_DIR/js/*.js* $ROOT_DIR/index.html $ROOT_DIR/precache-manifest*.js; do
    echo "Processing $file ..."
    sed -i 's|VUE_APP_KAAPANA_BACKEND_ENDPOINT_PLACEHOLDER|'${VUE_APP_KAAPANA_BACKEND_ENDPOINT}'|g' $file
    sed -i 's|VUE_APP_IDLE_TIMEOUT_PLACEHOLDER|'${VUE_APP_IDLE_TIMEOUT}'|g' $file
    # Your other variables placeholders from .env here...
done

# Let container execution proceed
exec "$@"
