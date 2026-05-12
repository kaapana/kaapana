#!/bin/bash
set -eu

MINIO_BUCKET=$(echo "${MINIO_PATH}/" | cut -d'/' -f1)
mc alias set minio http://${MINIO_SERVICE} ${MINIO_USER} ${MINIO_PASSWORD}
mc mb --ignore-existing minio/${MINIO_BUCKET}
mkdir -p $LOCAL_PATH

run_consistency_check() {
    local check_output
    check_output=$(mktemp)

    set +e
    rclone check \
        "${rclone_exclude_args[@]}" \
        --s3-provider Minio \
        --s3-endpoint "http://$MINIO_SERVICE" \
        --s3-access-key-id "$MINIO_USER" \
        --s3-secret-access-key "$MINIO_PASSWORD" \
        --checkers 16 \
        --combined "$check_output" \
        ":s3:/$MINIO_PATH" \
        "$LOCAL_PATH"
    local result=$?
    set -e

    if [[ $result -eq 0 ]]; then
        echo "INFO: Consistency check with checksums succeeded"
    else
        echo "WARN: Consistency check with checksums found mismatches (exit code ${result})"
        sed -n '1,200p' "$check_output"
    fi

    rm -f "$check_output"
}

check_sync_endpoints() {
    local local_check_file
    local_check_file=$(mktemp "${LOCAL_PATH}/.minio-mirror-writable.XXXXXX")
    rm -f "$local_check_file"

    rclone lsf \
        "${rclone_exclude_args[@]}" \
        --s3-provider Minio \
        --s3-endpoint "http://$MINIO_SERVICE" \
        --s3-access-key-id "$MINIO_USER" \
        --s3-secret-access-key "$MINIO_PASSWORD" \
        ":s3:/$MINIO_PATH" >/dev/null
}

run_sync_round_quietly() {
    local output_file
    output_file=$(mktemp)

    set +e
    "$@" >"$output_file" 2>&1
    local result=$?
    set -e

    if [[ $result -ne 0 ]]; then
        cat "$output_file"
        rm -f "$output_file"
        return $result
    fi

    if grep -q "No changes found" "$output_file"; then
        rm -f "$output_file"
        return 0
    fi

    if [[ -s "$output_file" ]]; then
        cat "$output_file"
    fi

    rm -f "$output_file"
    return 0
}

