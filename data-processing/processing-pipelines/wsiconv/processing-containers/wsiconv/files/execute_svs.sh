echo "Copyright (c) 2001-2022, David A. Clunie DBA PixelMed Publishing. All rights reserved."

find $WORKFLOW_DIR/$OPERATOR_IN_DIR -follow -name '*.svs' -exec /kaapana/app/idc-wsi-conversion/gdcsvstodcm_svs.sh '{}' ';'
