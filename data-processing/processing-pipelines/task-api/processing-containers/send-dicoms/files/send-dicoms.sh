dcmsend\
    -v \
    ${PACS_HOST}\
    ${PACS_PORT}\
    -aet kp-${DATASET}\
    -aec ${PROJECT_NAME}\
    --scan-directories \
    --scan-pattern *.dcm\
    --no-halt \
    +r \
    /home/kaapana/dicoms