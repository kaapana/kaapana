echo "Hello World"

find $WORKFLOW_DIR/$OPERATOR_IN_DIR -follow -name '*.svs' -exec /kaapana/app/idc-wsi-conversion/gdcsvstodcm_svs.sh '{}' ';'
