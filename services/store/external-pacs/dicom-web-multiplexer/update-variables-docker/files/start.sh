#!/bin/sh

CONFIG_FILE="/kaapana/mounted/workflows/plugins/kaapana/blueprints/kaapana_global_variables.py"

if [ "$1" = "append" ]; then
    echo "DICOM_WEB_SERVICE_RS = \"$DICOM_WEB_SERVICE_RS\"" >> "$CONFIG_FILE"
    echo "DICOM_WEB_SERVICE_URI = \"$DICOM_WEB_SERVICE_URI\"" >> "$CONFIG_FILE"
elif [ "$1" = "remove" ]; then
    sed -i '/DICOM_WEB_SERVICE_RS = "http:\/\/dicom-web-multiplexer-service.*"/d' "$CONFIG_FILE"
    sed -i '/DICOM_WEB_SERVICE_URI = "http:\/\/dicom-web-multiplexer-service.*"/d' "$CONFIG_FILE"
else
    echo "Invalid action. Use 'append' or 'remove'."
    exit 1
fi

# Display the updated config file for verification
cat "$CONFIG_FILE"