rclone_exclude_args=(
    # Ignore transient files that are never meaningful sync targets. This keeps
    # bisync from chasing incomplete transfers and local editor/cache artifacts.
    --exclude "*.partial"
    --exclude "**/.venv/**"
    --exclude "**/__pycache__/**"
    --exclude "**/.DS_Store"
    --exclude "**/Thumbs.db"
    --exclude "**/*.swp"
    --exclude "**/*.swo"
    --exclude "**/*~"
    --exclude "**/.nfs*"
)
if [ -v EXCLUDE ]; then
    IFS=',' read -ra EXCLUSION_PATTERNS <<< "${EXCLUDE}"
    for pattern in "${EXCLUSION_PATTERNS[@]}"; do
        # Trim accidental whitespace from comma-separated values before building
        # rclone exclude rules.
        pattern="${pattern#"${pattern%%[![:space:]]*}"}"
        pattern="${pattern%"${pattern##*[![:space:]]}"}"

        if [[ -z "${pattern}" ]]; then
            continue
        fi

        # A trailing slash is meant to exclude a directory recursively.
        if [[ "${pattern}" == */ ]]; then
            rclone_exclude_args+=(--exclude "${pattern}**")
            continue
        fi

        rclone_exclude_args+=(--exclude "${pattern}")
    done
fi

MINIO_PATH="$(printf '%s\n' "$MINIO_PATH" | sed -E 's#^/+##; s#/+#/#g; s#/$##')"
check_sync_endpoints

if [[ $ACTION == "FETCH" ]]; then
    echo "INFO: Start to mirror minio objects from ${MINIO_PATH} into local directory ${LOCAL_PATH}"
    cp /kaapana/app/README.txt ${LOCAL_PATH}
    mc cp /kaapana/app/README.txt minio/${MINIO_PATH}/README.txt
    # Poll with one-way sync instead of `mc mirror --watch` so FETCH keeps
    # picking up new objects even when object notification streams are unstable.
    FETCH_SYNC_CMD=(
        rclone sync
        "${rclone_exclude_args[@]}"
        --s3-provider Minio
        --s3-endpoint "http://$MINIO_SERVICE"
        --s3-access-key-id "$MINIO_USER"
        --s3-secret-access-key "$MINIO_PASSWORD"
        ":s3:/$MINIO_PATH"
        "$LOCAL_PATH"
        --create-empty-src-dirs
        # Use modtime+size comparisons for faster repeated polling on local
        # filesystems.
        --transfers 8
        --checkers 16
        -Mv
    )

    echo "INFO: Inital sync"
    "${FETCH_SYNC_CMD[@]}"
    while [[ true ]]; do
        sleep ${SYNC_INTERVAL:-5}
        run_sync_round_quietly "${FETCH_SYNC_CMD[@]}"
    done
elif [[ $ACTION == "PUSH" ]]; then
    echo "INFO: Start to mirror data from local directory ${LOCAL_PATH} into  minio objects at ${MINIO_PATH}"
    cp /kaapana/app/README.txt ${LOCAL_PATH}
    mc cp /kaapana/app/README.txt minio/${MINIO_PATH}/README.txt
    # Poll with one-way sync instead of `mc mirror --watch` so PUSH follows the
    # same rclone-based sync path as the bidirectional mode.
    PUSH_SYNC_CMD=(
        rclone sync
        "${rclone_exclude_args[@]}"
        --s3-provider Minio
        --s3-endpoint "http://$MINIO_SERVICE"
        --s3-access-key-id "$MINIO_USER"
        --s3-secret-access-key "$MINIO_PASSWORD"
        "$LOCAL_PATH"
        ":s3:/$MINIO_PATH"
        --create-empty-src-dirs
        # Use modtime+size comparisons for faster repeated polling on local
        # filesystems.
        --transfers 8
        --checkers 16
        -Mv
    )

    echo "INFO: Inital sync"
    "${PUSH_SYNC_CMD[@]}"
    while [[ true ]]; do
        sleep ${SYNC_INTERVAL:-5}
        run_sync_round_quietly "${PUSH_SYNC_CMD[@]}"
    done
elif [[ $ACTION == "SYNC" ]]; then
    echo "INFO: Start bidirectional sync from local directory ${LOCAL_PATH} into  minio objects at ${MINIO_PATH}"
    # Keep retry timing consistent across the initial resync and follow-up
    # polling rounds.
    SYNC_INTERVAL_SECONDS=${SYNC_INTERVAL:-5}
    # Run a slower read-only checksum audit outside the hot path. This is meant
    # to detect silent drift that size+modtime would miss without letting the
    # check mutate either side or trigger automatic recovery behavior.
    CHECK_INTERVAL_SECONDS=${CHECK_INTERVAL_SECONDS:-3600}
    NEXT_CHECK_EPOCH=$(( $(date +%s) + CHECK_INTERVAL_SECONDS ))
    # Resync is required to bootstrap a fresh bisync state, but running it after
    # every transient error is unsafe because resync copies the union of both
    # sides and can therefore resurrect files that were intentionally deleted on
    # only one side. Allow operators to opt back in explicitly if needed.
    # Manual operator recovery procedure:
    #   1. Verify which side should be authoritative before resyncing.
    #   2. Enable one-shot automatic recovery:
    #        kubectl -n services set env deployment/<release-name> AUTO_RESYNC_ON_ERROR=true
    #   3. Restart the pod and watch the sync container logs:
    #        kubectl -n services rollout restart deployment/<release-name>
    #        kubectl -n services logs -f deployment/<release-name> -c minio-sync
    #   4. Remove the override again after recovery completed:
    #        kubectl -n services set env deployment/<release-name> AUTO_RESYNC_ON_ERROR-
    #        kubectl -n services rollout restart deployment/<release-name>
    AUTO_RESYNC_ON_ERROR=${AUTO_RESYNC_ON_ERROR:-false}
    RCLONE_SYNC_CMD=(
        rclone bisync
        "${rclone_exclude_args[@]}"
        --s3-provider Minio
        --s3-endpoint "http://$MINIO_SERVICE"
        --s3-access-key-id "$MINIO_USER"
        --s3-secret-access-key "$MINIO_PASSWORD"
        ":s3:/$MINIO_PATH"
        "$LOCAL_PATH"
        --create-empty-src-dirs
        # Use modtime+size for delta detection to avoid the local checksum cost
        # on every bisync round.
        --compare size,modtime
        --resilient
        --recover
        -Mv
        --drive-skip-gdocs
        --fix-case
        --transfers 8
        --checkers 16
    )

    echo "INFO: Inital sync"
    until "${RCLONE_SYNC_CMD[@]}" --resync; do
        echo "ERROR: Initial resync failed with exit code $? - will retry after ${SYNC_INTERVAL_SECONDS}s"
        sleep ${SYNC_INTERVAL_SECONDS}
    done

    while [[ true ]]; do
        sleep ${SYNC_INTERVAL_SECONDS}
        set +e
        run_sync_round_quietly "${RCLONE_SYNC_CMD[@]}"
        RESULT=$?
        set -e

        case $RESULT in
        0)
            if [[ $CHECK_INTERVAL_SECONDS -gt 0 ]] && [[ $(date +%s) -ge $NEXT_CHECK_EPOCH ]]; then
                run_consistency_check
                NEXT_CHECK_EPOCH=$(( $(date +%s) + CHECK_INTERVAL_SECONDS ))
            fi
            continue ;;
        *)
            echo "ERROR: Sync round failed with exit code ${RESULT}"

            if [[ "${AUTO_RESYNC_ON_ERROR}" == "true" ]]; then
                echo "WARN: AUTO_RESYNC_ON_ERROR=true - attempting recovery resync"
                set +e
                "${RCLONE_SYNC_CMD[@]}" --resync
                RESYNC_RESULT=$?
                set -e
                if [[ $RESYNC_RESULT -eq 0 ]]; then
                    echo "INFO: Recovery resync successfull"
                    continue
                fi
                echo "ERROR: Recovery resync failed with exit code ${RESYNC_RESULT} - keeping container alive and retrying after ${SYNC_INTERVAL_SECONDS}s"
                continue
            fi

            echo "WARN: Skipping automatic resync to avoid recreating files that were deleted on one side"
            echo "WARN: If bisync now requires a manual recovery, rerun once with AUTO_RESYNC_ON_ERROR=true after checking both sides"
        esac
    done
else
    echo "ERROR: ACTION ${ACTION} not supported!!"
    echo "ERROR: ACTION must be one of FETCH, PUSH or SYNC"
    exit 1
fi
