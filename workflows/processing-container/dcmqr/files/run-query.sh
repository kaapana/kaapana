#!/bin/sh
set -x

CMD=""

if [ -n "$MAX_QUERY_SIZE" ]; then
    CMD="$CMD --max-query-size $MAX_QUERY_SIZE"
fi

if [ -n "$START_DATE" ]; then
    CMD="$CMD --start-date $START_DATE"
fi

if [ -n "$END_DATE" ]; then 
    CMD="$CMD --end-date $END_DATE"
fi

mkdir -p  /$WORKFLOW_DIR/$BATCH_NAME/query/$OPERATOR_OUT_DIR/
CMD="$CMD --filter-uid --level $LEVEL -aet $LOCAL_AE_TITLE -aec $AE_TITLE $PACS_HOST $PACS_PORT /$WORKFLOW_DIR/$BATCH_NAME/query/$OPERATOR_OUT_DIR/result.jsonl"

python3 -u query.py $CMD