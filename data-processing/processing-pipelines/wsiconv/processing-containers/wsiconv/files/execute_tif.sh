echo "Hello World"

find $WORKFLOW_DIR/$OPERATOR_IN_DIR -follow -name '*.tif' -exec /kaapana/app/idc-wsi-conversion/gdcsvstodcm_tif.sh '{}' ';'
